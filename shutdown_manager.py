# -*- coding: utf-8 -*-
"""定时关机模块：多条定时任务（时间/星期/动作），到点直接调用系统 API 关机

不再使用 Windows 自带的 shutdown.exe，因此不会弹出
“此计算机将在十分钟后注销”之类的横幅提示。
"""
import uuid
from datetime import datetime

from PyQt5.QtCore import Qt, QTime, QTimer
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QTableWidget,
    QTableWidgetItem, QDialog, QFormLayout, QLineEdit, QTimeEdit,
    QComboBox, QCheckBox, QDialogButtonBox, QMessageBox, QHeaderView
)

from app_config import ConfigManager, WEEKDAY_NAMES
from win_helpers import power_action

ACTION_LABELS = {"shutdown": "关机", "reboot": "重启", "sleep": "睡眠"}


# ---------- 定时关机调度器 ----------
class ShutdownScheduler(object):
    """每 15 秒检查一次配置里的定时关机任务，到点即执行"""

    def __init__(self, on_action=None):
        self.tasks = []
        self.on_action = on_action  # 触发回调（用于界面提示等）
        self.timer = QTimer()
        self.timer.setInterval(15000)
        self.timer.timeout.connect(self.check)

    def start(self):
        self.reload()
        self.timer.start()

    def reload(self):
        """从配置文件重新读取任务列表（设置保存后也会调用）"""
        try:
            self.tasks = ConfigManager.load_config().get("shutdown_tasks", [])
        except Exception as e:
            print(f"读取定时关机任务失败: {e}")
            self.tasks = []

    def check(self, now=None):
        """检查所有任务，允许传入 now 方便测试"""
        now = now or datetime.now()
        today = now.strftime("%Y-%m-%d")
        weekday = now.isoweekday()
        time_str = now.strftime("%H:%M")
        for task in self.tasks:
            try:
                if self._task_should_fire(task, today, weekday, time_str):
                    self._fire(task)
            except Exception as e:
                print(f"处理定时关机任务出错: {e}")

    @staticmethod
    def _task_should_fire(task, today, weekday, time_str):
        if not task.get("enabled", True):
            return False
        if weekday not in task.get("days", []):
            return False
        # 同一天同一任务只触发一次
        if task.get("last_fired_date") == today:
            return False
        return str(task.get("time", "")) == time_str

    def _fire(self, task):
        name = task.get("name", "未命名")
        action = task.get("action", "shutdown")
        print(f"触发定时任务: {name} ({ACTION_LABELS.get(action, action)})")

        # 先记录触发日期并落盘，避免同一分钟内重复触发
        task["last_fired_date"] = datetime.now().strftime("%Y-%m-%d")
        try:
            ConfigManager.update_config({"shutdown_tasks": self.tasks})
        except Exception as e:
            print(f"保存触发记录失败: {e}")

        if callable(self.on_action):
            try:
                self.on_action(task)
            except Exception:
                pass

        try:
            power_action(action)
        except Exception as e:
            print(f"执行电源操作失败: {e}")


# ---------- 任务编辑对话框 ----------
class ShutdownTaskDialog(QDialog):
    """单条定时关机任务的编辑窗口"""

    def __init__(self, parent=None, task=None):
        super().__init__(parent)
        self.setWindowTitle("编辑定时关机任务" if task else "添加定时关机任务")
        self.setMinimumWidth(460)
        self._task = dict(task) if task else None

        layout = QFormLayout(self)

        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("例如：晚自习结束关机")
        layout.addRow("任务名称：", self.name_input)

        self.time_edit = QTimeEdit()
        self.time_edit.setDisplayFormat("HH:mm")
        layout.addRow("触发时间：", self.time_edit)

        days_widget = QWidget()
        days_layout = QHBoxLayout(days_widget)
        days_layout.setContentsMargins(0, 0, 0, 0)
        self.day_checks = []
        for day_name in WEEKDAY_NAMES:
            check = QCheckBox(day_name)
            self.day_checks.append(check)
            days_layout.addWidget(check)
        layout.addRow("生效星期：", days_widget)

        self.action_combo = QComboBox()
        for key, label in ACTION_LABELS.items():
            self.action_combo.addItem(label, key)
        layout.addRow("执行动作：", self.action_combo)

        self.enabled_check = QCheckBox("启用该任务")
        layout.addRow("", self.enabled_check)

        btn_box = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        btn_box.accepted.connect(self.accept)
        btn_box.rejected.connect(self.reject)
        layout.addRow(btn_box)

        if task:
            self.name_input.setText(task.get("name", ""))
            self._set_time(task.get("time", "21:30"))
            for day in task.get("days", []):
                if 1 <= day <= 7:
                    self.day_checks[day - 1].setChecked(True)
            idx = self.action_combo.findData(task.get("action", "shutdown"))
            if idx >= 0:
                self.action_combo.setCurrentIndex(idx)
            self.enabled_check.setChecked(task.get("enabled", True))
        else:
            self._set_time("21:30")
            for check in self.day_checks:
                check.setChecked(True)
            self.enabled_check.setChecked(True)

    def _set_time(self, time_str):
        try:
            hour, minute = map(int, str(time_str).split(":"))
            self.time_edit.setTime(QTime(hour, minute))
        except Exception:
            self.time_edit.setTime(QTime(21, 30))

    def get_task(self):
        days = [i + 1 for i, check in enumerate(self.day_checks) if check.isChecked()]
        if self._task:
            new_task = dict(self._task)
        else:
            new_task = {"id": uuid.uuid4().hex[:8]}
        t = self.time_edit.time()
        new_task.update({
            "name": self.name_input.text().strip() or "定时关机",
            "time": f"{t.hour():02d}:{t.minute():02d}",
            "days": days if days else [1, 2, 3, 4, 5, 6, 7],
            "action": self.action_combo.currentData(),
            "enabled": self.enabled_check.isChecked(),
        })
        return new_task


