"""CRUD operations for Message."""

from typing import List, Optional
from datetime import datetime
from sqlalchemy import select, func, and_, desc
from sqlalchemy.orm import Session

from app.crud.base import CRUDBase
from app.models.message import Message
from app.models.conversation import Conversation
from app.schemas.message import MessageCreate


class CRUDMessage(CRUDBase[Message, MessageCreate, dict]):
    """CRUD operations for Message."""
    
    def create_message(
        self,
        db: Session,
        *,
        conversation_id: int,
        sender_user_id: int,
        message_text: str
    ) -> Message:
        """Create a new message and update conversation's last_message_at."""
        # Create message
        message = Message(
            conversation_id=conversation_id,
            sender_user_id=sender_user_id,
            message_text=message_text,
            is_read=False
        )
        db.add(message)
        
        # Update conversation's last_message_at
        conversation = db.get(Conversation, conversation_id)
        if conversation:
            conversation.last_message_at = datetime.utcnow()
            db.add(conversation)
        
        db.commit()
        db.refresh(message)
        
        # Note: WebSocket broadcast is handled in the endpoint, not here
        # to avoid async/sync mixing issues
        
        return message
    
    def get_by_conversation(
        self,
        db: Session,
        *,
        conversation_id: int,
        skip: int = 0,
        limit: int = 50
    ) -> List[Message]:
        """Get messages for a conversation with pagination (oldest first for chat UI)."""
        stmt = (
            select(Message)
            .where(Message.conversation_id == conversation_id)
            .order_by(Message.created_at.asc())  # Oldest first for chat UI
            .offset(skip)
            .limit(limit)
        )
        return list(db.scalars(stmt).all())
    
    def get_total_count(
        self,
        db: Session,
        *,
        conversation_id: int
    ) -> int:
        """Get total message count for a conversation."""
        stmt = select(func.count(Message.id)).where(
            Message.conversation_id == conversation_id
        )
        return db.scalar(stmt) or 0
    
    def mark_as_read(
        self,
        db: Session,
        *,
        conversation_id: int,
        message_ids: Optional[List[int]] = None,
        reader_user_id: int
    ) -> int:
        """Mark messages as read.
        
        Args:
            conversation_id: ID of the conversation
            message_ids: Specific message IDs to mark as read. If None, marks all unread.
            reader_user_id: ID of the user marking messages as read
        
        Returns:
            Number of messages marked as read
        """
        # Get conversation to determine the other participant
        conversation = db.get(Conversation, conversation_id)
        if not conversation:
            return 0
        
        from app.models.ibu_hamil import IbuHamil
        from app.models.perawat import Perawat
        
        ibu_hamil = db.get(IbuHamil, conversation.ibu_hamil_id)
        perawat = db.get(Perawat, conversation.perawat_id)
        
        if not ibu_hamil or not perawat:
            return 0
        
        # Determine sender user_id (the other participant)
        if ibu_hamil.user_id == reader_user_id:
            # Reader is ibu_hamil, mark messages from perawat as read
            sender_user_id = perawat.user_id
        elif perawat.user_id == reader_user_id:
            # Reader is perawat, mark messages from ibu_hamil as read
            sender_user_id = ibu_hamil.user_id
        else:
            # User is not part of this conversation
            return 0
        
        # Build query
        conditions = [
            Message.conversation_id == conversation_id,
            Message.sender_user_id == sender_user_id,
            Message.is_read == False
        ]
        
        if message_ids:
            conditions.append(Message.id.in_(message_ids))
        
        stmt = select(Message).where(and_(*conditions))
        messages = db.scalars(stmt).all()
        
        # Mark as read
        read_count = 0
        now = datetime.utcnow()
        for message in messages:
            message.is_read = True
            message.read_at = now
            db.add(message)
            read_count += 1
        
        if read_count > 0:
            db.commit()
        
        return read_count
    
    def get_unread_messages(
        self,
        db: Session,
        *,
        conversation_id: int,
        user_id: int
    ) -> List[Message]:
        """Get unread messages for a user in a conversation."""
        # Get conversation to determine the other participant
        conversation = db.get(Conversation, conversation_id)
        if not conversation:
            return []
        
        from app.models.ibu_hamil import IbuHamil
        from app.models.perawat import Perawat
        
        ibu_hamil = db.get(IbuHamil, conversation.ibu_hamil_id)
        perawat = db.get(Perawat, conversation.perawat_id)
        
        if not ibu_hamil or not perawat:
            return []
        
        # Determine sender user_id (the other participant)
        if ibu_hamil.user_id == user_id:
            sender_user_id = perawat.user_id
        elif perawat.user_id == user_id:
            sender_user_id = ibu_hamil.user_id
        else:
            return []
        
        stmt = (
            select(Message)
            .where(
                and_(
                    Message.conversation_id == conversation_id,
                    Message.sender_user_id == sender_user_id,
                    Message.is_read == False
                )
            )
            .order_by(Message.created_at.asc())
        )
        return list(db.scalars(stmt).all())


# Create instance
crud_message = CRUDMessage(Message)
