"""Message model for chat messages."""

from sqlalchemy import Column, Integer, Text, Boolean, TIMESTAMP, ForeignKey, Index
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from ..database import Base


class Message(Base):
    """Model untuk pesan dalam conversation."""
    
    __tablename__ = "messages"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # Foreign Keys
    conversation_id = Column(
        Integer, 
        ForeignKey("conversations.id", ondelete="CASCADE"), 
        nullable=False, 
        index=True
    )
    sender_user_id = Column(
        Integer, 
        ForeignKey("users.id", ondelete="SET NULL"), 
        nullable=False, 
        index=True
    )
    
    # Message Content
    message_text = Column(Text, nullable=False)
    
    # Read Status
    is_read = Column(Boolean, default=False, index=True)
    read_at = Column(TIMESTAMP, nullable=True)
    
    # Timestamps
    created_at = Column(TIMESTAMP, server_default=func.now(), index=True)
    
    # Constraints & Indexes
    __table_args__ = (
        # Index untuk query messages by conversation (ordered by created_at)
        Index('idx_message_conversation_created', 'conversation_id', 'created_at'),
        # Index untuk query unread messages
        Index('idx_message_unread', 'conversation_id', 'is_read', 'created_at'),
    )
    
    # Relationships
    conversation = relationship("Conversation", back_populates="messages")
    sender = relationship("User", foreign_keys=[sender_user_id])
