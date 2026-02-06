"""Chat endpoints for communication between Ibu Hamil and Perawat."""

import logging
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_active_user, get_db, require_role
from app.crud import (
    crud_conversation,
    crud_message,
    crud_ibu_hamil,
    crud_perawat,
)
from app.models.user import User
from app.models.conversation import Conversation
from app.models.message import Message
from app.models.ibu_hamil import IbuHamil
from app.models.perawat import Perawat
from app.schemas.conversation import (
    ConversationResponse,
    ConversationWithLastMessage,
    ConversationListResponse,
)
from app.schemas.message import (
    MessageCreate,
    MessageResponse,
    MessageListResponse,
    MarkReadRequest,
    UnreadCountResponse,
)
from app.services.notification_service import notification_service
from app.services.firebase_service import firebase_service
from app.api.v1.endpoints.websocket_chat import manager

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/chat",
    tags=["Chat"],
)


def _get_ibu_hamil_by_user_id(db: Session, user_id: int) -> Optional[IbuHamil]:
    """Get IbuHamil by user_id."""
    return crud_ibu_hamil.get_by_field(db, "user_id", user_id)


def _get_perawat_by_user_id(db: Session, user_id: int) -> Optional[Perawat]:
    """Get Perawat by user_id."""
    return crud_perawat.get_by_field(db, "user_id", user_id)


def _authorize_conversation_access(
    db: Session,
    conversation: Conversation,
    current_user: User
) -> None:
    """Verify that current user has access to this conversation."""
    # Get user's role-based profile
    ibu_hamil = _get_ibu_hamil_by_user_id(db, current_user.id)
    perawat = _get_perawat_by_user_id(db, current_user.id)
    
    if current_user.role == "ibu_hamil":
        if not ibu_hamil or ibu_hamil.id != conversation.ibu_hamil_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Anda tidak memiliki akses ke conversation ini."
            )
    elif current_user.role == "perawat":
        if not perawat or perawat.id != conversation.perawat_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Anda tidak memiliki akses ke conversation ini."
            )
    else:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Hanya ibu hamil dan perawat yang dapat mengakses chat."
        )


@router.get(
    "/conversations",
    response_model=ConversationListResponse,
    status_code=status.HTTP_200_OK,
    summary="List conversations",
    description="""
    Get list of conversations for the current user.
    
    - **Ibu Hamil**: Returns conversations with assigned perawat
    - **Perawat**: Returns conversations with assigned ibu hamil
    
    Conversations are ordered by last_message_at (most recent first).
    """,
)
def list_conversations(
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(50, ge=1, le=100, description="Maximum number of records to return"),
    current_user: User = Depends(require_role("ibu_hamil", "perawat")),
    db: Session = Depends(get_db),
) -> ConversationListResponse:
    """List all conversations for the current user."""
    conversations = []
    
    if current_user.role == "ibu_hamil":
        ibu_hamil = _get_ibu_hamil_by_user_id(db, current_user.id)
        if not ibu_hamil:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Profil ibu hamil tidak ditemukan."
            )
        conversations = crud_conversation.get_by_ibu_hamil(
            db, ibu_hamil_id=ibu_hamil.id, skip=skip, limit=limit
        )
    elif current_user.role == "perawat":
        perawat = _get_perawat_by_user_id(db, current_user.id)
        if not perawat:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Profil perawat tidak ditemukan."
            )
        conversations = crud_conversation.get_by_perawat(
            db, perawat_id=perawat.id, skip=skip, limit=limit
        )
    
    # Enrich with last message and unread count
    enriched_conversations = []
    for conv in conversations:
        # Get last message - query explicitly to ensure correct ordering
        last_message = None
        stmt = (
            select(Message)
            .where(Message.conversation_id == conv.id)
            .order_by(Message.created_at.desc())
            .limit(1)
        )
        last_message = db.scalar(stmt)
        
        # Get unread count
        unread_count = crud_conversation.get_unread_count(
            db, conversation_id=conv.id, user_id=current_user.id
        )
        
        enriched = ConversationWithLastMessage(
            id=conv.id,
            ibu_hamil_id=conv.ibu_hamil_id,
            perawat_id=conv.perawat_id,
            last_message_at=conv.last_message_at,
            created_at=conv.created_at,
            updated_at=conv.updated_at,
            last_message_text=last_message.message_text if last_message else None,
            last_message_sender_id=last_message.sender_user_id if last_message else None,
            unread_count=unread_count,
        )
        enriched_conversations.append(enriched)
    
    # Get total unread notifications for this user
    total_unread_notifications = notification_service.get_unread_count(
        db, user_id=current_user.id
    )

    return ConversationListResponse(
        conversations=enriched_conversations,
        total=len(enriched_conversations),
        total_unread_notifications=total_unread_notifications,
    )


