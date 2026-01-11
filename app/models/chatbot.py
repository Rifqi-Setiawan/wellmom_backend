"""Chatbot models for AI Assistant feature."""

from sqlalchemy import Column, Integer, String, Boolean, TIMESTAMP, ForeignKey, Text, Date, CheckConstraint, Index, UniqueConstraint
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from ..database import Base


class ChatbotConversation(Base):
    """Model untuk conversation/session chatbot dengan AI."""
    
    __tablename__ = "chatbot_conversations"
    
    # Primary Key
    id = Column(Integer, primary_key=True, index=True)
    
    # Foreign Keys
    user_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    
    # Conversation Info
    title = Column(String(255), nullable=True)  # Auto-generated from first message
    is_active = Column(Boolean, default=True, index=True)
    
    # Timestamps
    created_at = Column(TIMESTAMP, server_default=func.now(), index=True)
    updated_at = Column(TIMESTAMP, server_default=func.now(), onupdate=func.now())
    
    # Constraints & Indexes
    __table_args__ = (
        Index('idx_chatbot_conversations_user_id', 'user_id'),
        Index('idx_chatbot_conversations_created_at', 'created_at'),
    )
    
    # Relationships
    user = relationship("User", foreign_keys=[user_id])
    messages = relationship(
        "ChatbotMessage",
        back_populates="conversation",
        cascade="all, delete-orphan",
        order_by="ChatbotMessage.created_at.asc()"
    )


class ChatbotMessage(Base):
    """Model untuk individual messages dalam conversation."""
    
    __tablename__ = "chatbot_messages"
    
    # Primary Key
    id = Column(Integer, primary_key=True, index=True)
    
    # Foreign Keys
    conversation_id = Column(
        Integer,
        ForeignKey("chatbot_conversations.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    
    # Message Content
    role = Column(
        String(20),
        nullable=False,
        index=True
    )  # 'user' or 'assistant'
    content = Column(Text, nullable=False)
    
    # Token Usage Tracking
    input_tokens = Column(Integer, default=0)
    output_tokens = Column(Integer, default=0)
    
    # Timestamps
    created_at = Column(TIMESTAMP, server_default=func.now(), index=True)
    
    # Constraints
    __table_args__ = (
        CheckConstraint(
            "role IN ('user', 'assistant')",
            name="check_chatbot_message_role"
        ),
        Index('idx_chatbot_messages_conversation_id', 'conversation_id'),
        Index('idx_chatbot_messages_created_at', 'created_at'),
    )
    
    # Relationships
    conversation = relationship("ChatbotConversation", back_populates="messages")


class ChatbotUserUsage(Base):
    """Model untuk tracking daily usage per user (quota management)."""
    
    __tablename__ = "chatbot_user_usage"
    
    # Primary Key
    id = Column(Integer, primary_key=True, index=True)
    
    # Foreign Keys
    user_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    
    # Usage Tracking
    date = Column(Date, nullable=False, server_default=func.current_date(), index=True)
    tokens_used = Column(Integer, default=0)
    request_count = Column(Integer, default=0)
    
    # Timestamps
    created_at = Column(TIMESTAMP, server_default=func.now())
    updated_at = Column(TIMESTAMP, server_default=func.now(), onupdate=func.now())
    
    # Constraints & Indexes
    __table_args__ = (
        UniqueConstraint('user_id', 'date', name='uq_chatbot_user_usage_date'),
        Index('idx_chatbot_user_usage_user_date', 'user_id', 'date'),
    )
    
    # Relationships
    user = relationship("User", foreign_keys=[user_id])


class ChatbotGlobalUsage(Base):
    """Model untuk tracking global daily usage (billing protection)."""
    
    __tablename__ = "chatbot_global_usage"
    
    # Primary Key
    id = Column(Integer, primary_key=True, index=True)
    
    # Usage Tracking
    date = Column(
        Date,
        nullable=False,
        unique=True,
        server_default=func.current_date(),
        index=True
    )
    tokens_used = Column(Integer, default=0)
    request_count = Column(Integer, default=0)
    
    # Timestamps
    created_at = Column(TIMESTAMP, server_default=func.now())
    updated_at = Column(TIMESTAMP, server_default=func.now(), onupdate=func.now())
    
    # Constraints & Indexes
    __table_args__ = (
        Index('idx_chatbot_global_usage_date', 'date'),
    )
