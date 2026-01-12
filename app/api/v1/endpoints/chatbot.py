"""AI Chatbot endpoints for WellMom Assistant."""

import logging
from datetime import datetime, timedelta
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_active_user, get_db, require_role
from app.config import settings
from app.core.rate_limiter import get_rate_limiter
from app.crud import (
    crud_chatbot_conversation,
    crud_chatbot_message,
    crud_chatbot_user_usage,
    crud_chatbot_global_usage,
)
from app.models.user import User
from app.schemas.chatbot import (
    ChatbotSendRequest,
    ChatbotSendResponse,
    ChatbotConversationResponse,
    ChatbotMessageResponse,
    ChatbotHistoryResponse,
    QuotaInfoResponse,
    ChatbotNewConversationRequest,
)
from app.services.chatbot_service import chatbot_service, get_chatbot_service

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/chatbot",
    tags=["AI Chatbot"],
)


def _calculate_reset_time() -> datetime:
    """Calculate next reset time (midnight WIB / Asia/Jakarta).
    
    Note: Returns UTC datetime for next midnight in Jakarta timezone.
    """
    try:
        from pytz import timezone
        
        # Get current time in Jakarta timezone
        jakarta_tz = timezone('Asia/Jakarta')
        now_jakarta = datetime.now(jakarta_tz)
        
        # Calculate next midnight
        if now_jakarta.hour == 0 and now_jakarta.minute == 0:
            # Already at midnight, reset is tomorrow
            reset_time = (now_jakarta + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
        else:
            # Reset is today at midnight
            reset_time = now_jakarta.replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1)
        
        # Convert to UTC for storage
        return reset_time.astimezone(timezone('UTC')).replace(tzinfo=None)
    except ImportError:
        # Fallback: use UTC midnight if pytz not available
        now_utc = datetime.utcnow()
        reset_time = (now_utc + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
        return reset_time


@router.post(
    "/send",
    response_model=ChatbotSendResponse,
    status_code=status.HTTP_200_OK,
    summary="Kirim pesan ke AI chatbot",
    description="""
Kirim pesan ke AI chatbot WellMom Assistant dan dapatkan respons.

**Akses:**
- Hanya dapat diakses oleh ibu hamil dan kerabat (role: ibu_hamil, kerabat)

**Flow:**
1. Cek rate limit (10 req/min per user)
2. Cek user daily quota
3. Cek global daily quota
4. Kirim pesan ke Gemini API
5. Simpan pesan dan respons ke database
6. Update token usage
7. Return respons dengan quota info

**Query Parameters:**
- `conversation_id` (optional): ID conversation yang sedang berlangsung. Jika tidak diberikan, akan membuat conversation baru.

**Catatan:**
- Jika conversation_id tidak diberikan, akan membuat conversation baru otomatis
- Title conversation akan di-generate dari pesan pertama
- Token usage akan di-track untuk quota management
""",
    responses={
        200: {
            "description": "Pesan berhasil dikirim dan respons diterima",
            "content": {
                "application/json": {
                    "example": {
                        "response": "Halo Ibu! Untuk trimester pertama, makanan yang baik antara lain...",
                        "conversation_id": 1,
                        "quota": {
                            "used_today": 5000,
                            "limit": 10000,
                            "remaining": 5000,
                            "resets_at": "2026-01-10T00:00:00+07:00"
                        }
                    }
                }
            }
        },
        400: {
            "description": "Request tidak valid",
            "content": {
                "application/json": {
                    "example": {"detail": "Message tidak boleh kosong"}
                }
            }
        },
        403: {
            "description": "Quota habis atau tidak memiliki akses",
            "content": {
                "application/json": {
                    "examples": {
                        "quota_exceeded": {
                            "summary": "Quota harian habis",
                            "value": {"detail": "Batas penggunaan chatbot harian Anda telah habis. Silakan coba lagi besok."}
                        },
                        "global_quota_exceeded": {
                            "summary": "Global quota habis",
                            "value": {"detail": "Layanan chatbot sedang tidak tersedia. Silakan coba lagi besok."}
                        }
                    }
                }
            }
        },
        404: {
            "description": "Conversation tidak ditemukan",
            "content": {
                "application/json": {
                    "example": {"detail": "Percakapan tidak ditemukan"}
                }
            }
        },
        429: {
            "description": "Rate limit exceeded",
            "content": {
                "application/json": {
                    "example": {"detail": "Terlalu banyak permintaan. Silakan tunggu 45 detik."}
                }
            }
        },
        503: {
            "description": "Layanan AI tidak tersedia",
            "content": {
                "application/json": {
                    "example": {"detail": "Layanan AI sedang mengalami gangguan. Silakan coba lagi."}
                }
            }
        }
    }
)
async def send_message(
    request: ChatbotSendRequest,
    conversation_id: Optional[int] = Query(None, description="ID conversation (optional, None = new conversation)"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("ibu_hamil", "kerabat")),
) -> ChatbotSendResponse:
    """
    Kirim pesan ke AI chatbot dan dapatkan respons.
    
    Args:
        request: Request body dengan message
        conversation_id: Optional conversation ID (None = new conversation)
        db: Database session
        current_user: Current authenticated user (must be ibu_hamil or kerabat)
        
    Returns:
        ChatbotSendResponse: AI response, conversation_id, dan quota info
        
    Raises:
        HTTPException 400: Invalid request
        HTTPException 403: Quota exceeded
        HTTPException 404: Conversation not found
        HTTPException 429: Rate limited
        HTTPException 503: AI service unavailable
    """
    # Step 1: Check rate limit
    rate_limiter = get_rate_limiter()
    is_allowed, seconds_until_reset = await rate_limiter.is_allowed(current_user.id)
    if not is_allowed:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Terlalu banyak permintaan. Silakan tunggu {seconds_until_reset} detik.",
        )
    
    # Step 2: Check user quota
    can_use_user, remaining_user = crud_chatbot_user_usage.check_user_quota(db, user_id=current_user.id)
    if not can_use_user:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Batas penggunaan chatbot harian Anda telah habis. Silakan coba lagi besok.",
        )
    
    # Step 3: Check global quota
    can_use_global, remaining_global = crud_chatbot_global_usage.check_global_quota(db)
    if not can_use_global:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Layanan chatbot sedang tidak tersedia. Silakan coba lagi besok.",
        )
    
    # Step 4: Get or create conversation
    if conversation_id:
        conversation = crud_chatbot_conversation.get_conversation(
            db, conversation_id=conversation_id, user_id=current_user.id
        )
        if not conversation:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Percakapan tidak ditemukan.",
            )
    else:
        # Create new conversation with title from first message
        title = request.message[:50] + "..." if len(request.message) > 50 else request.message
        conversation = crud_chatbot_conversation.create_conversation(
            db, user_id=current_user.id, title=title
        )
    
    # Step 5: Get conversation history for context
    history_messages = crud_chatbot_message.get_conversation_messages(
        db, conversation_id=conversation.id, limit=settings.CHATBOT_MAX_HISTORY_MESSAGES
    )
    history = chatbot_service.prepare_history_from_messages(history_messages)
    
    # Step 6: Send message to Gemini API
    try:
        response_text, input_tokens, output_tokens = await chatbot_service.chat(
            message=request.message,
            history=history,
            timeout=settings.CHATBOT_REQUEST_TIMEOUT
        )
    except TimeoutError as e:
        logger.error(f"Chatbot request timeout: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Waktu respons habis. Silakan coba lagi dalam beberapa saat.",
        )
    except ValueError as e:
        # ValueError from chatbot_service contains user-friendly message
        error_msg = str(e)
        error_lower = error_msg.lower()
        logger.error(f"Chatbot service error: {error_msg}", exc_info=True)
        
        # Use the error message from chatbot_service directly (already user-friendly)
        # But provide more specific HTTP status codes if possible
        if "tidak ditemukan" in error_msg or "not found" in error_lower:
            status_code = status.HTTP_503_SERVICE_UNAVAILABLE
            detail = error_msg if error_msg else "Model AI tidak ditemukan. Silakan hubungi administrator."
        elif "quota" in error_lower or "rate limit" in error_lower or "sibuk" in error_lower:
            status_code = status.HTTP_503_SERVICE_UNAVAILABLE
            detail = error_msg if error_msg else "Layanan AI sedang sibuk. Silakan coba lagi dalam beberapa saat."
        elif "tidak valid" in error_lower or "api key" in error_lower or "authentication" in error_lower:
            status_code = status.HTTP_503_SERVICE_UNAVAILABLE
            detail = error_msg if error_msg else "Konfigurasi layanan AI tidak valid. Silakan hubungi administrator."
        else:
            status_code = status.HTTP_503_SERVICE_UNAVAILABLE
            detail = error_msg if error_msg else "Layanan AI sedang mengalami gangguan. Silakan coba lagi."
        
        raise HTTPException(
            status_code=status_code,
            detail=detail,
        )
    except Exception as e:
        # Log the actual error for debugging
        error_type = type(e).__name__
        error_msg = str(e)
        logger.error(f"Unexpected error in chatbot service: {error_type}: {error_msg}", exc_info=True)
        
        # Provide user-friendly error message
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Layanan AI sedang mengalami gangguan. Silakan coba lagi dalam beberapa saat.",
        )
    
    # Step 7: Save messages to database
    total_tokens = input_tokens + output_tokens
    
    # Save user message
    crud_chatbot_message.add_message(
        db,
        conversation_id=conversation.id,
        role="user",
        content=request.message,
        input_tokens=input_tokens,
        output_tokens=0
    )
    
    # Save assistant response
    crud_chatbot_message.add_message(
        db,
        conversation_id=conversation.id,
        role="assistant",
        content=response_text,
        input_tokens=0,
        output_tokens=output_tokens
    )
    
    # Step 8: Update conversation updated_at
    conversation.updated_at = datetime.utcnow()
    db.add(conversation)
    db.commit()
    
    # Step 9: Update token usage
    crud_chatbot_user_usage.increment_user_usage(db, user_id=current_user.id, tokens=total_tokens)
    crud_chatbot_global_usage.increment_global_usage(db, tokens=total_tokens)
    
    # Step 10: Record rate limit
    await rate_limiter.record_request(current_user.id)
    
    # Step 11: Get updated quota info
    _, remaining_after = crud_chatbot_user_usage.check_user_quota(db, user_id=current_user.id)
    usage = crud_chatbot_user_usage.get_or_create_user_usage(db, user_id=current_user.id)
    
    quota_info = QuotaInfoResponse(
        used_today=usage.tokens_used,
        limit=settings.CHATBOT_USER_DAILY_TOKEN_LIMIT,
        remaining=remaining_after,
        resets_at=_calculate_reset_time()
    )
    
    return ChatbotSendResponse(
        response=response_text,
        conversation_id=conversation.id,
        quota=quota_info
    )


