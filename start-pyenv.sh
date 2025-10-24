#!/bin/bash

# FinGenius 啟動腳本（使用 pyenv Python 3.12）

echo "🚀 FinGenius 台股分析平台啟動腳本"
echo "================================"

# 設置 pyenv 環境變量
export PYENV_ROOT="$HOME/.pyenv"
export PATH="$PYENV_ROOT/bin:$PATH"
eval "$(pyenv init -)"

# 切換到專案目錄
cd "$(dirname "$0")"

# 確認 Python 版本
PYTHON_VERSION=$(python --version 2>&1)
echo "✓ 使用 Python 版本: $PYTHON_VERSION"

# 檢查虛擬環境
if [ ! -d ".venv" ]; then
    echo "❌ 虛擬環境不存在，請先運行以下命令創建："
    echo "   python -m venv .venv"
    echo "   source .venv/bin/activate"
    echo "   pip install -r requirements-web.txt"
    exit 1
fi

# 激活虛擬環境
echo "✓ 激活虛擬環境..."
source .venv/bin/activate

# 檢查依賴
if ! python -c "import fastapi" 2>/dev/null; then
    echo "❌ 依賴未安裝，正在安裝..."
    pip install -r requirements-web.txt
fi

# 啟動服務器
echo "✓ 啟動 Web 服務器..."
echo "✓ 訪問地址: http://localhost:8000"
echo ""
cd web
python server.py
