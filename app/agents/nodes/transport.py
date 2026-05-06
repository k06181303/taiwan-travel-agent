"""
app/agents/nodes/transport.py

交通建議節點：用 Claude 生成台灣旅遊的交通規劃。
MVP 階段不接外部 API，純 LLM 生成。

此節點與 attraction_rag、food_rag 並行執行。
"""

from app.agents.state import AgentState
from app.utils.llm_client import chat

_SYSTEM = "你是台灣旅遊交通專家，熟悉台灣高鐵、台鐵、捷運、公車、計程車、租車等各種交通方式。請用繁體中文回答，內容要具體實用。"


def transport_node(state: AgentState) -> dict:
    """
    根據 intent 的目的地與天數，生成交通建議。

    Returns:
        {"transport": [{"summary": "...交通建議文字..."}]}
    """
    intent = state.get("intent", {})
    location = intent.get("location", "台北市")
    days = intent.get("days", 2)
    budget = intent.get("budget", "不限")

    print(f"[transport] 生成 {location} {days}天 交通建議...")

    prompt = f"""請為以下台灣旅遊行程提供交通建議：
目的地：{location}
天數：{days} 天
預算：{budget}

請提供：
1. 從台北到目的地的交通方式與費用
2. 當地移動建議（捷運/公車/計程車/租機車等）
3. 實用 app 推薦（Google Maps、台灣好行、Uber 等）
4. 預估交通總費用

請用條列式回答，簡潔明瞭。"""

    result = chat(prompt=prompt, system=_SYSTEM)

    print(f"[transport] 交通建議生成完成（{len(result)} 字）")
    return {"transport": [{"summary": result}]}