@router.get(
    "/conversations",
    response_model=List[ChatbotConversationResponse],
    status_code=status.HTTP_200_OK,
    summary="Daftar conversation chatbot",
    description="""
Dapatkan daftar semua conversation chatbot milik user yang sedang login.

**Akses:**
- Hanya dapat diakses oleh ibu hamil dan kerabat (role: ibu_hamil, kerabat)
- Hanya menampilkan conversation milik user yang sedang login

**Query Parameters:**
- `skip`: Number of conversations to skip (for pagination)
- `limit`: Maximum number of conversations to return (default: 20, max: 100)
""",
    responses={
        200: {
            "description": "Daftar conversation berhasil diambil",
            "content": {
                "application/json": {
                    "example": [
                        {
                            "id": 1,
                            "user_id": 10,
                            "title": "Pertanyaan tentang Nutrisi Kehamilan",
                            "is_active": True,
                            "message_count": 5,
                            "created_at": "2026-01-09T10:00:00Z",
                            "updated_at": "2026-01-09T10:15:00Z"
                        }
                    ]
                }
            }
        },
        403: {
            "description": "Tidak memiliki akses",
            "content": {
                "application/json": {
                    "example": {"detail": "Hanya ibu hamil dan kerabat yang dapat mengakses endpoint ini"}
                }
            }
        }
    }
)
async def get_conversations(
    skip: int = Query(0, ge=0, description="Number of conversations to skip"),
    limit: int = Query(20, ge=1, le=100, description="Maximum number of conversations to return"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("ibu_hamil", "kerabat")),
) -> List[ChatbotConversationResponse]:
    """
    Dapatkan daftar conversation milik user.
    
    Args:
        skip: Number of conversations to skip
        limit: Maximum number of conversations to return
        db: Database session
        current_user: Current authenticated user
        
    Returns:
        List[ChatbotConversationResponse]: List of conversations
    """
    conversations = crud_chatbot_conversation.get_user_conversations(
        db, user_id=current_user.id, skip=skip, limit=limit
    )
    
    # Enrich with message count
    result = []
    for conv in conversations:
        messages = crud_chatbot_message.get_conversation_messages(
            db, conversation_id=conv.id, limit=1000
        )
        result.append(ChatbotConversationResponse(
            id=conv.id,
            user_id=conv.user_id,
            title=conv.title,
            is_active=conv.is_active,
            message_count=len(messages),
            created_at=conv.created_at,
            updated_at=conv.updated_at,
        ))
    
    return result