@router.get(
    "/conversations/{conversation_id}",
    response_model=ConversationResponse,
    status_code=status.HTTP_200_OK,
    summary="Get conversation detail",
    description="Get conversation details by ID.",
)
def get_conversation(
    conversation_id: int,
    current_user: User = Depends(require_role("ibu_hamil", "perawat")),
    db: Session = Depends(get_db),
) -> ConversationResponse:
    """Get conversation by ID."""
    conversation = crud_conversation.get(db, conversation_id)
    if not conversation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation tidak ditemukan."
        )
    
    _authorize_conversation_access(db, conversation, current_user)
    
    return ConversationResponse.model_validate(conversation)


@router.get(
    "/conversations/{conversation_id}/messages",
    response_model=MessageListResponse,
    status_code=status.HTTP_200_OK,
    summary="Get messages",
    description="""
    Get messages for a conversation with pagination.
    
    Messages are returned in chronological order (oldest first) for chat UI.
    Use `skip` and `limit` for pagination.
    """,
)
def get_messages(
    conversation_id: int,
    skip: int = Query(0, ge=0, description="Number of messages to skip"),
    limit: int = Query(50, ge=1, le=100, description="Maximum number of messages to return"),
    current_user: User = Depends(require_role("ibu_hamil", "perawat")),
    db: Session = Depends(get_db),
) -> MessageListResponse:
    """Get messages for a conversation."""
    conversation = crud_conversation.get(db, conversation_id)
    if not conversation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation tidak ditemukan."
        )
    
    _authorize_conversation_access(db, conversation, current_user)
    
    # Get messages
    messages = crud_message.get_by_conversation(
        db, conversation_id=conversation_id, skip=skip, limit=limit
    )
    
    # Get total count
    total = crud_message.get_total_count(db, conversation_id=conversation_id)
    
    # Enrich with sender info
    enriched_messages = []
    for msg in messages:
        sender = db.get(User, msg.sender_user_id)
        enriched = MessageResponse(
            id=msg.id,
            conversation_id=msg.conversation_id,
            sender_user_id=msg.sender_user_id,
            sender_name=sender.full_name if sender else None,
            sender_role=sender.role if sender else None,
            message_text=msg.message_text,
            is_read=msg.is_read,
            read_at=msg.read_at,
            created_at=msg.created_at,
        )
        enriched_messages.append(enriched)
    
    return MessageListResponse(
        messages=enriched_messages,
        total=total,
        has_more=(skip + len(messages) < total)
    )


