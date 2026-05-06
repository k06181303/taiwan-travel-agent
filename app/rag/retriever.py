"""
app/rag/retriever.py

兩階段混合檢索：
  Stage 1: 向量檢索(bge-m3) + BM25(jieba) → RRF 融合 → top-20
  Stage 2: bge-reranker-v2-m3 Cross-Encoder → top-k（預設 5）
"""

import json
from pathlib import Path
from typing import Any

import jieba
from rank_bm25 import BM25Okapi
from sentence_transformers import CrossEncoder

from app.rag.embeddings import embed_query
from app.rag.vector_store import (
    COLLECTION_ATTRACTIONS,
    COLLECTION_FOODS,
    query_collection,
)

# ─── Reranker 初始化（全程單例）────────────────────────────
# 使用 sentence-transformers CrossEncoder，相容 transformers 5.x
_reranker: CrossEncoder | None = None


def _get_reranker() -> CrossEncoder:
    global _reranker
    if _reranker is None:
        _reranker = CrossEncoder("BAAI/bge-reranker-v2-m3")
    return _reranker


# ─── BM25 索引（每次 retriever 初始化時從磁碟讀取）──────────
_DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data"


def _load_bm25_index(collection: str) -> tuple[BM25Okapi, list[dict]]:
    """
    從 JSON 讀取資料，jieba 斷詞後建立 BM25 索引。
    回傳 (bm25, items) 供後續使用。
    """
    filename = "attractions.json" if collection == COLLECTION_ATTRACTIONS else "foods.json"
    items: list[dict] = json.loads((_DATA_DIR / filename).read_text(encoding="utf-8"))

    tokenized_corpus = []
    for item in items:
        text = item["description"] + " " + " ".join(item.get("keywords", []))
        tokens = list(jieba.cut(text))
        tokenized_corpus.append(tokens)

    bm25 = BM25Okapi(tokenized_corpus)
    return bm25, items


# ─── RRF 融合 ──────────────────────────────────────────────

def _rrf_fusion(
    vector_results: list[dict],
    bm25_items: list[dict],
    bm25_scores: list[float],
    k: int = 60,
    top_n: int = 20,
) -> list[dict]:
    """
    Reciprocal Rank Fusion：合併向量排名與 BM25 排名。
    k=60 是 RRF 論文的推薦預設值。
    """
    scores: dict[str, float] = {}
    id_to_item: dict[str, dict] = {}

    # 向量檢索排名貢獻
    for rank, doc in enumerate(vector_results):
        doc_id = doc["id"]
        scores[doc_id] = scores.get(doc_id, 0.0) + 1.0 / (k + rank + 1)
        id_to_item[doc_id] = doc

    # BM25 排名貢獻：先依分數排序取 top-n，再計算 RRF
    bm25_ranked = sorted(
        zip(bm25_scores, bm25_items),
        key=lambda x: x[0],
        reverse=True,
    )[:top_n]

    for rank, (score, item) in enumerate(bm25_ranked):
        doc_id = item["id"]
        scores[doc_id] = scores.get(doc_id, 0.0) + 1.0 / (k + rank + 1)
        if doc_id not in id_to_item:
            # BM25 獨有的結果，補充必要欄位
            id_to_item[doc_id] = {
                "id": doc_id,
                "document": item.get("description", ""),
                "metadata": item,
                "distance": 0.0,
            }

    # 依 RRF 分數降序排列，取 top_n
    sorted_ids = sorted(scores, key=lambda x: scores[x], reverse=True)[:top_n]
    return [id_to_item[doc_id] for doc_id in sorted_ids]


# ─── 主檢索函式 ────────────────────────────────────────────

def retrieve(
    query: str,
    collection: str = COLLECTION_ATTRACTIONS,
    top_k: int = 5,
    where: dict | None = None,
) -> list[dict[str, Any]]:
    """
    兩階段混合檢索主入口。

    Args:
        query:      使用者查詢字串
        collection: "attractions" 或 "foods"
        top_k:      最終回傳筆數（reranker 後）
        where:      ChromaDB metadata 過濾，例如 {"city": "台北"}

    Returns:
        list of dict，包含 id / name / document / metadata / score
    """
    # ── Stage 1a：向量檢索 ──────────────────────────────
    query_emb = embed_query(query)
    vector_results = query_collection(
        collection_name=collection,
        query_embedding=query_emb,
        n_results=20,
        where=where,
    )

    # ── Stage 1b：BM25 檢索 ─────────────────────────────
    bm25, items = _load_bm25_index(collection)
    query_tokens = list(jieba.cut(query))
    bm25_scores = bm25.get_scores(query_tokens)

    # ── Stage 1c：RRF 融合 → top-20 ─────────────────────
    fused = _rrf_fusion(
        vector_results=vector_results,
        bm25_items=items,
        bm25_scores=bm25_scores.tolist(),
        top_n=20,
    )

    if not fused:
        return []

    # ── Stage 2：Cross-Encoder Reranking → top-k ────────
    # CrossEncoder.predict() 回傳 numpy array，直接轉 list
    reranker = _get_reranker()
    pairs = [[query, doc["document"]] for doc in fused]
    rerank_scores: list[float] = reranker.predict(pairs).tolist()

    # 附加 rerank score 後排序
    for i, doc in enumerate(fused):
        doc["score"] = float(rerank_scores[i])

    reranked = sorted(fused, key=lambda x: x["score"], reverse=True)[:top_k]

    # 整理輸出格式
    return [
        {
            "id": doc["id"],
            "name": doc["metadata"].get("name", doc["id"]),
            "document": doc["document"],
            "metadata": doc["metadata"],
            "score": doc["score"],
        }
        for doc in reranked
    ]