@router.get(
    "/conversations/{conversation_id}",
    response_model=ChatbotHistoryResponse,
    status_code=status.HTTP_200_OK,
    summary="History conversation chatbot",
    description="""
Dapatkan history lengkap pesan dalam satu conversation.

**Akses:**
- Hanya dapat diakses oleh ibu hamil dan kerabat (role: ibu_hamil, kerabat)
- Hanya dapat melihat conversation milik sendiri

**Response:**
- Conversation info (id, title, created_at, updated_at)
- List semua messages dalam conversation (ordered by created_at)
""",
    responses={
        200: {
            "description": "History conversation berhasil diambil",
            "content": {
                "application/json": {
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
                                "content": "Halo Ibu! Untuk trimester pertama...",
                                "input_tokens": 0,
                                "output_tokens": 120,
                                "created_at": "2026-01-09T10:00:05Z"
                            }
                        ]
                    }
                }
            }
        },
        403: {
            "description": "Tidak memiliki akses",
            "content": {
                "application/json": {
                    "example": {"detail": "Hanya ibu hamil dan kerabat yang dapat mengakses endpoint ini"}
                }
            }
        },
        404: {
            "description": "Conversation tidak ditemukan",
            "content": {
                "application/json": {
                    "example": {"detail": "Percakapan tidak ditemukan"}
                }
            }
        }
    }
)
async def get_conversation_history(
    conversation_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("ibu_hamil", "kerabat")),
) -> ChatbotHistoryResponse:
    """
    Dapatkan history pesan dalam satu conversation.
    
    Args:
        conversation_id: ID conversation
        db: Database session
        current_user: Current authenticated user
        
    Returns:
        ChatbotHistoryResponse: Conversation info dan list messages
        
    Raises:
        HTTPException 404: Conversation not found or not owned by user
    """
    conversation = crud_chatbot_conversation.get_conversation(
        db, conversation_id=conversation_id, user_id=current_user.id
    )
    if not conversation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Percakapan tidak ditemukan.",
        )
    
    # Get messages
    messages = crud_chatbot_message.get_conversation_messages(
        db, conversation_id=conversation_id, limit=1000
    )
    
    # Format response
    conversation_response = ChatbotConversationResponse(
        id=conversation.id,
        user_id=conversation.user_id,
        title=conversation.title,
        is_active=conversation.is_active,
        message_count=len(messages),
        created_at=conversation.created_at,
        updated_at=conversation.updated_at,
    )
    
    messages_response = [
        ChatbotMessageResponse(
            id=msg.id,
            role=msg.role,
            content=msg.content,
            input_tokens=msg.input_tokens,
            output_tokens=msg.output_tokens,
            created_at=msg.created_at,
        )
        for msg in messages
    ]
    
    return ChatbotHistoryResponse(
        conversation=conversation_response,
        messages=messages_response
    )


