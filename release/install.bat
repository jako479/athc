@ECHO OFF
SETLOCAL

cd /d "%~dp0"

echo Installing athc...
echo.

REM uv must be on PATH. Install once with:  winget install --id=astral-sh.uv -e
where uv >NUL 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo ERROR: 'uv' was not found on PATH.
    echo Install it once, then re-run this script:
    echo     winget install --id=astral-sh.uv -e
    goto :error
)

REM Install athc into an isolated uv-tool environment from the bundled wheel.
REM uv pulls the dependencies from PyPI, so this step needs internet.
REM --reinstall replaces any prior athc install so the user ends up on exactly
REM this zip's version.
for %%w in (athc-*.whl) do uv tool install "%%w" --reinstall
if %ERRORLEVEL% NEQ 0 goto :error

REM Make sure uv's tool directory is on PATH (no-op if already there).
uv tool update-shell

REM Deploy files to the athc config folder.
REM   - Docs and the rules\ folder are shipped reference material -> always
REM     overwrite (no guard). Users copy a rule file before editing their own.
REM   - athc.ini is user-owned -> guard with 'if not exist' so user edits survive.
REM     New tool sections take effect via in-code defaults; the freshly-extracted
REM     athc.ini in this zip is the always-current reference of every setting.
set "DEST=%LOCALAPPDATA%\athc"
if not exist "%DEST%" mkdir "%DEST%"
if not exist "%DEST%\rules" mkdir "%DEST%\rules"
if not exist "%DEST%\docs" mkdir "%DEST%\docs"

copy /Y "docs\*.txt"   "%DEST%\docs\"  >NUL
copy /Y "rules\*.toml" "%DEST%\rules\" >NUL
if not exist "%DEST%\athc.ini" copy /Y "athc.ini" "%DEST%\athc.ini" >NUL

REM Season config (<season>.league.ini / <season>.nonconf_history.json) is
REM commissioner-owned -> guard per file so edits survive a reinstall.
for %%f in (*.league.ini *.nonconf_history.json) do if not exist "%DEST%\%%f" copy /Y "%%f" "%DEST%\%%f" >NUL

echo.
echo ============================================
echo   athc Installation Successful!
echo ============================================
echo.
echo The 'athc' command is now available from any terminal.
echo (If 'athc' is not found, open a NEW terminal so PATH refreshes.)
echo.
echo Usage:
echo   athc --help                  list available commands
echo   athc ^<command^> --help        show help for a specific command
echo.
echo Your settings and docs live at:
echo   %DEST%
echo.
echo See docs\COMMANDS.txt for what each tool does and examples.
echo docs\README.txt covers setup and troubleshooting.
echo.
echo To remove:  uv tool uninstall athc
echo ============================================
echo.
pause
exit /b 0

:error
echo.
echo ERROR: Installation failed. See above for details.
pause
exit /b 1
