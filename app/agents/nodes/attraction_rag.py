"""
app/agents/nodes/attraction_rag.py

景點 RAG 節點：根據 intent 建構查詢字串，
呼叫兩階段混合檢索（bge-m3 + BM25 + RRF + CrossEncoder），
回傳 top-5 景點。

此節點與 food_rag、transport 並行執行。
"""

from app.agents.state import AgentState
from app.rag.retriever import COLLECTION_ATTRACTIONS, retrieve


def attraction_rag_node(state: AgentState) -> dict:
    """
    讀取 state["intent"]，查詢景點資料庫。

    Returns:
        {"attractions": [{"id", "name", "document", "metadata", "score"}, ...]}
    """
    intent = state.get("intent", {})
    location = intent.get("location", "")
    preferences = intent.get("preferences", [])
    days = intent.get("days", 2)

    # 把意圖拼成自然語言查詢，讓 embedding 效果更好
    query = f"{location} {' '.join(preferences)} 景點 {days}天"
    print(f"[attraction_rag] 查詢：{query}")

    docs = retrieve(
        query=query,
        collection=COLLECTION_ATTRACTIONS,
        top_k=5,
    )

    print(f"[attraction_rag] 取得 {len(docs)} 筆景點")
    return {"attractions": docs}
