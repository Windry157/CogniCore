@echo off
chcp 65001 >nul
title CogniCore 停止
setlocal enabledelayedexpansion

set "ROOT=%~dp0"
set "VENV=%ROOT%venv\Scripts\python.exe"
set "PY_RUN=python"
if exist "%VENV%" set "PY_RUN=%VENV%"

"%PY_RUN%" "%ROOT%run.py" --stop
pause

