@echo off
:: 删除启动项
reg delete "HKCU\Software\Microsoft\Windows\CurrentVersion\Run" /v MyCountdown /f

:: 删除快捷方式
del "%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup\MyCountdown.lnk"

echo 已移除开机自启动
pause