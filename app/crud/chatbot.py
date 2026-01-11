"""CRUD operations for Chatbot AI Assistant."""

from __future__ import annotations

from datetime import datetime, date, timedelta
from typing import List, Optional, Tuple

from sqlalchemy import select, func, and_, desc
from sqlalchemy.orm import Session

from app.crud.base import CRUDBase
from app.models.chatbot import (
    ChatbotConversation,
    ChatbotMessage,
    ChatbotUserUsage,
    ChatbotGlobalUsage,
)
from app.config import settings


class CRUDChatbotConversation(CRUDBase[ChatbotConversation, dict, dict]):
    """CRUD operations for ChatbotConversation."""
    
    def create_conversation(
        self,
        db: Session,
        *,
        user_id: int,
        title: Optional[str] = None
    ) -> ChatbotConversation:
        """Create a new chatbot conversation."""
        db_obj = ChatbotConversation(
            user_id=user_id,
            title=title,
            is_active=True
        )
        try:
            db.add(db_obj)
            db.commit()
            db.refresh(db_obj)
        except Exception:
            db.rollback()
            raise
        return db_obj
    
    def get_conversation(
        self,
        db: Session,
        *,
        conversation_id: int,
        user_id: int
    ) -> Optional[ChatbotConversation]:
        """Get conversation by ID, verifying ownership."""
        stmt = select(ChatbotConversation).where(
            and_(
                ChatbotConversation.id == conversation_id,
                ChatbotConversation.user_id == user_id
            )
        )
        return db.scalars(stmt).first()
    
    def get_user_conversations(
        self,
        db: Session,
        *,
        user_id: int,
        skip: int = 0,
        limit: int = 20
    ) -> List[ChatbotConversation]:
        """Get all conversations for a user, ordered by created_at descending."""
        stmt = (
            select(ChatbotConversation)
            .where(ChatbotConversation.user_id == user_id)
            .where(ChatbotConversation.is_active == True)
            .order_by(desc(ChatbotConversation.created_at))
            .offset(skip)
            .limit(limit)
        )
        return list(db.scalars(stmt).all())
    
    def delete_conversation(
        self,
        db: Session,
        *,
        conversation_id: int,
        user_id: int
    ) -> Optional[ChatbotConversation]:
        """Soft delete a conversation (set is_active=False), verifying ownership."""
        conversation = self.get_conversation(db, conversation_id=conversation_id, user_id=user_id)
        if not conversation:
            return None
        
        conversation.is_active = False
        conversation.updated_at = datetime.utcnow()
        try:
            db.add(conversation)
            db.commit()
            db.refresh(conversation)
        except Exception:
            db.rollback()
            raise
        return conversation


class CRUDChatbotMessage(CRUDBase[ChatbotMessage, dict, dict]):
    """CRUD operations for ChatbotMessage."""
    
    def add_message(
        self,
        db: Session,
        *,
        conversation_id: int,
        role: str,
        content: str,
        input_tokens: int = 0,
        output_tokens: int = 0
    ) -> ChatbotMessage:
        """Add a message to a conversation."""
        db_obj = ChatbotMessage(
            conversation_id=conversation_id,
            role=role,
            content=content,
            input_tokens=input_tokens,
            output_tokens=output_tokens
        )
        try:
            db.add(db_obj)
            db.commit()
            db.refresh(db_obj)
        except Exception:
            db.rollback()
            raise
        return db_obj
    
    def get_conversation_messages(
        self,
        db: Session,
        *,
        conversation_id: int,
        limit: int = 100
    ) -> List[ChatbotMessage]:
        """Get messages for a conversation, ordered by created_at ascending."""
        stmt = (
            select(ChatbotMessage)
            .where(ChatbotMessage.conversation_id == conversation_id)
            .order_by(ChatbotMessage.created_at.asc())
            .limit(limit)
        )
        return list(db.scalars(stmt).all())


