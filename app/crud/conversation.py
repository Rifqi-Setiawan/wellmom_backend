"""CRUD operations for Conversation."""

from typing import List, Optional
from datetime import datetime
from sqlalchemy import select, func, and_, or_
from sqlalchemy.orm import Session, joinedload

from app.crud.base import CRUDBase
from app.models.conversation import Conversation
from app.models.message import Message
from app.models.ibu_hamil import IbuHamil
from app.models.perawat import Perawat
from app.schemas.conversation import ConversationCreate


class CRUDConversation(CRUDBase[Conversation, ConversationCreate, dict]):
    """CRUD operations for Conversation."""
    
    def get_or_create(
        self, 
        db: Session, 
        *, 
        ibu_hamil_id: int, 
        perawat_id: int
    ) -> Conversation:
        """Get existing conversation or create new one."""
        # Check if conversation exists
        stmt = select(Conversation).where(
            and_(
                Conversation.ibu_hamil_id == ibu_hamil_id,
                Conversation.perawat_id == perawat_id
            )
        )
        conversation = db.scalars(stmt).first()
        
        if conversation:
            return conversation
        
        # Create new conversation
        conversation = Conversation(
            ibu_hamil_id=ibu_hamil_id,
            perawat_id=perawat_id
        )
        db.add(conversation)
        db.commit()
        db.refresh(conversation)
        return conversation
    
    def get_by_ibu_hamil(
        self, 
        db: Session, 
        *, 
        ibu_hamil_id: int,
        skip: int = 0,
        limit: int = 50
    ) -> List[Conversation]:
        """Get all conversations for an ibu hamil."""
        stmt = (
            select(Conversation)
            .where(Conversation.ibu_hamil_id == ibu_hamil_id)
            .order_by(Conversation.last_message_at.desc().nulls_last(), Conversation.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        return list(db.scalars(stmt).all())
    
    def get_by_perawat(
        self, 
        db: Session, 
        *, 
        perawat_id: int,
        skip: int = 0,
        limit: int = 50
    ) -> List[Conversation]:
        """Get all conversations for a perawat."""
        stmt = (
            select(Conversation)
            .where(Conversation.perawat_id == perawat_id)
            .order_by(Conversation.last_message_at.desc().nulls_last(), Conversation.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        return list(db.scalars(stmt).all())
    
    def get_with_last_message(
        self,
        db: Session,
        *,
        conversation_id: int
    ) -> Optional[Conversation]:
        """Get conversation with last message info."""
        conversation = self.get(db, conversation_id)
        if not conversation:
            return None
        
        # Eager load last message
        stmt = (
            select(Message)
            .where(Message.conversation_id == conversation_id)
            .order_by(Message.created_at.desc())
            .limit(1)
        )
        last_message = db.scalars(stmt).first()
        
        return conversation
    
    def update_last_message_at(
        self,
        db: Session,
        *,
        conversation_id: int,
        timestamp: datetime
    ) -> Optional[Conversation]:
        """Update last_message_at timestamp."""
        conversation = self.get(db, conversation_id)
        if not conversation:
            return None
        
        conversation.last_message_at = timestamp
        db.add(conversation)
        db.commit()
        db.refresh(conversation)
        return conversation
    
    def verify_assignment(
        self,
        db: Session,
        *,
        ibu_hamil_id: int,
        perawat_id: int
    ) -> bool:
        """Verify that ibu hamil is assigned to this perawat."""
        stmt = select(IbuHamil).where(
            and_(
                IbuHamil.id == ibu_hamil_id,
                IbuHamil.perawat_id == perawat_id,
                IbuHamil.is_active == True
            )
        )
        ibu_hamil = db.scalars(stmt).first()
        return ibu_hamil is not None
    
    def get_unread_count(
        self,
        db: Session,
        *,
        conversation_id: int,
        user_id: int
    ) -> int:
        """Get count of unread messages for a user in a conversation."""
        # Get conversation to determine the other participant
        conversation = self.get(db, conversation_id)
        if not conversation:
            return 0
        
        # Determine the other participant's user_id
        # If current user is ibu_hamil, count messages from perawat
        # If current user is perawat, count messages from ibu_hamil
        ibu_hamil = db.get(IbuHamil, conversation.ibu_hamil_id)
        perawat = db.get(Perawat, conversation.perawat_id)
        
        if not ibu_hamil or not perawat:
            return 0
        
        # Determine sender user_id (the other participant)
        if ibu_hamil.user_id == user_id:
            # Current user is ibu_hamil, count messages from perawat
            sender_user_id = perawat.user_id
        elif perawat.user_id == user_id:
            # Current user is perawat, count messages from ibu_hamil
            sender_user_id = ibu_hamil.user_id
        else:
            # User is not part of this conversation
            return 0
        
        # Count unread messages from the other participant
        stmt = select(func.count(Message.id)).where(
            and_(
                Message.conversation_id == conversation_id,
                Message.sender_user_id == sender_user_id,
                Message.is_read == False
            )
        )
        count = db.scalar(stmt) or 0
        return count


# Create instance
crud_conversation = CRUDConversation(Conversation)
