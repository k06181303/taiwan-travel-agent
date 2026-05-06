"""
app/rag/vector_store.py

ChromaDB 向量資料庫的初始化與操作封裝。
資料持久化到專案根目錄的 chromadb_data/ 資料夾。
"""

import threading
from pathlib import Path
from typing import Any

import chromadb
from chromadb.config import Settings

# 持久化路徑：專案根目錄 / chromadb_data
_DB_PATH = str(Path(__file__).resolve().parent.parent.parent / "chromadb_data")

COLLECTION_ATTRACTIONS = "attractions"
COLLECTION_FOODS = "foods"

# ChromaDB Rust binding 在多執行緒時不能共用同一個 client 實例
# 使用 thread-local storage，每個執行緒各自持有一個 client
_thread_local = threading.local()


def _get_client() -> chromadb.PersistentClient:
    """
    取得當前執行緒的 ChromaDB client。
    LangGraph fan-out 會在多個執行緒中並行呼叫，每個執行緒需要獨立的 client。
    """
    if not hasattr(_thread_local, "client"):
        _thread_local.client = chromadb.PersistentClient(
            path=_DB_PATH,
            settings=Settings(anonymized_telemetry=False),
        )
    return _thread_local.client


def get_collection(name: str) -> chromadb.Collection:
    """取得（或建立）指定 collection"""
    client = _get_client()
    return client.get_or_create_collection(
        name=name,
        metadata={"hnsw:space": "cosine"},  # 用 cosine 相似度
    )


def upsert_documents(
    collection_name: str,
    ids: list[str],
    embeddings: list[list[float]],
    documents: list[str],
    metadatas: list[dict[str, Any]],
) -> None:
    """
    批次寫入（或更新）向量資料。

    Args:
        collection_name: "attractions" 或 "foods"
        ids:             每筆資料的唯一 ID
        embeddings:      對應的 1024 維向量
        documents:       原始文字（供 BM25 / 全文搜尋用）
        metadatas:       結構化欄位（city、type 等，供 metadata 過濾用）
    """
    collection = get_collection(collection_name)
    collection.upsert(
        ids=ids,
        embeddings=embeddings,
        documents=documents,
        metadatas=metadatas,
    )


def query_collection(
    collection_name: str,
    query_embedding: list[float],
    n_results: int = 20,
    where: dict | None = None,
) -> list[dict[str, Any]]:
    """
    向量相似度查詢。

    Args:
        collection_name:  "attractions" 或 "foods"
        query_embedding:  查詢字串的 1024 維向量
        n_results:        回傳筆數（預設 20，供 reranker 使用）
        where:            metadata 過濾條件，例如 {"city": "台北"}

    Returns:
        list of dict，每筆包含 id / document / metadata / distance
    """
    collection = get_collection(collection_name)
    kwargs: dict[str, Any] = {
        "query_embeddings": [query_embedding],
        "n_results": n_results,
        "include": ["documents", "metadatas", "distances"],
    }
    if where:
        kwargs["where"] = where

    results = collection.query(**kwargs)

    # 攤平 ChromaDB 的巢狀結構，回傳扁平 list
    ids = results["ids"][0]
    documents = results["documents"][0]
    metadatas = results["metadatas"][0]
    distances = results["distances"][0]

    return [
        {
            "id": ids[i],
            "document": documents[i],
            "metadata": metadatas[i],
            "distance": distances[i],
        }
        for i in range(len(ids))
    ]


def count_documents(collection_name: str) -> int:
    """回傳 collection 目前的資料筆數"""
    return get_collection(collection_name).count()
