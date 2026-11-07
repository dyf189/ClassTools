# ClassTools
## 介绍
基于PyQt5的班级大屏工具集合软件（古法vibe coding，现由 AI 完善并模块化重构）

## 功能模块
### 1. 倒计时（countdown_window.py）
- 设置精确到日/时或者自动调整的考试/重大事件倒计时
- **是否显示倒计时的开关**：设置 → 基本设置 可勾选“在屏幕上显示倒计时”；托盘菜单也有“显示/隐藏倒计时”快捷开关（隐藏后程序仍驻留托盘，随时找回）

### 2. 定时关机（shutdown_manager.py）
- 支持添加**多条**定时关机任务，每条可设置：名称、触发时间、生效星期（周一~周日）、执行动作（关机/重启/睡眠）、是否启用
- 不再调用 Windows 自带的 `shutdown.exe`，而是直接调用系统 API（`ExitWindowsEx`），到点立即执行，**不会再弹出“此计算机将在十分钟后注销”的横幅提示**
- 旧版“每日一次关机”配置会自动迁移为一条任务

### 3. 桌面清理（desktop_cleanup.py）
- 每周固定星期几自动把桌面上的指定类型文件（默认 .ppt/.pptx/.doc/.docx/.jpg）移动到备份目录
- 清理日期、备份目录、文件类型均可在设置中修改，也可手动“立即清理一次”

### 4. 设置（settings_dialog.py）
- 托盘图标右键 → 设置，四个标签页：基本设置（倒计时 + 隐藏页）、定时关机、桌面清理、外观设置

## 运行
```
pip install PyQt5
python main.py
```

## 打包与开机自启
```
pyinstaller -F -w --uac-admin --name ClassSimple main.py
install.bat   # 创建开机自启快捷方式
```
> 关机需要相应权限，建议以管理员身份运行（app.manifest 已声明）。

## 配置文件
所有设置保存在运行目录的 `countdown_config.json`，主要字段：
- `target_time` / `prefix_text` / `display_mode`：普通倒计时
- `show_countdown`：是否在屏幕上显示倒计时
- `shutdown_tasks`：定时关机任务列表（name/time/days/action/enabled）
- `desktop_cleanup`：桌面清理设置（enabled/day_of_week/backup_dir/extensions）
- `style`：字体大小、颜色、透明度

## 许可证
MIT协议
