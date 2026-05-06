"""
app/agents/state.py

LangGraph 工作流的共享狀態定義。
AgentState 是一個 TypedDict，所有節點都讀寫這個 dict。

Annotated[list, operator.add] 的 reducer 會把多個節點對同一 list 欄位的更新
合併（append），而不是覆蓋。messages 欄位用於儲存對話歷史（Phase 4 HITL 需要）。
"""

import operator
from typing import Annotated, TypedDict


class AgentState(TypedDict):
    # ── 輸入 ────────────────────────────────────────
    user_query: str               # 使用者原始輸入

    # ── intent_parser 節點輸出 ───────────────────────
    intent: dict                  # {location, days, preferences, budget}

    # ── 並行 RAG 節點輸出 ────────────────────────────
    attractions: list             # 景點 RAG 結果（attraction_rag 寫入）
    foods: list                   # 美食 RAG 結果（food_rag 寫入）
    transport: list               # 交通建議（transport 寫入）

    # ── itinerary 節點輸出 ───────────────────────────
    itinerary_draft: str          # 行程草稿

    # ── Phase 4 HITL 用（Phase 3 暫不使用）─────────
    user_feedback: str            # 使用者審核回饋
    final_output: str             # 最終確認輸出

    # ── 對話歷史（累加 reducer）──────────────────────
    # operator.add 代表每個節點回傳的 messages 會 append 而非覆蓋
    messages: Annotated[list, operator.add]
