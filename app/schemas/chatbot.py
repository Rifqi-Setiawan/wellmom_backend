"""Pydantic schemas for Chatbot AI Assistant domain objects."""

from datetime import datetime, date
from typing import Optional, List

from pydantic import BaseModel, ConfigDict, field_validator


# ============================================================================
# REQUEST SCHEMAS
# ============================================================================

class ChatbotSendRequest(BaseModel):
    """Request schema for sending message to chatbot."""
    message: str
    
    @field_validator("message")
    @classmethod
    def validate_message(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("Message tidak boleh kosong")
        if len(v) > 2000:
            raise ValueError("Message maksimal 2000 karakter")
        return v.strip()
    
    model_config = ConfigDict(json_schema_extra={
        "example": {
            "message": "Apa saja makanan yang baik untuk ibu hamil trimester pertama?"
        }
    })


class ChatbotNewConversationRequest(BaseModel):
    """Request schema for creating new conversation."""
    title: Optional[str] = None
    
    @field_validator("title")
    @classmethod
    def validate_title(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and len(v) > 255:
            raise ValueError("Title maksimal 255 karakter")
        return v
    
    model_config = ConfigDict(json_schema_extra={
        "example": {
            "title": "Pertanyaan tentang Nutrisi Kehamilan"
        }
    })


# ============================================================================
# RESPONSE SCHEMAS
# ============================================================================

class QuotaInfoResponse(BaseModel):
    """Response schema for quota information."""
    used_today: int
    limit: int
    remaining: int
    resets_at: datetime  # Next reset time (midnight WIB)
    
    model_config = ConfigDict(json_schema_extra={
        "example": {
            "used_today": 5000,
            "limit": 10000,
            "remaining": 5000,
            "resets_at": "2026-01-10T00:00:00+07:00"
        }
    })


class ChatbotMessageResponse(BaseModel):
    """Response schema for chatbot message."""
    id: int
    role: str  # 'user' or 'assistant'
    content: str
    input_tokens: int = 0
    output_tokens: int = 0
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True, json_schema_extra={
        "example": {
            "id": 1,
            "role": "user",
            "content": "Apa saja makanan yang baik untuk ibu hamil trimester pertama?",
            "input_tokens": 15,
            "output_tokens": 0,
            "created_at": "2026-01-09T10:00:00Z"
        }
    })


class ChatbotConversationResponse(BaseModel):
    """Response schema for chatbot conversation."""
    id: int
    user_id: int
    title: Optional[str] = None
    is_active: bool
    message_count: int = 0  # Will be populated from relationship
    created_at: datetime
    updated_at: datetime
    
    model_config = ConfigDict(from_attributes=True, json_schema_extra={
        "example": {
            "id": 1,
            "user_id": 10,
            "title": "Pertanyaan tentang Nutrisi Kehamilan",
            "is_active": True,
            "message_count": 5,
            "created_at": "2026-01-09T10:00:00Z",
            "updated_at": "2026-01-09T10:15:00Z"
        }
    })


class ChatbotHistoryResponse(BaseModel):
    """Response schema for conversation history with messages."""
    conversation: ChatbotConversationResponse
    messages: List[ChatbotMessageResponse]
    
    model_config = ConfigDict(json_schema_extra={
        "example": {
            "conversation": {
                "id": 1,
                "user_id": 10,
                "title": "Pertanyaan tentang Nutrisi Kehamilan",
                "is_active": True,
                "message_count": 5,
                "created_at": "2026-01-09T10:00:00Z",
                "updated_at": "2026-01-09T10:15:00Z"
            },
            "messages": [
                {
                    "id": 1,
                    "role": "user",
                    "content": "Apa saja makanan yang baik untuk ibu hamil trimester pertama?",
                    "input_tokens": 15,
                    "output_tokens": 0,
                    "created_at": "2026-01-09T10:00:00Z"
                },
                {
                    "id": 2,
                    "role": "assistant",
                    "content": "Halo Ibu! Untuk trimester pertama, makanan yang baik antara lain...",
                    "input_tokens": 0,
                    "output_tokens": 120,
                    "created_at": "2026-01-09T10:00:05Z"
                }
            ]
        }
    })


class ChatbotSendResponse(BaseModel):
    """Response schema for sending message to chatbot."""
    response: str
    conversation_id: int
    quota: QuotaInfoResponse
    
    model_config = ConfigDict(json_schema_extra={
        "example": {
            "response": "Halo Ibu! Untuk trimester pertama, makanan yang baik antara lain sayuran hijau, buah-buahan, protein dari daging tanpa lemak, ikan, telur, dan kacang-kacangan. Pastikan juga mengonsumsi asam folat dan zat besi yang cukup. Jika ada pertanyaan lebih lanjut, jangan ragu untuk bertanya! 🤰💕",
            "conversation_id": 1,
            "quota": {
                "used_today": 5000,
                "limit": 10000,
                "remaining": 5000,
                "resets_at": "2026-01-10T00:00:00+07:00"
            }
        }
    })
