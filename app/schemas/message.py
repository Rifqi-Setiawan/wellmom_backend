"""Pydantic schemas for Message."""

from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field


class MessageCreate(BaseModel):
    """Schema for creating a new message."""
    message_text: str = Field(..., min_length=1, max_length=5000, description="Message content")
    ibu_hamil_id: Optional[int] = Field(None, description="Required for perawat: ID of ibu hamil to send message to. Ignored for ibu_hamil (uses their assigned perawat).")


class MessageResponse(BaseModel):
    """Schema for Message response."""
    id: int
    conversation_id: int
    sender_user_id: int
    sender_name: Optional[str] = None  # Will be populated from user relationship
    sender_role: Optional[str] = None  # Will be populated from user relationship
    message_text: str
    is_read: bool
    read_at: Optional[datetime] = None
    created_at: datetime
    
    class Config:
        from_attributes = True


class MessageListResponse(BaseModel):
    """Response for listing messages."""
    messages: List[MessageResponse]
    total: int
    has_more: bool = Field(..., description="Whether there are more messages to load")


class MarkReadRequest(BaseModel):
    """Schema for marking messages as read."""
    message_ids: Optional[List[int]] = Field(None, description="Specific message IDs to mark as read. If None or empty, marks all unread in conversation.")


class UnreadCountResponse(BaseModel):
    """Response for unread message count."""
    conversation_id: int
    unread_count: int
