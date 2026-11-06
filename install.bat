@echo off
set TARGET=dist\ClassSimple.exe
set SHORTCUT="%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup\ClassSimple.lnk"

:: 创建快捷方式
powershell "$ws = New-Object -ComObject WScript.Shell; $sc = $ws.CreateShortcut(%SHORTCUT%); $sc.TargetPath = '%CD%\%TARGET%'; $sc.Save()"

:: 设置注册表项
reg add "HKCU\Software\Microsoft\Windows\CurrentVersion\Run" /v ClassSimple /t REG_SZ /d "\"%CD%\%TARGET%\" -minimized" /f

echo 已设置开机自启动
pause