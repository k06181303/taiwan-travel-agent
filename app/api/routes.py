"""
app/api/routes.py

FastAPI 路由定義。
Phase 4: 加入 SSE 串流 + HITL feedback endpoint。

端點：
  POST /chat          同步版（向下相容，Phase 3 行為，無 HITL）
  POST /chat/stream   SSE 串流 + HITL interrupt（主要端點）
  POST /chat/feedback HITL resume（使用者傳入修改或核准）
  GET  /health        健康檢查
"""

import json

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from langgraph.types import Command

from app.agents.graph import travel_graph
from app.api.schemas import (
    ChatRequest,
    ChatResponse,
    FeedbackRequest,
    FeedbackResponse,
    StreamChatRequest,
)

router = APIRouter()


# ── POST /chat（同步版，向下相容）──────────────────────────────────────────
@router.post("/chat", response_model=ChatResponse, summary="旅遊規劃（同步，無 HITL）")
async def chat_endpoint(request: ChatRequest) -> ChatResponse:
    """
    同步版 /chat，行為與 Phase 3 相同（無 HITL 暫停）。
    因為工作流現在含有 interrupt()，直接 invoke 會在 reviewer 節點暫停，
    所以這個端點在 reviewer 暫停後取出 itinerary_draft 直接回傳，
    模擬「跳過 HITL」的行為，用於快速測試。
    """
    try:
        initial_state = {
            "user_query": request.query,
            "messages": [],
            "intent": {},
            "attractions": [],
            "foods": [],
            "transport": [],
            "itinerary_draft": "",
            "user_feedback": "",
            "final_output": "",
        }
        # thread_id 每次都不同，確保不會撞到舊的 checkpoint
        config = {"configurable": {"thread_id": f"sync-{request.query[:20]}"}}

        result = travel_graph.invoke(initial_state, config)

        # invoke 在 interrupt 暫停後回傳當下 state
        answer = result.get("itinerary_draft", "行程生成失敗，請再試一次。")
        return ChatResponse(answer=answer, query=request.query)

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"工作流執行失敗: {type(e).__name__}: {e}")


# ── POST /chat/stream（SSE + HITL）────────────────────────────────────────
@router.post("/chat/stream", summary="旅遊規劃（SSE 串流 + HITL）")
async def chat_stream_endpoint(request: StreamChatRequest):
    """
    SSE 串流版 /chat。

    執行流程：
      1. 工作流逐節點執行，每個節點完成時送出一個 SSE event
      2. 到達 reviewer 節點時，interrupt() 暫停工作流
      3. 送出 "review_request" event，前端顯示行程草稿供使用者審核
      4. 使用者透過 POST /chat/feedback 傳入回饋

    SSE 格式（每個 event 兩行 + 空行）：
      data: {"event": "node_complete", "node": "intent_parser", "data": {...}}\\n\\n
      data: {"event": "review_request", "thread_id": "...", "itinerary_draft": "..."}\\n\\n
      data: {"event": "done"}\\n\\n
    """
    config = {"configurable": {"thread_id": request.thread_id}}

    initial_state = {
        "user_query": request.query,
        "messages": [],
        "intent": {},
        "attractions": [],
        "foods": [],
        "transport": [],
        "itinerary_draft": "",
        "user_feedback": "",
        "final_output": "",
    }

    async def event_generator():
        try:
            # stream_mode="updates" 每個節點完成時回傳該節點的 state 更新
            for chunk in travel_graph.stream(
                initial_state,
                config,
                stream_mode="updates",
            ):
                for node_name, node_output in chunk.items():
                    if node_name == "__interrupt__":
                        # interrupt() 觸發時，chunk 的 key 是 "__interrupt__"
                        # value 是 interrupt() 呼叫時傳入的 value dict
                        interrupt_value = node_output[0].value if node_output else {}
                        payload = {
                            "event": "review_request",
                            "thread_id": request.thread_id,
                            "itinerary_draft": interrupt_value.get("itinerary_draft", ""),
                            "message": interrupt_value.get("message", ""),
                        }
                    else:
                        # 一般節點完成事件
                        payload = {
                            "event": "node_complete",
                            "node": node_name,
                            "data": _serialize_node_output(node_name, node_output),
                        }

                    # SSE 格式：data: {...}\n\n
                    yield f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"

            # 工作流正常結束（被 interrupt 暫停不會到這）
            yield f"data: {json.dumps({'event': 'done'})}\n\n"

        except Exception as e:
            error_payload = {"event": "error", "detail": f"{type(e).__name__}: {e}"}
            yield f"data: {json.dumps(error_payload, ensure_ascii=False)}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",  # 防止 nginx 緩衝 SSE
        },
    )


# ── POST /chat/feedback（HITL resume）─────────────────────────────────────
@router.post("/chat/feedback", response_model=FeedbackResponse, summary="HITL 回饋（resume 工作流）")
async def chat_feedback_endpoint(request: FeedbackRequest) -> FeedbackResponse:
    """
    接收使用者對行程草稿的回饋，resume 被 interrupt 暫停的工作流。

    運作原理：
      - graph.invoke(Command(resume=feedback), config) 可恢復暫停的工作流
      - reviewer_node 中的 interrupt() 回傳使用者的 feedback 字串
      - reviewer 根據 feedback 決定：OK → final_output_node，否則 → itinerary
    """
    config = {"configurable": {"thread_id": request.thread_id}}

    try:
        # Command(resume=...) 是 LangGraph 1.x 的 resume 語法
        # 它會把 feedback 傳給暫停點的 interrupt()，然後繼續執行
        result = travel_graph.invoke(
            Command(resume=request.feedback),
            config,
        )

        final_output = result.get("final_output", "")
        itinerary_draft = result.get("itinerary_draft", "")

        if final_output:
            # 使用者核准，工作流已結束
            return FeedbackResponse(
                thread_id=request.thread_id,
                status="approved",
                final_output=final_output,
            )
        else:
            # 工作流在 reviewer 再次暫停（等新一輪審核）
            return FeedbackResponse(
                thread_id=request.thread_id,
                status="revised",
                itinerary_draft=itinerary_draft,
            )

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Resume 失敗: {type(e).__name__}: {e}",
        )


# ── GET /health ───────────────────────────────────────────────────────────
@router.get("/health", summary="健康檢查")
async def health_check() -> dict:
    """確認服務正在運行"""
    return {"status": "ok", "service": "taiwan-travel-agent"}


# ── 工具函式 ──────────────────────────────────────────────────────────────
def _serialize_node_output(node_name: str, output: dict) -> dict:
    """
    將節點輸出轉成可 JSON 序列化的格式，送給前端顯示。
    各節點只送有意義的摘要，避免把 RAG docs 全丟給前端。
    """
    if node_name == "intent_parser":
        return {"intent": output.get("intent", {})}
    elif node_name == "attraction_rag":
        docs = output.get("attractions", [])
        return {"count": len(docs), "names": [d.get("name", "") for d in docs]}
    elif node_name == "food_rag":
        docs = output.get("foods", [])
        return {"count": len(docs), "names": [d.get("name", "") for d in docs]}
    elif node_name == "transport":
        transport = output.get("transport", [])
        summary = transport[0].get("summary", "")[:100] if transport else ""
        return {"summary_preview": summary}
    elif node_name == "itinerary":
        draft = output.get("itinerary_draft", "")
        return {"length": len(draft), "preview": draft[:200]}
    elif node_name == "reviewer":
        return {"user_feedback": output.get("user_feedback", "")}
    elif node_name == "final_output_node":
        return {"final_output_length": len(output.get("final_output", ""))}
    return output
