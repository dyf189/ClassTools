# -*- coding: utf-8 -*-
"""ClassTools 程序入口

模块划分：
  countdown_window.py  倒计时（主窗口 + 隐藏的高考倒计时页）
  shutdown_manager.py  定时关机（多条任务，调用系统 API）
  desktop_cleanup.py   桌面清理（每周定时搬运桌面文件）
  settings_dialog.py   设置（整合上面各模块的设置页）
  app_config.py        配置读写（共用）
  win_helpers.py       Windows 辅助与电源操作（共用）
"""
import sys

from PyQt5.QtWidgets import QApplication

from countdown_window import CountdownWindow
from win_helpers import hide_console, abort_legacy_shutdown


def main():
    try:
        hide_console()
        # 取消旧版本用 shutdown.exe 设置的待执行关机（如有）
        abort_legacy_shutdown()

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


if __name__ == "__main__":
    main()
