@echo off
chcp 65001 >nul
REM ==========================================================
REM CogniCore-Portable U盘即插即用启动脚本 (Windows)
REM 委托 run.py 处理 Ollama 检测回退逻辑
REM ==========================================================
title CogniCore-Portable
echo.
echo ========================================================
echo      CogniCore-Portable - U盘即插即用版
echo ========================================================
echo.

cd /d "%~dp0\.."
set "PYTHON=%~dp0..\python\python.exe"
if not exist "%PYTHON%" (
    echo [ERROR] Bundled Python not found at %PYTHON%
    pause
    exit /b 1
)
"%PYTHON%" -u run.py
pause