@router.delete(
    "/conversations/{conversation_id}",
    status_code=status.HTTP_200_OK,
    summary="Hapus conversation chatbot",
    description="""
Hapus (soft delete) conversation chatbot.

**Akses:**
- Hanya dapat diakses oleh ibu hamil dan kerabat (role: ibu_hamil, kerabat)
- Hanya dapat menghapus conversation milik sendiri

**Catatan:**
- Conversation akan di-soft delete (is_active = False)
- Messages dalam conversation tetap tersimpan di database
""",
    responses={
        200: {
            "description": "Conversation berhasil dihapus",
            "content": {
                "application/json": {
                    "example": {"message": "Conversation berhasil dihapus"}
                }
            }
        },
        403: {
            "description": "Tidak memiliki akses",
            "content": {
                "application/json": {
                    "example": {"detail": "Hanya ibu hamil dan kerabat yang dapat mengakses endpoint ini"}
                }
            }
        },
        404: {
            "description": "Conversation tidak ditemukan",
            "content": {
                "application/json": {
                    "example": {"detail": "Percakapan tidak ditemukan"}
                }
            }
        }
    }
)
async def delete_conversation(
    conversation_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("ibu_hamil", "kerabat")),
) -> dict:
    """
    Hapus conversation.
    
    Args:
        conversation_id: ID conversation yang akan dihapus
        db: Database session
        current_user: Current authenticated user
        
    Returns:
        dict: Success message
        
    Raises:
        HTTPException 404: Conversation not found or not owned by user
    """
    deleted = crud_chatbot_conversation.delete_conversation(
        db, conversation_id=conversation_id, user_id=current_user.id
    )
    
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Percakapan tidak ditemukan.",
        )
    
    return {"message": "Conversation berhasil dihapus"}


