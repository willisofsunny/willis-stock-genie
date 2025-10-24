#!/bin/bash

# FinGenius 快速啟動腳本（不檢查依賴）

echo "🚀 快速啟動 FinGenius 台股 AI 分析平台..."
echo ""

# 激活虛擬環境
if [ -d ".venv" ]; then
    source .venv/bin/activate
    echo "✅ 虛擬環境已激活"
else
    echo "❌ 錯誤：未找到虛擬環境 (.venv)"
    echo "請先運行：python3 -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt"
    exit 1
fi

# 啟動服務器
echo ""
echo "================================================"
echo "    FinGenius 台股 AI 分析平台"
echo "    訪問: http://localhost:8000"
echo "================================================"
echo ""
cd web
python3 server.py