@router.post(
    "/messages",
    response_model=MessageResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Send message",
    description="""
    Send a new message. The conversation will be created automatically if it doesn't exist.
    
    For **Ibu Hamil**: Message will be sent to their assigned perawat (ibu_hamil_id is ignored).
    For **Perawat**: Must specify `ibu_hamil_id` in request body to send message to a specific ibu hamil.
    """,
)
def send_message(
    message_in: MessageCreate,
    current_user: User = Depends(require_role("ibu_hamil", "perawat")),
    db: Session = Depends(get_db),
) -> MessageResponse:
    """Send a message. Auto-creates conversation if needed."""
    conversation = None
    
    if current_user.role == "ibu_hamil":
        # Ibu hamil sends to their assigned perawat
        ibu_hamil = _get_ibu_hamil_by_user_id(db, current_user.id)
        if not ibu_hamil:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Profil ibu hamil tidak ditemukan."
            )
        
        if not ibu_hamil.perawat_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Anda belum ter-assign ke perawat. Silakan hubungi admin puskesmas."
            )
        
        # Get or create conversation
        conversation = crud_conversation.get_or_create(
            db, ibu_hamil_id=ibu_hamil.id, perawat_id=ibu_hamil.perawat_id
        )
        
    elif current_user.role == "perawat":
        # Perawat sends to a specific ibu hamil
        if not message_in.ibu_hamil_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="ibu_hamil_id harus diisi untuk perawat."
            )
        
        perawat = _get_perawat_by_user_id(db, current_user.id)
        if not perawat:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Profil perawat tidak ditemukan."
            )
        
        # Verify that this ibu hamil is assigned to this perawat
        ibu_hamil = crud_ibu_hamil.get(db, message_in.ibu_hamil_id)
        if not ibu_hamil:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Ibu hamil tidak ditemukan."
            )
        
        if ibu_hamil.perawat_id != perawat.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Ibu hamil ini tidak ter-assign ke Anda."
            )
        
        # Get or create conversation
        conversation = crud_conversation.get_or_create(
            db, ibu_hamil_id=message_in.ibu_hamil_id, perawat_id=perawat.id
        )
    
    if not conversation:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Gagal membuat atau mendapatkan conversation."
        )
    
    # Create message
    message = crud_message.create_message(
        db,
        conversation_id=conversation.id,
        sender_user_id=current_user.id,
        message_text=message_in.message_text
    )
    
    # Broadcast via WebSocket (non-blocking)
    try:
        from app.api.v1.endpoints.websocket_chat import broadcast_new_message
        import asyncio
        # Schedule async broadcast (non-blocking)
        try:
            loop = asyncio.get_event_loop()
            loop.create_task(broadcast_new_message(message.id, conversation.id))
        except RuntimeError:
            # If no event loop, create a new one
            asyncio.run(broadcast_new_message(message.id, conversation.id))
    except Exception:
        # WebSocket broadcast is optional, don't fail if it errors
        pass

    # Send notification to recipient if NOT connected to WebSocket
    try:
        # Determine recipient user_id
        if current_user.role == "ibu_hamil":
            # Message from ibu_hamil to perawat - get perawat's user_id
            perawat_obj = crud_perawat.get(db, ibu_hamil.perawat_id)
            recipient_user_id = perawat_obj.user_id if perawat_obj else None
        else:
            # Message from perawat to ibu_hamil
            recipient_user_id = ibu_hamil.user_id

        # Only send notification if recipient is NOT online in WebSocket
        if recipient_user_id and recipient_user_id not in manager.active_connections:
            notification_service.create_new_message_notification(
                db,
                conversation_id=conversation.id,
                sender_name=current_user.full_name,
                recipient_user_id=recipient_user_id,
            )

            # Also send push notification via Firebase
            try:
                firebase_service.send_notification_to_user(
                    db=db,
                    user_id=recipient_user_id,
                    title=f"Pesan baru dari {current_user.full_name}",
                    body=message_in.message_text[:100],
                    data={
                        "type": "new_message",
                        "conversation_id": str(conversation.id),
                        "sender_id": str(current_user.id),
                        "sender_name": current_user.full_name,
                    },
                    priority="high",
                )
            except Exception as e:
                logger.warning(f"Failed to send push notification for message: {str(e)}")
    except Exception:
        # Notification is optional, don't fail if it errors
        pass

    # Enrich with sender info
    sender = db.get(User, message.sender_user_id)
    return MessageResponse(
        id=message.id,
        conversation_id=message.conversation_id,
        sender_user_id=message.sender_user_id,
        sender_name=sender.full_name if sender else None,
        sender_role=sender.role if sender else None,
        message_text=message.message_text,
        is_read=message.is_read,
        read_at=message.read_at,
        created_at=message.created_at,
    )


@router.post(
    "/conversations/{conversation_id}/mark-read",
    response_model=dict,
    status_code=status.HTTP_200_OK,
    summary="Mark messages as read",
    description="""
    Mark messages in a conversation as read.
    
    If `message_ids` is provided in request body, only those specific messages will be marked as read.
    If `message_ids` is None or empty, all unread messages from the other participant will be marked as read.
    """,
)
def mark_messages_as_read(
    conversation_id: int,
    payload: Optional[MarkReadRequest] = None,
    current_user: User = Depends(require_role("ibu_hamil", "perawat")),
    db: Session = Depends(get_db),
) -> dict:
    """Mark messages as read."""
    conversation = crud_conversation.get(db, conversation_id)
    if not conversation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation tidak ditemukan."
        )
    
    _authorize_conversation_access(db, conversation, current_user)
    
    # Mark as read
    message_ids = payload.message_ids if payload else None
    read_count = crud_message.mark_as_read(
        db,
        conversation_id=conversation_id,
        message_ids=message_ids,
        reader_user_id=current_user.id
    )
    
    return {
        "message": f"{read_count} pesan telah ditandai sebagai sudah dibaca.",
        "read_count": read_count
    }


@router.get(
    "/conversations/{conversation_id}/unread-count",
    response_model=UnreadCountResponse,
    status_code=status.HTTP_200_OK,
    summary="Get unread message count",
    description="Get count of unread messages in a conversation.",
)
def get_unread_count(
    conversation_id: int,
    current_user: User = Depends(require_role("ibu_hamil", "perawat")),
    db: Session = Depends(get_db),
) -> UnreadCountResponse:
    """Get unread message count for a conversation."""
    conversation = crud_conversation.get(db, conversation_id)
    if not conversation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation tidak ditemukan."
        )
    
    _authorize_conversation_access(db, conversation, current_user)
    
    unread_count = crud_conversation.get_unread_count(
        db, conversation_id=conversation_id, user_id=current_user.id
    )
    
    return UnreadCountResponse(
        conversation_id=conversation_id,
        unread_count=unread_count
    )
