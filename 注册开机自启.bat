@echo off
setlocal
set "STARTUP=%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup"
set "LNK=%STARTUP%\AI Simulation Assistant.lnk"
set "TARGET=%~dp0启动AI仿真助手.bat"
powershell -NoProfile -ExecutionPolicy Bypass -Command "$ws=New-Object -ComObject WScript.Shell; $s=$ws.CreateShortcut('%LNK%'); $s.TargetPath='%TARGET%'; $s.Arguments='/silent'; $s.WorkingDirectory='%~dp0'; $s.WindowStyle=7; $s.Save()"
if exist "%LNK%" (echo [ok] Autostart registered.) else (echo [fail] Registration failed.)
pause
