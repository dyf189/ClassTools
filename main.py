import sys
import json
import os
from datetime import datetime, timedelta

from PyQt5.QtCore import Qt, QTimer, QTime
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QLabel, QPushButton, QDialog,
    QDateTimeEdit, QVBoxLayout, QSystemTrayIcon, QMenu,
    QStyle, QTabWidget, QWidget, QDialogButtonBox,
    QFormLayout, QSpinBox, QGridLayout, QSlider,
    QColorDialog, QMessageBox, QLineEdit, QComboBox,
    QCheckBox, QTimeEdit
)
from PyQt5.QtGui import QColor, QFont

import ctypes
import subprocess
import shutil


# ---------- 隐藏控制台窗口 ----------
def hide_console():
    """隐藏控制台窗口"""
    try:
        console_window = ctypes.windll.kernel32.GetConsoleWindow()
        if console_window != 0:
            # 获取控制台窗口标题
            title = ctypes.create_unicode_buffer(256)
            ctypes.windll.kernel32.GetConsoleTitleW(title, 256)
            # 隐藏控制台
            ctypes.windll.user32.ShowWindow(console_window, 0)  # 0 = SW_HIDE
            print("控制台已隐藏")
    except Exception as e:
        pass  # 静默处理，不影响程序运行
    

# ---------- 修复后的 Windows API 相关（隐藏任务栏图标） ----------
def hide_from_taskbar(window):
    """兼容不同Python/Windows版本的隐藏任务栏方法"""
    if sys.platform != 'win32':
        return

    try:
        hwnd = int(window.winId())

        # 尝试多种API函数名
        GWL_EXSTYLE = -20
        WS_EX_TOOLWINDOW = 0x00000080
        WS_EX_APPWINDOW = 0x00040000

        user32 = ctypes.windll.user32
        
        # 尝试不同的函数名
        set_func = None
        get_func = None
        
        for func_name in ['SetWindowLongPtrW', 'SetWindowLongW', 'SetWindowLongA']:
            if hasattr(user32, func_name):
                set_func = getattr(user32, func_name)
                break
                
        for func_name in ['GetWindowLongPtrW', 'GetWindowLongW', 'GetWindowLongA']:
            if hasattr(user32, func_name):
                get_func = getattr(user32, func_name)
                break

        if set_func and get_func:
            # 获取当前样式
            ex_style = get_func(hwnd, GWL_EXSTYLE)
            # 修改样式
            new_ex_style = (ex_style & ~WS_EX_APPWINDOW) | WS_EX_TOOLWINDOW
            # 设置新样式
            set_func(hwnd, GWL_EXSTYLE, new_ex_style)
            
            # 刷新窗口
            user32.ShowWindow(hwnd, 0)
            window.show()
            return True
            
    except Exception as e:
        print(f"隐藏任务栏失败（将使用普通模式）: {e}")
        return False


# ---------- 辅助功能 ----------
def weekly_backup():
    """每周一自动备份桌面指定类型文件到 D:\桌面备份"""
    if datetime.today().isoweekday() != 1:
        return

    desktop = os.path.join(os.environ['USERPROFILE'], 'Desktop')
    backup_dir = r"D:\桌面备份"
    extensions = {'.ppt', '.pptx', '.doc', '.docx', '.jpg'}
    
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
                except Exception as e:
                    print(f"移动失败 {filename}: {e}")
    except Exception as e:
        print(f"备份过程出错: {e}")

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
        "auto_shutdown_enabled": True,
        "shutdown_time": "21:00",
        "style": {
            "font_size": 48,
            "text_color": "#FFD700",
            "opacity": 0.9
        }
    }

    @classmethod
    def load_config(cls):
        """加载配置，确保所有必需字段存在"""
        try:
            if os.path.exists(cls.CONFIG_FILE):
                with open(cls.CONFIG_FILE, 'r', encoding='utf-8') as f:
                    saved = json.load(f)
                
                # 深度合并默认配置，确保所有字段存在
                config = cls.DEFAULT_CONFIG.copy()
                cls._deep_update(config, saved)
                return config
        except Exception as e:
            print(f"配置加载失败，使用默认配置: {e}")
        
        return cls.DEFAULT_CONFIG.copy()

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


