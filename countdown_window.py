# -*- coding: utf-8 -*-
"""倒计时模块：主窗口（普通倒计时 + 默认隐藏的高考倒计时页）"""
from datetime import datetime, timedelta

from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QLabel, QMenu, QSystemTrayIcon, QStyle
)
from PyQt5.QtGui import QFont

from app_config import ConfigManager, parse_iso_datetime
from shutdown_manager import ShutdownScheduler
from desktop_cleanup import DesktopCleanupManager
from settings_dialog import SettingsDialog
from win_helpers import hide_from_taskbar

# 隐藏页切换手势：2 秒内连点 5 次，或按 Ctrl+Alt+G
GAOKAO_SWITCH_CLICKS = 5
GAOKAO_SWITCH_INTERVAL_MS = 2000


# ---------- 主窗口 ----------
class CountdownWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.oldPos = None
        self.show_gaokao = False          # 是否显示隐藏的高考倒计时页
        self._click_times = []            # 用于识别连点手势
        self.target_time = datetime.now()
        self.display_mode = "auto"
        self.prefix_text = ""
        self.gaokao_config = {}

        # 各功能模块的管理器
        self.shutdown_scheduler = ShutdownScheduler(on_action=self.on_shutdown_task_fired)
        self.cleanup_manager = DesktopCleanupManager()

        self.init_ui()
        self.init_tray()
        self.apply_settings()
        self.init_timer()

        self.shutdown_scheduler.start()
        self.cleanup_manager.start()

        # 在窗口完全初始化后再尝试隐藏任务栏
        hide_from_taskbar(self)

    def init_ui(self):
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        self.setFixedSize(1200, 200)
        self.setWindowTitle("倒计时")
        self.setFocusPolicy(Qt.StrongFocus)

        self.label = QLabel('加载中...', self)
        self.label.setAlignment(Qt.AlignCenter)
        self.label.setFont(QFont('HarmonyOS Sans SC', 48))
        self.setCentralWidget(self.label)

    def init_tray(self):
        self.tray_icon = QSystemTrayIcon(self)
        self.tray_icon.setIcon(self.style().standardIcon(QStyle.SP_ComputerIcon))
        self.tray_icon.setToolTip("倒计时工具")

        tray_menu = QMenu()
        setting_action = tray_menu.addAction("设置")
        setting_action.triggered.connect(self.show_settings)
        tray_menu.addSeparator()
        exit_action = tray_menu.addAction("退出")
        exit_action.triggered.connect(self.close_app)

        self.tray_icon.setContextMenu(tray_menu)
        self.tray_icon.show()

    def init_timer(self):
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_countdown)
        self.timer.start(1000)  # 每秒更新一次

    # ---------- 设置相关 ----------
    def apply_settings(self):
        """从配置文件重新加载设置并应用到界面"""
        try:
            config = ConfigManager.load_config()

            # 普通倒计时
            self.target_time = self._parse_target(config.get("target_time", ""))
            self.prefix_text = config.get("prefix_text", "")
            self.display_mode = config.get("display_mode", "auto")

            # 隐藏页（高考倒计时）
            self.gaokao_config = dict(config.get("gaokao") or {})

            # 样式
            style = config.get("style", {})
            font_size = style.get("font_size", 48)
            text_color = style.get("text_color", "#FFD700")
            opacity = style.get("opacity", 0.9)

            # 应用样式
            self.label.setStyleSheet(f"""
                QLabel {{
                    font-size: {font_size}px;
                    color: {text_color};
                    padding: 10px;
                }}
            """)
            font = QFont('HarmonyOS Sans SC', font_size)
            if not font.exactMatch():
                font = QFont('Microsoft YaHei', font_size)
            self.label.setFont(font)
            self.setWindowOpacity(opacity)

            # 窗口位置
            pos = config.get("window_pos", [100, 100])
            self.move(pos[0], pos[1])

            # 刷新各功能模块的配置
            self.shutdown_scheduler.reload()
            self.cleanup_manager.reload()

            # 立即刷新倒计时
            self.update_countdown()

        except Exception as e:
            print(f"应用设置时出错: {e}")

    @staticmethod
    def _parse_target(target_str):
        try:
            if target_str:
                return parse_iso_datetime(target_str)
        except Exception as e:
            print(f"解析目标时间失败: {e}")
        return datetime.now() + timedelta(days=100)

    def show_settings(self):
        """显示设置对话框"""
        dialog = SettingsDialog(self, self)
        dialog.exec_()

    def on_shutdown_task_fired(self, task):
        """定时关机任务触发时的提示"""
        try:
            self.tray_icon.showMessage(
                "ClassTools",
                f"定时任务“{task.get('name', '')}”触发，正在执行 {task.get('action', 'shutdown')}",
                QSystemTrayIcon.Information, 2000
            )
        except Exception:
            pass

    # ---------- 倒计时显示 ----------
    def update_countdown(self):
        """更新倒计时显示（普通页 / 隐藏的高考页）"""
        try:
            if self.show_gaokao:
                prefix = self.gaokao_config.get("prefix_text", "距离高考还有")
                target = self._parse_target(self.gaokao_config.get("target_time", ""))
                mode = self.gaokao_config.get("display_mode", "days_only")
            else:
                prefix = self.prefix_text
                target = self.target_time
                mode = self.display_mode

            now = datetime.now()
            delta = target - now
            total_seconds = delta.total_seconds()

            if total_seconds <= 0:
                self.label.setText(f"{prefix}0天 (已经到达)")
                return

            if mode == "days_only":
                self.label.setText(f"{prefix}{delta.days}天")
            elif mode == "days_hours":
                days = delta.days
                hours = delta.seconds // 3600
                self.label.setText(f"{prefix}{days}天{hours}小时")
            else:  # auto
                if total_seconds < 86400:  # 小于1天
                    hours = total_seconds // 3600
                    minutes = (total_seconds % 3600) // 60
                    seconds = total_seconds % 60
                    if hours > 0:
                        self.label.setText(f"{prefix}{int(hours)}小时{int(minutes)}分钟")
                    else:
                        self.label.setText(f"{prefix}{int(minutes)}分钟{int(seconds)}秒")
                else:
                    self.label.setText(f"{prefix}{delta.days}天")

        except Exception as e:
            print(f"更新倒计时出错: {e}")

    # ---------- 隐藏高考倒计时页的切换 ----------
    def toggle_gaokao_page(self):
        """在普通倒计时与隐藏的高考倒计时页之间切换"""
        self.show_gaokao = not self.show_gaokao
        self.update_countdown()
        tip = "已切换到高考倒计时（隐藏页）" if self.show_gaokao else "已切换回普通倒计时"
        print(tip)
        try:
            self.tray_icon.showMessage("ClassTools", tip, QSystemTrayIcon.Information, 1500)
        except Exception:
            pass

    def _register_click(self):
        """记录点击，2 秒内连点 5 次切换隐藏页"""
        now = datetime.now()
        self._click_times = [
            t for t in self._click_times
            if (now - t).total_seconds() <= GAOKAO_SWITCH_INTERVAL_MS / 1000.0
        ]
        self._click_times.append(now)
        if len(self._click_times) >= GAOKAO_SWITCH_CLICKS:
            self._click_times = []
            self.toggle_gaokao_page()

    def keyPressEvent(self, event):
        # Ctrl + Alt + G 同样可以切换隐藏页
        if (event.key() == Qt.Key_G
                and (event.modifiers() & Qt.ControlModifier)
                and (event.modifiers() & Qt.AltModifier)):
            self.toggle_gaokao_page()
        else:
            super().keyPressEvent(event)

    # ---------- 关闭 ----------
    def close_app(self):
        """关闭应用前保存窗口位置"""
        try:
            config = ConfigManager.load_config()
            config["window_pos"] = [self.x(), self.y()]
            ConfigManager.save_config(config)
        except Exception as e:
            print(f"保存窗口位置失败: {e}")
        finally:
            QApplication.quit()

    # 窗口拖动功能
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.oldPos = event.globalPos()
            self._register_click()

    def mouseMoveEvent(self, event):
        if self.oldPos is not None:
            delta = event.globalPos() - self.oldPos
            self.move(self.x() + delta.x(), self.y() + delta.y())
            self.oldPos = event.globalPos()

    def mouseReleaseEvent(self, event):
        self.oldPos = None