class CRUDChatbotUserUsage(CRUDBase[ChatbotUserUsage, dict, dict]):
    """CRUD operations for ChatbotUserUsage."""
    
    def get_or_create_user_usage(
        self,
        db: Session,
        *,
        user_id: int,
        usage_date: Optional[date] = None
    ) -> ChatbotUserUsage:
        """Get or create user usage record for a date (default: today)."""
        if usage_date is None:
            usage_date = date.today()
        
        stmt = select(ChatbotUserUsage).where(
            and_(
                ChatbotUserUsage.user_id == user_id,
                ChatbotUserUsage.date == usage_date
            )
        )
        usage = db.scalars(stmt).first()
        
        if not usage:
            usage = ChatbotUserUsage(
                user_id=user_id,
                date=usage_date,
                tokens_used=0,
                request_count=0
            )
            try:
                db.add(usage)
                db.commit()
                db.refresh(usage)
            except Exception:
                db.rollback()
                raise
        
        return usage
    
    def increment_user_usage(
        self,
        db: Session,
        *,
        user_id: int,
        tokens: int
    ) -> ChatbotUserUsage:
        """Increment user usage tokens and request count."""
        usage = self.get_or_create_user_usage(db, user_id=user_id)
        usage.tokens_used += tokens
        usage.request_count += 1
        usage.updated_at = datetime.utcnow()
        try:
            db.add(usage)
            db.commit()
            db.refresh(usage)
        except Exception:
            db.rollback()
            raise
        return usage
    
    def check_user_quota(
        self,
        db: Session,
        *,
        user_id: int
    ) -> Tuple[bool, int]:
        """
        Check if user can use chatbot (quota check).
        
        Returns:
            tuple: (can_use: bool, remaining: int)
        """
        usage = self.get_or_create_user_usage(db, user_id=user_id)
        limit = settings.CHATBOT_USER_DAILY_TOKEN_LIMIT
        remaining = max(0, limit - usage.tokens_used)
        can_use = usage.tokens_used < limit
        
        return (can_use, remaining)


class CRUDChatbotGlobalUsage(CRUDBase[ChatbotGlobalUsage, dict, dict]):
    """CRUD operations for ChatbotGlobalUsage."""
    
    def get_or_create_global_usage(
        self,
        db: Session,
        *,
        usage_date: Optional[date] = None
    ) -> ChatbotGlobalUsage:
        """Get or create global usage record for a date (default: today)."""
        if usage_date is None:
            usage_date = date.today()
        
        stmt = select(ChatbotGlobalUsage).where(
            ChatbotGlobalUsage.date == usage_date
        )
        usage = db.scalars(stmt).first()
        
        if not usage:
            usage = ChatbotGlobalUsage(
                date=usage_date,
                tokens_used=0,
                request_count=0
            )
            try:
                db.add(usage)
                db.commit()
                db.refresh(usage)
            except Exception:
                db.rollback()
                raise
        
        return usage
    
    def increment_global_usage(
        self,
        db: Session,
        *,
        tokens: int
    ) -> ChatbotGlobalUsage:
        """Increment global usage tokens and request count."""
        usage = self.get_or_create_global_usage(db)
        usage.tokens_used += tokens
        usage.request_count += 1
        usage.updated_at = datetime.utcnow()
        try:
            db.add(usage)
            db.commit()
            db.refresh(usage)
        except Exception:
            db.rollback()
            raise
        return usage
    
    def check_global_quota(
        self,
        db: Session
    ) -> Tuple[bool, int]:
        """
        Check if global quota allows chatbot usage.
        
        Returns:
            tuple: (can_use: bool, remaining: int)
        """
        usage = self.get_or_create_global_usage(db)
        limit = settings.CHATBOT_GLOBAL_DAILY_TOKEN_LIMIT
        remaining = max(0, limit - usage.tokens_used)
        can_use = usage.tokens_used < limit
        
        return (can_use, remaining)


# Singleton instances
crud_chatbot_conversation = CRUDChatbotConversation(ChatbotConversation)
crud_chatbot_message = CRUDChatbotMessage(ChatbotMessage)
crud_chatbot_user_usage = CRUDChatbotUserUsage(ChatbotUserUsage)
crud_chatbot_global_usage = CRUDChatbotGlobalUsage(ChatbotGlobalUsage)
