from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class ChatRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    message: str = Field(min_length=1, max_length=1000)
    conversation_id: int | None = Field(default=None, gt=0)


class ChatMessageResponse(BaseModel):
    id: int
    role: str
    content: str
    created_at: datetime


class ChatResponse(BaseModel):
    conversation_id: int
    user_message: ChatMessageResponse
    assistant_message: ChatMessageResponse


class ChatConversationResponse(BaseModel):
    id: int
    created_at: datetime
    updated_at: datetime
    messages: list[ChatMessageResponse]


class ChatConversationListResponse(BaseModel):
    conversations: list[ChatConversationResponse]
