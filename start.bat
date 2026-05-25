@echo off
chcp 65001 >nul
title CogniCore 便携AI
setlocal enabledelayedexpansion

set "ROOT=%~dp0"
set "PYTHON=%ROOT%python\python.exe"
set "VENV=%ROOT%venv\Scripts\python.exe"
set "PY_RUN=python"

"%ROOT%python\python.exe" --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [C++] 检测到缺少 VC++ 运行库，正在安装...
    "%ROOT%redist\vc_redist.x64.exe" /install /quiet /norestart
)

if exist "%VENV%" set "PY_RUN=%VENV%"
if not exist "%VENV%" if exist "%PYTHON%" set "PY_RUN=%PYTHON%"

if "!PY_RUN!"=="python" (
    echo [设置] 未找到便携Python，正在自动配置...
    PowerShell -ExecutionPolicy Bypass -File "%ROOT%bootstrap.ps1" -SkipOllama
    if exist "%PYTHON%" set "PY_RUN=%PYTHON%"
    if exist "%VENV%" set "PY_RUN=%VENV%"
)

"%PY_RUN%" "%ROOT%run.py"
if %errorlevel% neq 0 (
    echo [错误] 启动失败
    echo 如果提示 VCRUNTIME140.dll 丢失，请手动双击 redist\vc_redist.x64.exe 安装
    pause
)