@router.get(
    "/quota",
    response_model=QuotaInfoResponse,
    status_code=status.HTTP_200_OK,
    summary="Cek quota penggunaan chatbot",
    description="""
Cek sisa quota penggunaan chatbot hari ini untuk user yang sedang login.

**Akses:**
- Hanya dapat diakses oleh ibu hamil dan kerabat (role: ibu_hamil, kerabat)

**Response:**
- `used_today`: Jumlah token yang sudah digunakan hari ini
- `limit`: Batas maksimal token per hari
- `remaining`: Sisa token yang masih bisa digunakan
- `resets_at`: Waktu reset quota (midnight WIB)
""",
    responses={
        200: {
            "description": "Quota info berhasil diambil",
            "content": {
                "application/json": {
                    "example": {
                        "used_today": 5000,
                        "limit": 10000,
                        "remaining": 5000,
                        "resets_at": "2026-01-10T00:00:00+07:00"
                    }
                }
            }
        },
        403: {
            "description": "Tidak memiliki akses",
            "content": {
                "application/json": {
                    "example": {"detail": "Hanya ibu hamil dan kerabat yang dapat mengakses endpoint ini"}
                }
            }
        }
    }
)
async def get_quota(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("ibu_hamil", "kerabat")),
) -> QuotaInfoResponse:
    """
    Cek sisa quota penggunaan chatbot hari ini.
    
    Args:
        db: Database session
        current_user: Current authenticated user
        
    Returns:
        QuotaInfoResponse: Quota information
    """
    usage = crud_chatbot_user_usage.get_or_create_user_usage(db, user_id=current_user.id)
    _, remaining = crud_chatbot_user_usage.check_user_quota(db, user_id=current_user.id)
    
    return QuotaInfoResponse(
        used_today=usage.tokens_used,
        limit=settings.CHATBOT_USER_DAILY_TOKEN_LIMIT,
        remaining=remaining,
        resets_at=_calculate_reset_time()
    )


