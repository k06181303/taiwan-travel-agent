"""
app/rag/embeddings.py

封裝 bge-m3 embedding 模型。
第一次執行會自動從 HuggingFace 下載模型（約 500MB），
之後 cache 在 ~/.cache/huggingface/。
"""

from functools import lru_cache

from sentence_transformers import SentenceTransformer

MODEL_NAME = "BAAI/bge-m3"


@lru_cache(maxsize=1)
def _get_model() -> SentenceTransformer:
    """載入模型（使用 lru_cache 確保全程只初始化一次）"""
    return SentenceTransformer(MODEL_NAME)


def embed_texts(texts: list[str]) -> list[list[float]]:
    """
    將一批文字轉成 bge-m3 向量（1024 維）。

    Args:
        texts: 要 embed 的字串列表
    Returns:
        每筆文字對應的 1024 維浮點數向量列表
    """
    model = _get_model()
    embeddings = model.encode(texts, normalize_embeddings=True)
    return embeddings.tolist()


def embed_query(query: str) -> list[float]:
    """單一查詢字串的 embedding，供 retriever 使用"""
    return embed_texts([query])[0]
