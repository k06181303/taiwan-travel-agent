"""
app/config.py

讀取 .env 環境變數,集中管理所有設定。
使用 pydantic-settings 強型別驗證,避免 API Key 漏填時才在執行期爆炸。
"""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # Anthropic Claude API Key(必填,缺少會在啟動時拋出驗證錯誤)
    anthropic_api_key: str

    # FastAPI 服務設定
    app_env: str = "development"
    app_host: str = "0.0.0.0"
    app_port: int = 8000

    # ChromaDB 向量資料庫持久化路徑
    chroma_persist_dir: str = "./chromadb_data"

    # SQLite 資料庫連線字串(Phase 4 HITL checkpointer 用)
    database_url: str = "sqlite:///./travel_agent.db"

    # Claude 模型設定
    claude_model: str = "claude-sonnet-4-5"
    claude_max_tokens: int = 4096

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )


# 全域單例,其他模組直接 import settings 使用
settings = Settings()
