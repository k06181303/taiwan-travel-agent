"""
app/api/schemas.py

API 請求與回應的 Pydantic 模型。
Pydantic 會在 request 進來時自動驗證欄位型別,省去手動 if 判斷。
"""

from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    """POST /chat 的請求格式"""
    query: str = Field(..., min_length=1, description="使用者輸入的旅遊問題")

    model_config = {
        "json_schema_extra": {
            "examples": [
                {"query": "我想去台北玩 2 天,喜歡老街跟小吃,預算 5000 元"}
            ]
        }
    }


class ChatResponse(BaseModel):
    """POST /chat 的回應格式"""
    answer: str = Field(..., description="Claude 的回應文字")
    query: str = Field(..., description="原始使用者輸入(方便 debug)")


class StreamChatRequest(BaseModel):
    """POST /chat/stream 的請求格式"""
    query: str = Field(..., min_length=1, description="使用者輸入的旅遊問題")
    thread_id: str = Field(
        default="default",
        description="對話 thread ID，用於 HITL checkpoint 識別。同一個 thread_id 代表同一對話",
    )

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "query": "我想去台北玩 2 天,喜歡老街跟小吃,預算 5000 元",
                    "thread_id": "user-123",
                }
            ]
        }
    }


class FeedbackRequest(BaseModel):
    """POST /chat/feedback 的請求格式"""
    thread_id: str = Field(..., description="對應 /chat/stream 使用的 thread_id")
    feedback: str = Field(
        ...,
        min_length=1,
        description="使用者對行程草稿的回饋。輸入「OK」代表核准，其他文字代表修改要求",
    )

    model_config = {
        "json_schema_extra": {
            "examples": [
                {"thread_id": "user-123", "feedback": "把第 2 天下午換成參觀故宮"},
                {"thread_id": "user-123", "feedback": "OK"},
            ]
        }
    }


class FeedbackResponse(BaseModel):
    """POST /chat/feedback 的回應格式"""
    thread_id: str
    status: str = Field(description="'approved'（核准）或 'revised'（修改中）")
    final_output: str = Field(default="", description="核准後的最終行程（status='approved' 時有值）")
    itinerary_draft: str = Field(default="", description="修改後的新行程草稿（status='revised' 時有值）")
