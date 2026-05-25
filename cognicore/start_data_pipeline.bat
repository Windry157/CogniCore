@echo off
REM CogniCore 数据管道 MVP 快速启动脚本
REM Windows 版本

echo ========================================================
echo   CogniCore 数据管道 MVP - 快速启动
echo ========================================================
echo.

cd /d "%~dp0"

echo [1/3] 检查 Python 环境...
python --version
if errorlevel 1 (
    echo ❌ Python 未安装或未在 PATH 中
    pause
    exit /b 1
)

echo.
echo [2/3] 安装/检查依赖...
pip install aiosqlite
if errorlevel 1 (
    echo 警告: 依赖安装可能失败，但继续尝试运行
)

echo.
echo [3/3] 启动数据管道 MVP 验证...
echo.
python -m src.core.pipeline_validation

echo.
echo ========================================================
echo   ✅ 验证完成！
echo ========================================================
echo.
echo 下一步:
echo   1. 检查 reports/ 目录的 HTML 报告
echo   2. 运行测试: pytest tests/test_pipeline_mvp.py
echo   3. 阅读 DATA_PIPELINE_DESIGN.md 了解架构
echo.
pause
