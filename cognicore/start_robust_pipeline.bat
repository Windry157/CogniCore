@echo off
REM CogniCore 工业级数据管道 - 快速启动
REM Windows 版本

echo ========================================================
echo   🔥 CogniCore - 工业级数据管道
echo ========================================================
echo.
echo   包含:
echo     ✅ 重试机制 + 指数退避
echo     ✅ 幂等性处理
echo     ✅ 死信队列 (DLQ)
echo     ✅ 数据校验层
echo     ✅ 监控与可观测性
echo.

cd /d "%~dp0"

echo [1/2] 检查 Python 环境...
python --version
if errorlevel 1 (
    echo ❌ Python 未安装或未在 PATH 中
    pause
    exit /b 1
)

echo.
echo [2/2] 启动工业级管道验证...
echo.
python -m src.core.robust_data_pipeline

echo.
echo ========================================================
echo   🎉 工业级数据管道验证完成！
echo ========================================================
echo.
echo 检查结果:
echo   - data/pipeline.db (主数据库)
echo   - data/pipeline.db (DLQ 表已创建)
echo.
pause
