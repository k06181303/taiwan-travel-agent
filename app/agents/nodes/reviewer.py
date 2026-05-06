"""
app/agents/nodes/reviewer.py

HITL 審核節點：在行程草稿生成後暫停，等待使用者審核。

使用 LangGraph 的 interrupt() 機制：
  - 執行到此節點時，工作流暫停並保存 checkpoint
  - 使用者透過 /chat/feedback endpoint 傳入回饋
  - graph.invoke(None, config) 或 graph.stream(None, config) resume 工作流
  - 若使用者說「OK」→ 寫入 final_output，流程結束
  - 若使用者提出修改 → 更新 user_feedback，回到 itinerary 重新生成
"""

from langgraph.types import interrupt

from app.agents.state import AgentState


def reviewer_node(state: AgentState) -> dict:
    """
    暫停工作流，等待使用者對行程草稿的回饋。

    interrupt() 的運作：
      1. LangGraph 將目前 state 存入 checkpointer
      2. 拋出 GraphInterrupt exception，工作流暫停
      3. 外部呼叫 graph.invoke({"user_feedback": "..."}, config) 可 resume
      4. resume 後，interrupt() 的回傳值即為使用者傳入的 feedback

    Returns:
        {"user_feedback": "..."} 或 {"final_output": "..."}（若使用者核准）
    """
    draft = state.get("itinerary_draft", "")

    # interrupt() 會暫停工作流，value 是傳給前端的暫停訊息
    # resume 時，interrupt() 回傳值是使用者傳入的 user_feedback
    feedback = interrupt(
        {
            "type": "review_request",
            "message": "請審核以下行程草稿，輸入修改要求或輸入「OK」確認",
            "itinerary_draft": draft,
        }
    )

    print(f"[reviewer] 收到使用者回饋：{str(feedback)[:100]}")

    # 判斷使用者是否核准
    feedback_str = str(feedback).strip()
    if feedback_str.upper() in ("OK", "好", "沒問題", "確認", "可以"):
        return {
            "final_output": draft,
            "user_feedback": feedback_str,
        }
    else:
        # 有修改要求，寫入 user_feedback，graph 根據條件分支回到 itinerary
        return {
            "user_feedback": feedback_str,
            "final_output": "",
        }
