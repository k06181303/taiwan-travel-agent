"""
app/main.py

FastAPI 應用程式入口。
負責:
  1. 建立 FastAPI app 實例
  2. 掛載路由
  3. 設定 CORS(之後前端串接用)
  4. 啟動時顯示設定資訊(方便 debug)
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import os
from app.api.routes import router
from app.config import settings

# 建立 FastAPI 實例,加上 API 文件說明
app = FastAPI(
    title="Taiwan Travel Agent",
    description="基於 LangGraph + Claude API 的台灣旅遊 AI Agent",
    version="0.1.0",
)

# CORS 設定:Phase 1 先全開,之後可以限制特定 domain
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 掛載 API 路由
app.include_router(router)

# 掛載靜態檔案（前端 HTML/CSS/JS）
_static_dir = os.path.join(os.path.dirname(__file__), "static")
app.mount("/static", StaticFiles(directory=_static_dir), name="static")


@app.get("/", include_in_schema=False)
async def serve_frontend():
    """首頁：回傳前端 HTML"""
    return FileResponse(os.path.join(_static_dir, "index.html"))


@app.on_event("startup")
async def startup_event():
    """啟動時印出設定資訊,方便確認環境正確"""
    print(f"\n{'='*50}")
    print(f"  Taiwan Travel Agent 啟動中...")
    print(f"  環境: {settings.app_env}")
    print(f"  Claude 模型: {settings.claude_model}")
    print(f"  API 文件: http://{settings.app_host}:{settings.app_port}/docs")
    print(f"{'='*50}\n")
