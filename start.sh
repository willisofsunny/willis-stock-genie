#!/bin/bash

# FinGenius 啟動腳本

echo "🚀 正在啟動 FinGenius 台股 AI 分析平台..."
echo ""

# 檢查 Python 版本
if ! command -v python3 &> /dev/null; then
    echo "❌ 錯誤：未找到 Python 3"
    echo "請先安裝 Python 3.12 或更高版本"
    exit 1
fi

# 顯示 Python 版本
PYTHON_VERSION=$(python3 --version)
echo "✅ 檢測到 $PYTHON_VERSION"

# 檢查虛擬環境
if [ ! -d ".venv" ]; then
    echo "⚠️  未找到虛擬環境，正在創建..."
    python3 -m venv .venv
    echo "✅ 虛擬環境創建完成"
fi

# 激活虛擬環境
echo "🔧 激活虛擬環境..."
source .venv/bin/activate

# 檢查依賴（跳過以加快啟動速度）
echo "⏭️  跳過依賴檢查（如需重新安裝，請執行：pip install -r requirements.txt）"

# 檢查配置檔案
if [ ! -f "config/config.toml" ]; then
    echo "⚠️  警告：未找到 config/config.toml"
    echo "請先配置您的 API Key"
    exit 1
fi

# 啟動服務器
echo ""
echo "================================================"
echo "    FinGenius 台股 AI 分析平台"
echo "================================================"
echo ""
cd web
python3 server.py
