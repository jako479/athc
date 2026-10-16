@echo off
rem Runs INSIDE Windows Sandbox: the installed athc autocontinue, its lines to Desktop\out.
rem A test that needs its own settings puts an athc.ini in assets\config.
if exist "%~dp0config\athc.ini" set "ATHC_CONFIG_DIR=%~dp0config"
"C:\Users\WDAGUtilityAccount\AppData\Local\Programs\Assistant to the Head Coach\athc.exe" autocontinue > C:\Users\WDAGUtilityAccount\Desktop\out\ac-out.txt 2> C:\Users\WDAGUtilityAccount\Desktop\out\ac-err.txt
