@echo off
setlocal
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\preview_lvbu.ps1"
if errorlevel 1 pause
