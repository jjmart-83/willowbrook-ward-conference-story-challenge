@echo off
setlocal
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0conference-game\Start-ConferenceGame.ps1"
if errorlevel 1 pause
endlocal
