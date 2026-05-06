"""
app/agents/nodes/intent_parser.py

意圖解析節點：用 Claude tool_use 把使用者的自然語言輸入
轉換成結構化 intent dict。

tool_use 比 prompt engineering 穩定，因為 Claude 被強制回傳 JSON schema，
不會輸出多餘文字或格式錯誤。
"""

from app.agents.state import AgentState
from app.utils.llm_client import chat_with_tools

# ── Claude tool schema：強制輸出結構化意圖 ────────────────
_PARSE_INTENT_TOOL = [
    {
        "name": "parse_travel_intent",
        "description": "解析使用者的台灣旅遊需求，提取關鍵資訊",
        "input_schema": {
            "type": "object",
            "properties": {
                "location": {
                    "type": "string",
                    "description": "目的地城市或地區，例如「台北市」、「花蓮縣」。若未指定，預設「台北市」",
                },
                "days": {
                    "type": "integer",
                    "description": "旅遊天數，若未指定預設 2",
                },
                "preferences": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "旅遊偏好清單，例如 ['老街', '小吃', '山景', '夜市']",
                },
                "budget": {
                    "type": "string",
                    "description": "預算描述，例如「5000 元」、「不限」，若未提及預設「不限」",
                },
            },
            "required": ["location", "days", "preferences", "budget"],
        },
    }
]

_SYSTEM = "你是旅遊需求分析師。請分析使用者的旅遊需求，提取地點、天數、偏好、預算。若使用者沒有明確說明某項，請給出合理的預設值。"


def intent_parser_node(state: AgentState) -> dict:
    """
    讀取 state["user_query"]，透過 Claude tool_use 解析出結構化 intent。

    Returns:
        {"intent": {"location": ..., "days": ..., "preferences": [...], "budget": ...}}
    """
    print(f"[intent_parser] 解析意圖：{state['user_query'][:50]}...")

    intent = chat_with_tools(
        prompt=state["user_query"],
        tools=_PARSE_INTENT_TOOL,
        system=_SYSTEM,
    )

    print(f"[intent_parser] 解析結果：{intent}")
    return {"intent": intent}
