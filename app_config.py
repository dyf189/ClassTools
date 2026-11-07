# -*- coding: utf-8 -*-
"""配置管理模块：countdown_config.json 的读写、默认值与旧版配置迁移"""
import json
import os
from datetime import datetime, timedelta

# 星期名称（isoweekday：1=周一 ... 7=周日）
WEEKDAY_NAMES = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]


# ---------- Python 3.6 兼容性函数 ----------
def parse_iso_datetime(iso_string):
    """兼容 Python 3.6 的 ISO 时间解析"""
    try:
        # Python 3.7+ 使用 fromisoformat
        return datetime.fromisoformat(iso_string)
    except AttributeError:
        # Python 3.6 手动解析
        try:
            # 处理格式: "2024-06-15T08:30:00" 或 "2024-06-15T08:30:00.123456"
            if 'T' in iso_string:
                date_part, time_part = iso_string.split('T')
                # 去除可能的微秒部分
                if '.' in time_part:
                    time_part = time_part.split('.')[0]
                return datetime.strptime(f"{date_part} {time_part}", "%Y-%m-%d %H:%M:%S")
            else:
                return datetime.strptime(iso_string, "%Y-%m-%d %H:%M:%S")
        except Exception as e:
            print(f"时间解析失败: {e}")
            return datetime.now()


# ---------- 配置管理器 ----------
class ConfigManager:
    CONFIG_FILE = "countdown_config.json"

    DEFAULT_CONFIG = {
        "target_time": (datetime.now() + timedelta(days=100)).isoformat(),
        "window_pos": [100, 100],
        "prefix_text": "距离中考还有",
        "display_mode": "auto",
        # 旧版每日关机字段（仅保留用于迁移旧配置文件，新版本不再直接使用）
        "auto_shutdown_enabled": True,
        "shutdown_time": "21:00",
        # 隐藏页：高考倒计时（默认不在主界面显示）
        "gaokao": {
            "target_time": "2027-06-07T09:00:00",
            "prefix_text": "距离高考还有",
            "display_mode": "days_only",
        },
        # 定时关机任务列表（新版支持多条）
        "shutdown_tasks": [],
        # 桌面清理
        "desktop_cleanup": {
            "enabled": True,
            "day_of_week": 1,
            "backup_dir": "D:\\桌面备份",
            "extensions": [".ppt", ".pptx", ".doc", ".docx", ".jpg"],
        },
        "style": {
            "font_size": 48,
            "text_color": "#FFD700",
            "opacity": 0.9
        }
    }

    @classmethod
    def load_config(cls):
        """加载配置，确保所有必需字段存在，并迁移旧版配置"""
        try:
            if os.path.exists(cls.CONFIG_FILE):
                with open(cls.CONFIG_FILE, 'r', encoding='utf-8') as f:
                    saved = json.load(f)

                # 深度合并默认配置，确保所有字段存在
                config = cls.DEFAULT_CONFIG.copy()
                cls._deep_update(config, saved)
                cls._migrate_old_shutdown(config, saved)
                return config
        except Exception as e:
            print(f"配置加载失败，使用默认配置: {e}")

        config = cls.DEFAULT_CONFIG.copy()
        cls._migrate_old_shutdown(config, {})
        return config

    @classmethod
    def _deep_update(cls, target, source):
        """递归更新字典"""
        for key, value in source.items():
            if key in target:
                if isinstance(value, dict) and isinstance(target[key], dict):
                    cls._deep_update(target[key], value)
                else:
                    target[key] = value

    @classmethod
    def _migrate_old_shutdown(cls, config, saved):
        """把旧版“每日一次关机”配置迁移为任务列表（仅当配置文件里没有任务列表时）"""
        if saved.get("shutdown_tasks") is not None:
            return
        config["shutdown_tasks"] = [{
            "id": "daily",
            "name": "每日定时关机",
            "time": str(config.get("shutdown_time", "21:00")),
            "days": [1, 2, 3, 4, 5, 6, 7],
            "action": "shutdown",
            "enabled": bool(config.get("auto_shutdown_enabled", True)),
        }]

    @classmethod
    def save_config(cls, config):
        """保存配置到文件"""
        try:
            # 确保配置目录存在
            config_dir = os.path.dirname(os.path.abspath(cls.CONFIG_FILE))
            if config_dir:
                os.makedirs(config_dir, exist_ok=True)

            # 写入临时文件，然后重命名（原子操作）
            temp_file = cls.CONFIG_FILE + '.tmp'
            with open(temp_file, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=2, ensure_ascii=False)

            # 删除旧文件并重命名临时文件
            if os.path.exists(cls.CONFIG_FILE):
                os.remove(cls.CONFIG_FILE)
            os.rename(temp_file, cls.CONFIG_FILE)

            print("配置已成功保存")
            return True
        except PermissionError as e:
            print(f"权限错误: {e}")
            return False
        except Exception as e:
            print(f"保存配置时出错: {e}")
            return False

    @classmethod
    def update_config(cls, new_data: dict):
        """部分更新配置并保存"""
        config = cls.load_config()
        config.update(new_data)
        return cls.save_config(config)
