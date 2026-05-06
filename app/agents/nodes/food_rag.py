"""
app/agents/nodes/food_rag.py

美食 RAG 節點：根據 intent 建構查詢字串，
呼叫兩階段混合檢索，回傳 top-5 美食推薦。

此節點與 attraction_rag、transport 並行執行。
"""

from app.agents.state import AgentState
from app.rag.retriever import COLLECTION_FOODS, retrieve


def food_rag_node(state: AgentState) -> dict:
    """
    讀取 state["intent"]，查詢美食資料庫。

    Returns:
        {"foods": [{"id", "name", "document", "metadata", "score"}, ...]}
    """
    intent = state.get("intent", {})
    location = intent.get("location", "")
    preferences = intent.get("preferences", [])

    # 偏好關鍵字 + 美食 → 讓 embedding 往美食語意靠
    query = f"{location} {' '.join(preferences)} 美食 小吃 餐廳"
    print(f"[food_rag] 查詢：{query}")

    docs = retrieve(
        query=query,
        collection=COLLECTION_FOODS,
        top_k=5,
    )

    print(f"[food_rag] 取得 {len(docs)} 筆美食")
    return {"foods": docs}
