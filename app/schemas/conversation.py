"""Pydantic schemas for Conversation."""

from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field


class ConversationBase(BaseModel):
    """Base schema for Conversation."""
    ibu_hamil_id: int
    perawat_id: int


class ConversationCreate(ConversationBase):
    """Schema for creating a new conversation."""
    pass


class ConversationResponse(ConversationBase):
    """Schema for Conversation response."""
    id: int
    last_message_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class ConversationWithLastMessage(ConversationResponse):
    """Conversation with last message info."""
    last_message_text: Optional[str] = None
    last_message_sender_id: Optional[int] = None
    unread_count: int = 0
    
    class Config:
        from_attributes = True


class ConversationListResponse(BaseModel):
    """Response for listing conversations."""
    conversations: List[ConversationWithLastMessage]
    total: int
