# Taiwan Travel Agent - Dockerfile
#
# Base: python:3.11-slim（精簡版，約 120MB）
# 注意：sentence-transformers + torch（CPU）安裝後 image 約 3-4GB
# 首次 build 需要較長時間（下載模型權重）

FROM python:3.11-slim

# 設定工作目錄
WORKDIR /app

# 安裝系統依賴
# build-essential：編譯 chromadb Rust binding 所需
# curl：健康檢查 curl 指令
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# 先複製 requirements.txt，利用 Docker layer cache
# 只有 requirements.txt 改變時才重新安裝套件
COPY requirements.txt .

# 安裝 Python 套件
# --no-cache-dir：不保留 pip 快取，減少 image 大小
RUN pip install --no-cache-dir -r requirements.txt \
    # torch CPU-only 版本，節省約 1.5GB
    && pip install --no-cache-dir torch --index-url https://download.pytorch.org/whl/cpu

# 複製專案程式碼
COPY app/ ./app/
COPY data/ ./data/
COPY scripts/ ./scripts/
COPY pyproject.toml .

# 建立 ChromaDB 資料目錄（volume mount 的掛載點）
RUN mkdir -p chromadb_data

# 暴露 FastAPI 埠號
EXPOSE 8000

# 健康檢查：每 30 秒確認 /health endpoint
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# 啟動指令
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