@router.post(
    "/conversations/new",
    response_model=ChatbotConversationResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Buat conversation baru",
    description="""
Buat conversation baru untuk chatbot.

**Akses:**
- Hanya dapat diakses oleh ibu hamil dan kerabat (role: ibu_hamil, kerabat)

**Catatan:**
- Endpoint ini opsional, karena `/send` juga bisa membuat conversation baru otomatis
- Title bisa diisi manual atau akan di-generate dari pesan pertama saat mengirim pesan
""",
    responses={
        201: {
            "description": "Conversation baru berhasil dibuat",
            "content": {
                "application/json": {
                    "example": {
                        "id": 1,
                        "user_id": 10,
                        "title": "Pertanyaan tentang Nutrisi Kehamilan",
                        "is_active": True,
                        "message_count": 0,
                        "created_at": "2026-01-09T10:00:00Z",
                        "updated_at": "2026-01-09T10:00:00Z"
                    }
                }
            }
        },
        403: {
            "description": "Tidak memiliki akses",
            "content": {
                "application/json": {
                    "example": {"detail": "Hanya ibu hamil dan kerabat yang dapat mengakses endpoint ini"}
                }
            }
        }
    }
)
async def create_new_conversation(
    request: Optional[ChatbotNewConversationRequest] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("ibu_hamil", "kerabat")),
) -> ChatbotConversationResponse:
    """
    Buat conversation baru (opsional, /send juga bisa buat otomatis).
    
    Args:
        request: Optional request body dengan title
        db: Database session
        current_user: Current authenticated user
        
    Returns:
        ChatbotConversationResponse: Created conversation
    """
    title = request.title if request else None
    conversation = crud_chatbot_conversation.create_conversation(
        db, user_id=current_user.id, title=title
    )
    
    return ChatbotConversationResponse(
        id=conversation.id,
        user_id=conversation.user_id,
        title=conversation.title,
        is_active=conversation.is_active,
        message_count=0,
        created_at=conversation.created_at,
        updated_at=conversation.updated_at,
    )


@router.get(
    "/status",
    status_code=status.HTTP_200_OK,
    summary="Cek status layanan chatbot",
    description="""
Cek status dan ketersediaan layanan chatbot AI.

**Akses:**
- Dapat diakses oleh semua user yang terautentikasi (ibu_hamil, kerabat, perawat, admin)

**Response:**
- `is_available`: Apakah layanan chatbot tersedia
- `model_name`: Nama model AI yang digunakan
- `api_key_configured`: Apakah API key sudah dikonfigurasi
- `error`: Pesan error jika ada

**Catatan:**
- Endpoint ini berguna untuk troubleshooting dan monitoring
- Jika `is_available` = false, berarti ada masalah dengan konfigurasi atau API key
""",
    responses={
        200: {
            "description": "Status layanan chatbot",
            "content": {
                "application/json": {
                    "examples": {
                        "available": {
                            "summary": "Layanan tersedia",
                            "value": {
                                "is_available": True,
                                "model_name": "gemini-1.5-flash-latest",
                                "api_key_configured": True,
                                "error": None
                            }
                        },
                        "unavailable": {
                            "summary": "Layanan tidak tersedia",
                            "value": {
                                "is_available": False,
                                "model_name": None,
                                "api_key_configured": True,
                                "error": "Model tidak terinisialisasi"
                            }
                        }
                    }
                }
            }
        }
    }
)
async def get_chatbot_status(
    current_user: User = Depends(get_current_active_user),
) -> dict:
    """
    Cek status layanan chatbot.
    
    Args:
        current_user: Current authenticated user
        
    Returns:
        dict: Status information
    """
    try:
        service = get_chatbot_service()
        status_info = service.get_status()
        return status_info
    except Exception as e:
        logger.error(f"Error checking chatbot status: {str(e)}", exc_info=True)
        return {
            "is_available": False,
            "model_name": None,
            "api_key_configured": bool(settings.GEMINI_API_KEY),
            "error": f"Gagal memeriksa status: {str(e)}"
        }


__all__ = ["router"]
