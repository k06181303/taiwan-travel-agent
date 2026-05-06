"""
app/agents/nodes/itinerary.py

行程生成節點：整合 attraction_rag、food_rag、transport 三個並行節點的結果，
呼叫 Claude 生成完整行程草稿。

這是 fan-in 節點，等前三個並行節點全部完成後才執行。
"""

from app.agents.state import AgentState
from app.utils.llm_client import chat

_SYSTEM = (
    "你是專業的台灣旅遊規劃師。請根據提供的景點、美食、交通資料，"
    "制定具體可執行的每日行程。優先使用資料庫中的推薦內容，"
    "並確保行程合理（考慮地理位置、開放時間、用餐時機）。"
    "請用繁體中文回答。"
)


def _format_docs(docs: list[dict], max_chars: int = 120) -> str:
    """將 RAG 結果格式化成 LLM 可讀的條列文字"""
    if not docs:
        return "（無資料）"
    lines = []
    for doc in docs:
        name = doc.get("name", "")
        meta = doc.get("metadata", {})
        city = meta.get("city", "")
        district = meta.get("district", "")
        description = doc.get("document", "")[:max_chars]
        lines.append(f"• {name}（{city}{district}）：{description}")
    return "\n".join(lines)


def itinerary_node(state: AgentState) -> dict:
    """
    整合三個並行節點的輸出，生成行程草稿。

    Returns:
        {"itinerary_draft": "...完整行程文字..."}
    """
    intent = state.get("intent", {})
    attractions = state.get("attractions", [])
    foods = state.get("foods", [])
    transport = state.get("transport", [])

    location = intent.get("location", "台灣")
    days = intent.get("days", 2)
    preferences = intent.get("preferences", [])
    budget = intent.get("budget", "不限")

    transport_summary = transport[0].get("summary", "以大眾運輸為主") if transport else "以大眾運輸為主"

    print(f"[itinerary] 生成 {location} {days}天行程（景點{len(attractions)}筆、美食{len(foods)}筆）...")

    prompt = f"""請根據以下資料，為使用者規劃一份 {days} 天的 {location} 旅遊行程：

【使用者偏好】
- 喜好：{', '.join(preferences) if preferences else '無特別指定'}
- 預算：{budget}

【推薦景點（RAG 資料庫）】
{_format_docs(attractions)}

【推薦美食（RAG 資料庫）】
{_format_docs(foods)}

【交通資訊】
{transport_summary[:500]}

請輸出格式：
=== {location} {days}天行程草稿 ===

第 1 天
  早上：...（景點名稱 + 簡短說明）
  午餐：...（餐廳名稱 + 推薦菜色）
  下午：...
  晚餐：...
  晚上：...（可選）

第 2 天
  ...

=== 預算估算 ===
（交通 / 餐飲 / 門票分別估算）

請盡量使用上方資料庫中的推薦，並標注資訊來源（資料庫推薦 / LLM 補充）。"""

    draft = chat(prompt=prompt, system=_SYSTEM)

    print(f"[itinerary] 行程草稿生成完成（{len(draft)} 字）")
    return {"itinerary_draft": draft}
