#!/bin/bash
# HF Spaces 啟動腳本
# 先初始化 ChromaDB 向量資料，再啟動 FastAPI server

set -e

echo "=== Taiwan Travel Agent 啟動中 ==="

# 初始化向量資料庫（若已有資料會自動跳過）
echo ">>> 初始化 ChromaDB..."
python scripts/seed.py

echo ">>> 啟動 FastAPI server..."
exec uvicorn app.main:app --host 0.0.0.0 --port 7860
