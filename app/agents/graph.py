"""
app/agents/graph.py

LangGraph 主工作流定義。

拓樸（Phase 4，含 HITL）：
  START
    ↓
  intent_parser
    ↓ ↓ ↓  （並行 fan-out）
  attraction_rag  food_rag  transport
    ↓          ↓         ↓  （fan-in）
         itinerary
              ↓
           reviewer  ←── interrupt()，等待使用者回饋
              ↓
        (條件分支)
         ↙         ↘
    itinerary      final_output_node
   （修改重跑）       （核准，END）

HITL 機制說明：
- reviewer_node 呼叫 interrupt()，工作流暫停並存 checkpoint
- 外部透過 graph.invoke(Command(resume=feedback), config) 恢復
- 若使用者 OK → 走向 final_output_node → END
- 若使用者要修改 → 回到 itinerary 重新生成
"""

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, StateGraph
from langgraph.types import Command

from app.agents.state import AgentState
from app.agents.nodes.attraction_rag import attraction_rag_node
from app.agents.nodes.food_rag import food_rag_node
from app.agents.nodes.intent_parser import intent_parser_node
from app.agents.nodes.itinerary import itinerary_node
from app.agents.nodes.reviewer import reviewer_node
from app.agents.nodes.transport import transport_node


def final_output_node(state: AgentState) -> dict:
    """
    最終輸出節點：將 itinerary_draft 複製到 final_output（若還沒設定）。
    使用者核准後進入此節點，代表行程確認完成。
    """
    final = state.get("final_output") or state.get("itinerary_draft", "")
    print(f"[final_output] 行程確認完成（{len(final)} 字）")
    return {"final_output": final}


def _reviewer_router(state: AgentState) -> str:
    """
    條件分支函式：根據 reviewer 節點的輸出決定下一步。
    - final_output 有值 → 核准 → 進入 final_output_node
    - 否則 → 有修改要求 → 回到 itinerary 重新生成
    """
    if state.get("final_output"):
        return "final_output_node"
    return "itinerary"


def build_graph() -> StateGraph:
    """
    建立並編譯 LangGraph 工作流（含 HITL + MemorySaver）。
    回傳已編譯的 CompiledGraph，可直接 .invoke() / .stream() 使用。
    """
    # MemorySaver：in-memory checkpointer，讓 interrupt/resume 能正確還原 state
    # Production 環境可換成 SqliteSaver 或 PostgresSaver 做持久化
    checkpointer = MemorySaver()

    graph = StateGraph(AgentState)

    # ── 加入所有節點 ──────────────────────────────────
    graph.add_node("intent_parser", intent_parser_node)
    graph.add_node("attraction_rag", attraction_rag_node)
    graph.add_node("food_rag", food_rag_node)
    graph.add_node("transport", transport_node)
    graph.add_node("itinerary", itinerary_node)
    graph.add_node("reviewer", reviewer_node)
    graph.add_node("final_output_node", final_output_node)

    # ── 設定入口點 ────────────────────────────────────
    graph.set_entry_point("intent_parser")

    # ── Fan-out：intent_parser → 三個並行節點 ─────────
    graph.add_edge("intent_parser", "attraction_rag")
    graph.add_edge("intent_parser", "food_rag")
    graph.add_edge("intent_parser", "transport")

    # ── Fan-in：三個並行節點完成後 → itinerary ─────────
    graph.add_edge("attraction_rag", "itinerary")
    graph.add_edge("food_rag", "itinerary")
    graph.add_edge("transport", "itinerary")

    # ── itinerary → reviewer（interrupt 暫停點）────────
    graph.add_edge("itinerary", "reviewer")

    # ── reviewer → 條件分支 ────────────────────────────
    graph.add_conditional_edges(
        "reviewer",
        _reviewer_router,
        {
            "final_output_node": "final_output_node",
            "itinerary": "itinerary",
        },
    )

    # ── 結束 ──────────────────────────────────────────
    graph.add_edge("final_output_node", END)

    return graph.compile(checkpointer=checkpointer)


# 全域單例：module 載入時編譯一次，後續直接 invoke/stream
travel_graph = build_graph()
