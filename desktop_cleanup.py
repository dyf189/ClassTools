# -*- coding: utf-8 -*-
"""桌面清理模块：每周固定星期几把桌面指定类型的文件移动到备份目录

由原来硬编码的“周一清理”改造为可配置：星期、备份目录、文件类型均可设置。
"""
import os
import shutil
from datetime import datetime

from PyQt5.QtCore import QTimer
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFormLayout, QLabel, QLineEdit,
    QPushButton, QCheckBox, QComboBox, QMessageBox, QFileDialog
)

from app_config import ConfigManager, WEEKDAY_NAMES

DEFAULT_EXTENSIONS = [".ppt", ".pptx", ".doc", ".docx", ".jpg"]
DEFAULT_BACKUP_DIR = "D:\\桌面备份"


# ---------- 清理调度器 ----------
class DesktopCleanupManager(object):
    """按星期检查并执行桌面清理；由主窗口持有"""

    def __init__(self):
        self.config = {}
        self.timer = QTimer()
        self.timer.setInterval(600000)  # 每 10 分钟检查一次
        self.timer.timeout.connect(self.check)

    def start(self):
        self.reload()
        self.check()  # 启动时先检查一次
        self.timer.start()

    def reload(self):
        """从配置文件重新读取清理设置"""
        try:
            self.config = ConfigManager.load_config().get("desktop_cleanup", {})
        except Exception as e:
            print(f"读取桌面清理配置失败: {e}")
            self.config = {}

    def check(self, now=None):
        """到达设定的星期且当天未执行过时执行清理"""
        now = now or datetime.now()
        if not self.config.get("enabled", True):
            return
        try:
            if int(self.config.get("day_of_week", 1)) != now.isoweekday():
                return
            today = now.strftime("%Y-%m-%d")
            if self.config.get("last_run_date") == today:
                return
            self.run_cleanup()
            # 记录今天已执行，避免一天内反复移动文件
            cleanup_cfg = ConfigManager.load_config().get("desktop_cleanup", {})
            cleanup_cfg["last_run_date"] = today
            ConfigManager.update_config({"desktop_cleanup": cleanup_cfg})
        except Exception as e:
            print(f"桌面清理检查出错: {e}")

    def run_cleanup(self):
        """执行一次桌面清理，返回移动的文件数"""
        desktop = os.path.join(os.environ.get('USERPROFILE', ''), 'Desktop')
        backup_dir = self.config.get("backup_dir") or DEFAULT_BACKUP_DIR
        extensions = set(self.config.get("extensions") or DEFAULT_EXTENSIONS)

        moved = 0
        try:
            os.makedirs(backup_dir, exist_ok=True)

            for filename in os.listdir(desktop):
                src_path = os.path.join(desktop, filename)
                if os.path.isfile(src_path) and os.path.splitext(filename)[1].lower() in extensions:
                    dest_path = os.path.join(backup_dir, filename)
                    if os.path.exists(dest_path):
                        base, ext = os.path.splitext(filename)
                        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                        dest_path = os.path.join(backup_dir, f"{base}_{timestamp}{ext}")
                    try:
                        shutil.move(src_path, dest_path)
                        print(f"已移动: {filename}")
                        moved += 1
                    except Exception as e:
                        print(f"移动失败 {filename}: {e}")
        except Exception as e:
            print(f"桌面清理出错: {e}")
        return moved


# ---------- 清理设置面板 ----------
class DesktopCleanupWidget(QWidget):
    """桌面清理设置（作为设置对话框的一个标签页）"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()

    def init_ui(self):
        layout = QFormLayout(self)

        self.enabled_check = QCheckBox("启用每周桌面清理")
        layout.addRow("", self.enabled_check)

        self.day_combo = QComboBox()
        for i, day_name in enumerate(WEEKDAY_NAMES, start=1):
            self.day_combo.addItem(day_name, i)
        layout.addRow("清理日期：", self.day_combo)

        dir_row = QHBoxLayout()
        self.dir_input = QLineEdit()
        browse_btn = QPushButton("浏览...")
        browse_btn.clicked.connect(self.choose_dir)
        dir_row.addWidget(self.dir_input)
        dir_row.addWidget(browse_btn)
        layout.addRow("备份目录：", dir_row)

        self.ext_input = QLineEdit()
        self.ext_input.setPlaceholderText("用逗号分隔，例如：.ppt,.pptx,.doc,.docx,.jpg")
        layout.addRow("文件类型：", self.ext_input)

        self.tip_label = QLabel("")
        self.tip_label.setWordWrap(True)
        layout.addRow("", self.tip_label)

        run_btn = QPushButton("立即清理一次（不受星期限制）")
        run_btn.clicked.connect(self.run_now)
        layout.addRow("", run_btn)

    def set_config(self, cfg):
        cfg = cfg or {}
        self.enabled_check.setChecked(cfg.get("enabled", True))
        try:
            idx = self.day_combo.findData(int(cfg.get("day_of_week", 1)))
        except (TypeError, ValueError):
            idx = 0
        if idx >= 0:
            self.day_combo.setCurrentIndex(idx)
        self.dir_input.setText(cfg.get("backup_dir") or DEFAULT_BACKUP_DIR)
        self.ext_input.setText(",".join(cfg.get("extensions") or DEFAULT_EXTENSIONS))
        last = cfg.get("last_run_date", "从未执行")
        self.tip_label.setText(f"上次执行：{last}。清理会把桌面上匹配类型的文件移动到备份目录。")

    def get_config(self):
        raw = self.ext_input.text().replace('，', ',').replace(' ', ',')
        exts = [ext.strip().lower() for ext in raw.split(',') if ext.strip()]
        return {
            "enabled": self.enabled_check.isChecked(),
            "day_of_week": self.day_combo.currentData(),
            "backup_dir": self.dir_input.text().strip() or DEFAULT_BACKUP_DIR,
            "extensions": exts or list(DEFAULT_EXTENSIONS),
        }

    def choose_dir(self):
        chosen = QFileDialog.getExistingDirectory(self, "选择备份目录", self.dir_input.text())
        if chosen:
            self.dir_input.setText(chosen)

    def run_now(self):
        if QMessageBox.question(
                self, "确认", "确定现在就把桌面上匹配类型的文件移动到备份目录吗？") != QMessageBox.Yes:
            return
        manager = DesktopCleanupManager()
        manager.reload()
        manager.config = self.get_config()  # 使用界面上的设置立即执行
        moved = manager.run_cleanup()
        QMessageBox.information(self, "完成", f"本次共移动 {moved} 个文件。")
