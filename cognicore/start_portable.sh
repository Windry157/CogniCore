#!/bin/bash
# ==========================================================
# CogniCore-Portable U盘即插即用启动脚本 (Linux/Mac)
# ==========================================================

echo ""
echo "╔═══════════════════════════════════════════════════════╗"
echo "║      🚀 CogniCore-Portable - U盘即插即用版         ║"
echo "╚═══════════════════════════════════════════════════════╝"
echo ""
echo "[1/5] 检查环境..."

# 切换到脚本所在目录
cd "$(dirname "$0")"

# 检查Python
echo "[2/5] 检查 Python..."
if ! command -v python3 &> /dev/null; then
    echo "❌ Python3 未找到！请先安装 Python 3.8+"
    exit 1
fi
echo "✅ Python 检查通过"

# 设置CONFIG_PATH环境变量
echo "[3/5] 设置便携配置..."
export CONFIG_PATH="$(pwd)/config.yaml"
echo "CONFIG_PATH=$CONFIG_PATH"

# 检查虚拟环境
echo "[4/5] 检查依赖..."
if [ ! -d "venv" ]; then
    echo ""
    echo "⚠️  首次运行，正在创建虚拟环境..."
    python3 -m venv venv
    source venv/bin/activate
    pip install -r requirements.txt
    if [ $? -ne 0 ]; then
        echo "❌ 依赖安装失败！"
        exit 1
    fi
    echo "✅ 依赖安装完成！"
else
    source venv/bin/activate
fi

# 启动服务
echo "[5/5] 启动 CogniCore..."
echo ""
echo "╔═══════════════════════════════════════════════════════╗"
echo "║      服务即将启动，请稍候...                             ║"
echo "║      访问地址: http://localhost:8002                    ║"
echo "╚═══════════════════════════════════════════════════════╝"
echo ""
echo "提示: 按 Ctrl+C 停止服务"
echo ""

python3 app.py
