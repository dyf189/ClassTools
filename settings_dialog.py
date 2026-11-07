# -*- coding: utf-8 -*-
"""设置模块：基本设置（倒计时 + 隐藏页）、定时关机、桌面清理、外观设置"""
import json
from datetime import datetime, timedelta

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QDialog, QLabel, QPushButton, QDateTimeEdit,
    QVBoxLayout, QWidget, QDialogButtonBox,
    QFormLayout, QSpinBox, QGridLayout, QSlider,
    QColorDialog, QMessageBox, QLineEdit, QComboBox,
    QGroupBox, QTabWidget
)
from PyQt5.QtGui import QColor

from app_config import ConfigManager, parse_iso_datetime
from shutdown_manager import ShutdownTasksWidget
from desktop_cleanup import DesktopCleanupWidget

GAOKAO_DEFAULT_DATETIME = datetime(2027, 6, 7, 9, 0, 0)


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

        # 定时关机 / 桌面清理 来自各自的模块
        self.shutdown_widget = ShutdownTasksWidget()
        self.cleanup_widget = DesktopCleanupWidget()

        tab_widget.addTab(basic_tab, "基本设置")
        tab_widget.addTab(self.shutdown_widget, "定时关机")
        tab_widget.addTab(self.cleanup_widget, "桌面清理")
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

        # 隐藏页：高考倒计时
        gaokao_group = QGroupBox("隐藏页：高考倒计时（默认不在主界面显示）")
        gaokao_form = QFormLayout(gaokao_group)

        self.gaokao_prefix_input = QLineEdit()
        self.gaokao_prefix_input.setPlaceholderText("例如：距离高考还有")
        gaokao_form.addRow("显示前缀：", self.gaokao_prefix_input)

        self.gaokao_date_edit = QDateTimeEdit()
        self.gaokao_date_edit.setCalendarPopup(True)
        self.gaokao_date_edit.setDisplayFormat("yyyy-MM-dd HH:mm:ss")
        gaokao_form.addRow("目标时间：", self.gaokao_date_edit)

        hint = QLabel("切换方式：在倒计时窗口 2 秒内快速连点 5 次，或按 Ctrl+Alt+G")
        hint.setWordWrap(True)
        gaokao_form.addRow("", hint)

        layout.addRow(gaokao_group)

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

            # 加载隐藏页（高考倒计时）
            gaokao = config.get("gaokao") or {}
            self.gaokao_prefix_input.setText(gaokao.get("prefix_text", "距离高考还有"))
            try:
                gaokao_time = gaokao.get("target_time", "")
                if gaokao_time:
                    self.gaokao_date_edit.setDateTime(parse_iso_datetime(gaokao_time))
                else:
                    self.gaokao_date_edit.setDateTime(GAOKAO_DEFAULT_DATETIME)
            except Exception as e:
                print(f"加载高考倒计时失败: {e}")
                self.gaokao_date_edit.setDateTime(GAOKAO_DEFAULT_DATETIME)

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

            # 加载定时关机 / 桌面清理设置
            self.shutdown_widget.set_tasks(config.get("shutdown_tasks", []))
            self.cleanup_widget.set_config(config.get("desktop_cleanup", {}))

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
            target_datetime = self.datetime_edit.dateTime().toPyDateTime()
            gaokao_datetime = self.gaokao_date_edit.dateTime().toPyDateTime()

            # 保留各配置段里未在界面上编辑的字段
            current = ConfigManager.load_config()

            gaokao_cfg = dict(current.get("gaokao") or {})
            gaokao_cfg["target_time"] = gaokao_datetime.isoformat()
            gaokao_cfg["prefix_text"] = self.gaokao_prefix_input.text() or "距离高考还有"

            cleanup_cfg = dict(current.get("desktop_cleanup") or {})
            cleanup_cfg.update(self.cleanup_widget.get_config())

            new_config = {
                "target_time": target_datetime.isoformat(),
                "prefix_text": self.prefix_input.text(),
                "display_mode": self.display_mode_combo.currentData(),
                "gaokao": gaokao_cfg,
                "shutdown_tasks": self.shutdown_widget.get_tasks(),
                "desktop_cleanup": cleanup_cfg,
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