# ---------- 任务管理面板 ----------
class ShutdownTasksWidget(QWidget):
    """定时关机任务管理（作为设置对话框的一个标签页）"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.tasks = []  # 编辑中的任务副本（点“保存”后才写入配置）
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)

        tip = QLabel("到点后直接调用系统 API 关机，不会再弹出“此计算机将在几分钟后注销”提示")
        tip.setWordWrap(True)
        layout.addWidget(tip)

        self.table = QTableWidget(0, 5)
        self.table.setHorizontalHeaderLabels(["名称", "时间", "星期", "动作", "启用"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setSelectionMode(QTableWidget.SingleSelection)
        layout.addWidget(self.table)

        btn_row = QHBoxLayout()
        add_btn = QPushButton("添加任务")
        add_btn.clicked.connect(self.add_task)
        edit_btn = QPushButton("编辑")
        edit_btn.clicked.connect(self.edit_task)
        del_btn = QPushButton("删除")
        del_btn.clicked.connect(self.delete_task)
        btn_row.addWidget(add_btn)
        btn_row.addWidget(edit_btn)
        btn_row.addWidget(del_btn)
        btn_row.addStretch()
        layout.addLayout(btn_row)

    def set_tasks(self, tasks):
        self.tasks = [dict(task) for task in tasks]
        self.refresh_table()

    def get_tasks(self):
        return self.tasks

    def refresh_table(self):
        self.table.setRowCount(len(self.tasks))
        for row, task in enumerate(self.tasks):
            days = task.get("days", [])
            if days and len(days) == 7:
                days_text = "每天"
            else:
                days_text = "、".join(
                    WEEKDAY_NAMES[d - 1] for d in sorted(days) if 1 <= d <= 7
                )
            values = [
                task.get("name", ""),
                task.get("time", ""),
                days_text,
                ACTION_LABELS.get(task.get("action", "shutdown"), "关机"),
                "是" if task.get("enabled", True) else "否",
            ]
            for col, text in enumerate(values):
                item = QTableWidgetItem(str(text))
                item.setTextAlignment(Qt.AlignCenter)
                self.table.setItem(row, col, item)

    def add_task(self):
        dialog = ShutdownTaskDialog(self)
        if dialog.exec_() == QDialog.Accepted:
            self.tasks.append(dialog.get_task())
            self.refresh_table()

    def edit_task(self):
        row = self.table.currentRow()
        if row < 0 or row >= len(self.tasks):
            QMessageBox.information(self, "提示", "请先选中一个任务")
            return
        old_task = self.tasks[row]
        dialog = ShutdownTaskDialog(self, old_task)
        if dialog.exec_() == QDialog.Accepted:
            new_task = dialog.get_task()
            # 触发时间变了就清除已触发记录，让新时间当天生效
            if new_task.get("time") != old_task.get("time"):
                new_task.pop("last_fired_date", None)
            self.tasks[row] = new_task
            self.refresh_table()

    def delete_task(self):
        row = self.table.currentRow()
        if row < 0 or row >= len(self.tasks):
            QMessageBox.information(self, "提示", "请先选中一个任务")
            return
        name = self.tasks[row].get("name", "")
        if QMessageBox.question(self, "确认", f"确定删除任务“{name}”吗？") == QMessageBox.Yes:
            del self.tasks[row]
            self.refresh_table()