# ---------- 设置对话框 ----------
class SettingsDialog(QDialog):
    def __init__(self, main_window, parent=None):
        super().__init__(parent)
        self.main_window = main_window
        self.setWindowTitle("高级设置")
        self.setMinimumSize(800, 600)
        self.setStyleSheet("QDialog { background: #F5F5F5; }")
        self.selected_color = QColor("#FFD700")  # 初始化默认颜色
        self.init_ui()
        self.load_settings()

    def init_ui(self):
        main_layout = QVBoxLayout()
        tab_widget = QTabWidget()

        basic_tab = QWidget()
        style_tab = QWidget()
        self.init_basic_tab(basic_tab)
        self.init_style_tab(style_tab)

        tab_widget.addTab(basic_tab, "基本设置")
        tab_widget.addTab(style_tab, "外观设置")
        main_layout.addWidget(tab_widget)

        btn_box = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        btn_box.accepted.connect(self.save_settings)
        btn_box.rejected.connect(self.reject)
        main_layout.addWidget(btn_box)

        self.setLayout(main_layout)

    def init_basic_tab(self, tab):
        layout = QFormLayout()

        self.prefix_input = QLineEdit()
        self.prefix_input.setPlaceholderText("例如：距离中考还有")
        layout.addRow("显示前缀：", self.prefix_input)

        self.datetime_edit = QDateTimeEdit()
        self.datetime_edit.setCalendarPopup(True)
        self.datetime_edit.setDisplayFormat("yyyy-MM-dd HH:mm:ss")
        layout.addRow("目标时间：", self.datetime_edit)

        self.display_mode_combo = QComboBox()
        self.display_mode_combo.addItem("自动 (小于1天显示小时)", "auto")
        self.display_mode_combo.addItem("仅显示天数", "days_only")
        self.display_mode_combo.addItem("始终显示 天+小时", "days_hours")
        layout.addRow("显示模式：", self.display_mode_combo)

        self.font_size_spin = QSpinBox()
        self.font_size_spin.setRange(12, 128)
        self.font_size_spin.setSuffix(" px")
        layout.addRow("字体大小：", self.font_size_spin)

        # 每日关机设置
        shutdown_widget = QWidget()
        shutdown_layout = QVBoxLayout(shutdown_widget)
        shutdown_layout.setContentsMargins(0, 0, 0, 0)
        
        self.shutdown_enabled_check = QCheckBox("启用每日自动关机")
        self.shutdown_time_edit = QTimeEdit()
        self.shutdown_time_edit.setDisplayFormat("HH:mm")
        
        shutdown_layout.addWidget(self.shutdown_enabled_check)
        shutdown_layout.addWidget(self.shutdown_time_edit)
        
        layout.addRow("自动关机：", shutdown_widget)
        self.shutdown_enabled_check.toggled.connect(self.shutdown_time_edit.setEnabled)

        tab.setLayout(layout)

    def init_style_tab(self, tab):
        layout = QGridLayout()

        self.color_btn = QPushButton("选择文字颜色")
        self.color_btn.clicked.connect(self.choose_color)
        self.color_btn.setMinimumHeight(40)
        layout.addWidget(QLabel("文字颜色："), 0, 0)
        layout.addWidget(self.color_btn, 0, 1)

        self.opacity_slider = QSlider(Qt.Horizontal)
        self.opacity_slider.setRange(30, 100)
        self.opacity_slider.setTickPosition(QSlider.TicksBelow)
        self.opacity_slider.setTickInterval(10)
        layout.addWidget(QLabel("窗口透明度："), 1, 0)
        layout.addWidget(self.opacity_slider, 1, 1)
        
        self.opacity_label = QLabel("90%")
        layout.addWidget(self.opacity_label, 1, 2)
        self.opacity_slider.valueChanged.connect(
            lambda v: self.opacity_label.setText(f"{v}%")
        )

        tab.setLayout(layout)

    def load_settings(self):
        """从配置文件加载设置到界面"""
        try:
            config = ConfigManager.load_config()
            
            # 加载前缀
            self.prefix_input.setText(config.get("prefix_text", ""))
            
            # 加载目标时间
            try:
                target_time = config.get("target_time", "")
                if target_time:
                    self.datetime_edit.setDateTime(parse_iso_datetime(target_time))
                else:
                    self.datetime_edit.setDateTime(datetime.now() + timedelta(days=100))
            except Exception as e:
                    print(f"加载目标时间失败: {e}")
                    self.datetime_edit.setDateTime(datetime.now() + timedelta(days=100))

            # 加载显示模式
            mode = config.get("display_mode", "auto")
            idx = self.display_mode_combo.findData(mode)
            if idx >= 0:
                self.display_mode_combo.setCurrentIndex(idx)

            # 加载样式设置
            style = config.get("style", {})
            
            font_size = style.get("font_size", 48)
            self.font_size_spin.setValue(font_size)
            
            opacity = style.get("opacity", 0.9)
            opacity_percent = int(opacity * 100)
            self.opacity_slider.setValue(opacity_percent)

            # 加载颜色
            color_str = style.get("text_color", "#FFD700")
            self.selected_color = QColor(color_str)
            if self.selected_color.isValid():
                self.update_color_button()

            # 加载关机设置
            self.shutdown_enabled_check.setChecked(config.get("auto_shutdown_enabled", True))
            shutdown_time_str = config.get("shutdown_time", "21:00")
            try:
                hour, minute = map(int, shutdown_time_str.split(":"))
                self.shutdown_time_edit.setTime(QTime(hour, minute))
            except Exception:
                self.shutdown_time_edit.setTime(QTime(21, 0))
            
            self.shutdown_time_edit.setEnabled(self.shutdown_enabled_check.isChecked())
            
        except Exception as e:
            print(f"加载设置时出错: {e}")
            QMessageBox.warning(self, "警告", f"加载设置失败: {str(e)}")

    def update_color_button(self):
        """更新颜色按钮的外观"""
        if self.selected_color.isValid():
            color_name = self.selected_color.name()
            # 根据颜色亮度设置文字颜色
            brightness = (self.selected_color.red() * 299 + 
                         self.selected_color.green() * 587 + 
                         self.selected_color.blue() * 114) / 1000
            text_color = "black" if brightness > 128 else "white"
            
            self.color_btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: {color_name};
                    color: {text_color};
                    border: 2px solid #555;
                    border-radius: 5px;
                    padding: 5px;
                    font-weight: bold;
                }}
            """)
            self.color_btn.setText(f"当前颜色: {color_name}")

    def save_settings(self):
        """保存设置到配置文件"""
        try:
            # 收集所有设置
            shutdown_time = self.shutdown_time_edit.time()
            shutdown_time_str = f"{shutdown_time.hour():02d}:{shutdown_time.minute():02d}"
            
            target_datetime = self.datetime_edit.dateTime().toPyDateTime()
            
            new_config = {
                "target_time": target_datetime.isoformat(),
                "prefix_text": self.prefix_input.text(),
                "display_mode": self.display_mode_combo.currentData(),
                "auto_shutdown_enabled": self.shutdown_enabled_check.isChecked(),
                "shutdown_time": shutdown_time_str,
                "style": {
                    "font_size": self.font_size_spin.value(),
                    "text_color": self.selected_color.name() if self.selected_color.isValid() else "#FFD700",
                    "opacity": self.opacity_slider.value() / 100.0
                }
            }
            
            # 验证数据
            print(f"准备保存的配置: {json.dumps(new_config, indent=2, ensure_ascii=False)}")
            
            # 保存配置
            if ConfigManager.update_config(new_config):
                # 通知主窗口刷新
                if hasattr(self.main_window, 'apply_settings'):
                    self.main_window.apply_settings()
                QMessageBox.information(self, "成功", "设置已保存并生效！")
                self.accept()
            else:
                QMessageBox.warning(self, "错误", 
                    "配置文件保存失败！\n\n可能的原因：\n"
                    "1. 文件被其他程序占用\n"
                    "2. 磁盘空间不足\n"
                    "3. 文件夹权限不足\n\n"
                    "请检查后重试。")
                    
        except Exception as e:
            print(f"保存设置时出错: {e}")
            QMessageBox.critical(self, "错误", f"保存设置时发生错误:\n{str(e)}")

    def choose_color(self):
        """打开颜色选择对话框"""
        try:
            dialog = QColorDialog(self.selected_color, self)
            dialog.setOption(QColorDialog.DontUseNativeDialog, True)
            dialog.setWindowTitle("选择文字颜色")
            
            if dialog.exec_() == QDialog.Accepted:
                color = dialog.selectedColor()
                if color.isValid():
                    self.selected_color = color
                    self.update_color_button()
        except Exception as e:
            print(f"颜色选择失败: {e}")
            QMessageBox.warning(self, "错误", f"颜色选择失败: {str(e)}")


# ---------- 主窗口 ----------
class CountdownWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.oldPos = None
        self.target_time = datetime.now()
        self.display_mode = "auto"
        self.prefix_text = ""

        self.init_ui()
        self.init_tray()
        self.apply_settings()
        self.init_timer()
        
        # 在窗口完全初始化后再尝试隐藏任务栏
        hide_from_taskbar(self)

    def init_ui(self):
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        self.setFixedSize(1200, 200)
        self.setWindowTitle("倒计时")

        self.label = QLabel('加载中...', self)
        self.label.setAlignment(Qt.AlignCenter)
        self.label.setFont(QFont('HarmonyOS Sans SC', 48))
        self.setCentralWidget(self.label)

    def apply_settings(self):
        """从配置文件重新加载设置并应用到界面"""
        try:
            config = ConfigManager.load_config()

            # 目标时间
            try:
                target_str = config.get("target_time", "")
                if target_str:
                    self.target_time = parse_iso_datetime(target_str)
                else:
                    self.target_time = datetime.now() + timedelta(days=100)
            except Exception as e:
                print(f"解析目标时间失败: {e}")
                self.target_time = datetime.now() + timedelta(days=100)

            # 前缀与显示模式
            self.prefix_text = config.get("prefix_text", "")
            self.display_mode = config.get("display_mode", "auto")

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

            # 设置或取消自动关机
            self.setup_auto_shutdown(config)

            # 立即刷新倒计时
            self.update_countdown()
            
        except Exception as e:
            print(f"应用设置时出错: {e}")

    def setup_auto_shutdown(self, config):
        """根据配置执行每日关机计划"""
        try:
            # 先取消已有计划
            subprocess.run("shutdown /a", shell=True, capture_output=True)
        except Exception:
            pass

        if not config.get("auto_shutdown_enabled", True):
            print("自动关机已禁用")
            return

        shutdown_time_str = config.get("shutdown_time", "21:00")
        try:
            hour, minute = map(int, shutdown_time_str.split(":"))
        except Exception:
            hour, minute = 21, 0

        now = datetime.now()
        target = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
        if now >= target:
            target += timedelta(days=1)

        delta_seconds = (target - now).total_seconds()
        if delta_seconds <= 0:
            return

        cmd = f"shutdown /s /t {int(delta_seconds)}"
        try:
            subprocess.run(cmd, shell=True, check=True)
            print(f"自动关机已设置: {shutdown_time_str} (剩余{int(delta_seconds)}秒)")
        except subprocess.CalledProcessError as e:
            print(f"自动关机设置失败: {e}")

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

    def update_countdown(self):
        """更新倒计时显示"""
        try:
            now = datetime.now()
            delta = self.target_time - now
            total_seconds = delta.total_seconds()

            if total_seconds <= 0:
                text = f"{self.prefix_text}0天 (已经到达)"
                self.label.setText(text)
                return

            if self.display_mode == "days_only":
                days = delta.days
                text = f"{self.prefix_text}{days}天"
            elif self.display_mode == "days_hours":
                days = delta.days
                hours = delta.seconds // 3600
                text = f"{self.prefix_text}{days}天{hours}小时"
            else:  # auto
                if total_seconds < 86400:  # 小于1天
                    hours = total_seconds // 3600
                    minutes = (total_seconds % 3600) // 60
                    seconds = total_seconds % 60
                    if hours > 0:
                        text = f"{self.prefix_text}{int(hours)}小时{int(minutes)}分钟"
                    else:
                        text = f"{self.prefix_text}{int(minutes)}分钟{int(seconds)}秒"
                else:
                    days = delta.days
                    hours = delta.seconds // 3600
                    text = f"{self.prefix_text}{days}天"

            self.label.setText(text)
            
        except Exception as e:
            print(f"更新倒计时出错: {e}")

    def show_settings(self):
        """显示设置对话框"""
        dialog = SettingsDialog(self, self)
        dialog.exec_()

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

    def mouseMoveEvent(self, event):
        if self.oldPos is not None:
            delta = event.globalPos() - self.oldPos
            self.move(self.x() + delta.x(), self.y() + delta.y())
            self.oldPos = event.globalPos()

    def mouseReleaseEvent(self, event):
        self.oldPos = None


# ---------- 程序入口 ----------
if __name__ == "__main__":
    try:
        hide_console()
        # 启动时运行一次备份（每周一）
        weekly_backup()

        app = QApplication(sys.argv)
        
        # 设置应用程序样式
        app.setStyle('Fusion')
        
        window = CountdownWindow()
        window.show()
        
        print("程序已启动，右键系统托盘图标可进行设置")
        
        sys.exit(app.exec_())
        
    except Exception as e:
        print(f"程序启动失败: {e}")
        input("按回车键退出...")
