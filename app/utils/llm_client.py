"""
app/utils/llm_client.py

封裝 Anthropic Claude API 呼叫。
提供兩個函式:
  - chat()        同步呼叫,回傳完整字串(Phase 1~3 用)
  - chat_stream() 串流呼叫,回傳 generator(Phase 4 SSE 用)

統一在這裡管理 model、max_tokens 等參數,讓其他節點不需要知道 API 細節。
"""

import anthropic
from app.config import settings


# 建立全域 Anthropic client(避免每次呼叫都重新初始化)
_client = anthropic.Anthropic(api_key=settings.anthropic_api_key)


def chat(
    prompt: str,
    system: str = "你是一個專業的台灣旅遊規劃師,熟悉台灣各地景點、美食與交通。請用繁體中文回答。",
) -> str:
    """
    同步呼叫 Claude API,回傳完整回應字串。

    Args:
        prompt: 使用者輸入文字
        system: 系統提示詞(可覆寫,讓不同節點設定不同角色)

    Returns:
        Claude 的回應文字
    """
    message = _client.messages.create(
        model=settings.claude_model,
        max_tokens=settings.claude_max_tokens,
        system=system,
        messages=[
            {"role": "user", "content": prompt}
        ],
    )
    # message.content 是 list[ContentBlock],取第一個 text block
    return message.content[0].text


def chat_with_history(
    messages: list[dict],
    system: str = "你是一個專業的台灣旅遊規劃師,熟悉台灣各地景點、美食與交通。請用繁體中文回答。",
) -> str:
    """
    帶完整對話歷史呼叫 Claude API。

    Args:
        messages: 對話歷史,格式 [{"role": "user"/"assistant", "content": "..."}]
        system: 系統提示詞

    Returns:
        Claude 的回應文字
    """
    message = _client.messages.create(
        model=settings.claude_model,
        max_tokens=settings.claude_max_tokens,
        system=system,
        messages=messages,
    )
    return message.content[0].text


def chat_with_tools(
    prompt: str,
    tools: list[dict],
    system: str = "你是一個專業的台灣旅遊規劃師。",
) -> dict:
    """
    呼叫 Claude API 並強制使用 tool_use 取得結構化輸出。
    Phase 3 的 intent_parser 節點會用這個函式。

    Args:
        prompt: 使用者輸入文字
        tools: Anthropic tool schema 列表
        system: 系統提示詞

    Returns:
        tool_use 的 input dict(即解析後的結構化資料)
    """
    message = _client.messages.create(
        model=settings.claude_model,
        max_tokens=settings.claude_max_tokens,
        system=system,
        tools=tools,
        messages=[{"role": "user", "content": prompt}],
    )
    # 找到 tool_use 類型的 content block
    for block in message.content:
        if block.type == "tool_use":
            return block.input
    # 若 Claude 沒有呼叫 tool(不應該發生),回傳空 dict
    return {}
