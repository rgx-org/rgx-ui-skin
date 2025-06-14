@echo off
setlocal

REM ─────────────────────────────────────────────────────────────────
REM Iterate recursively from this script’s folder
for /R "%~dp0" %%F in (*) do (
    REM Compare extension case-insensitive; skip .bmp
    if /I not "%%~xF"==".bmp" (
        echo Deleting "%%F"
        del /F /Q "%%F"
    )
)

endlocal
echo Done.
pause