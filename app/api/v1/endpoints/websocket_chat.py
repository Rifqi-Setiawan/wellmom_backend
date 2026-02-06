"""WebSocket endpoints for real-time chat."""

import json
import logging
from typing import Dict, Set
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, HTTPException, status
from sqlalchemy.orm import Session
from starlette.websockets import WebSocketState

from app.api.deps import get_db
from app.crud import crud_conversation, crud_message, crud_user
from app.models.user import User
from app.core.security import decode_token

logger = logging.getLogger(__name__)


class ConnectionManager:
    """Manages WebSocket connections for real-time chat."""
    
    def __init__(self):
        # Map user_id -> Set of WebSocket connections
        self.active_connections: Dict[int, Set[WebSocket]] = {}
        # Map WebSocket -> user_id
        self.websocket_to_user: Dict[WebSocket, int] = {}
    
    async def connect(self, websocket: WebSocket, user_id: int):
        """Connect a WebSocket for a user."""
        await websocket.accept()
        
        if user_id not in self.active_connections:
            self.active_connections[user_id] = set()
        
        self.active_connections[user_id].add(websocket)
        self.websocket_to_user[websocket] = user_id
    
    def disconnect(self, websocket: WebSocket):
        """Disconnect a WebSocket."""
        user_id = self.websocket_to_user.get(websocket)
        if user_id:
            self.active_connections[user_id].discard(websocket)
            if not self.active_connections[user_id]:
                del self.active_connections[user_id]
            del self.websocket_to_user[websocket]
    
    async def send_personal_message(self, message: dict, user_id: int):
        """Send a message to a specific user (all their connections)."""
        if user_id in self.active_connections:
            disconnected = set()
            for connection in self.active_connections[user_id]:
                try:
                    await connection.send_json(message)
                except Exception:
                    disconnected.add(connection)
            
            # Clean up disconnected connections
            for conn in disconnected:
                self.disconnect(conn)
    
    async def broadcast_to_conversation(self, message: dict, conversation_id: int, db: Session):
        """Broadcast a message to all participants in a conversation."""
        # Get conversation participants
        conversation = crud_conversation.get(db, conversation_id)
        if not conversation:
            return
        
        from app.crud import crud_ibu_hamil, crud_perawat
        
        # Get user IDs of participants
        ibu_hamil = crud_ibu_hamil.get(db, conversation.ibu_hamil_id)
        perawat = crud_perawat.get(db, conversation.perawat_id)
        
        user_ids = []
        if ibu_hamil and ibu_hamil.user_id:
            user_ids.append(ibu_hamil.user_id)
        if perawat and perawat.user_id:
            user_ids.append(perawat.user_id)
        
        # Send to all participants
        for user_id in user_ids:
            await self.send_personal_message(message, user_id)


# Global connection manager instance
manager = ConnectionManager()

router = APIRouter(
    prefix="/ws/chat",
    tags=["WebSocket Chat"],
)


def get_user_from_token_sync(token: str, db: Session) -> User:
    """Get user from WebSocket token."""
    try:
        payload = decode_token(token)
        phone = payload.get("sub")
        if not phone:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token"
            )
        
        user = crud_user.get_by_phone(db, phone=phone)
        if not user or not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found or inactive"
            )
        
        return user
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials"
        ) from e


@router.websocket("/{conversation_id}")
async def websocket_endpoint(
    websocket: WebSocket,
    conversation_id: int,
    token: str = None,
):
    """
    WebSocket endpoint for real-time chat.
    
    Query parameters:
    - token: JWT token for authentication
    
    The WebSocket will:
    1. Receive new messages and broadcast them to conversation participants
    2. Send real-time updates when messages are received
    """
    # Get database session
    from app.database import SessionLocal
    db = SessionLocal()
    
    try:
        # Authenticate user
        if not token:
            await websocket.close(code=1008, reason="Token required")
            return
        
        try:
            user = get_user_from_token_sync(token, db)
        except HTTPException:
            await websocket.close(code=1008, reason="Invalid token")
            return
        
        # Verify user has access to this conversation
        conversation = crud_conversation.get(db, conversation_id)
        if not conversation:
            await websocket.close(code=1008, reason="Conversation not found")
            return
        
        # Check authorization
        from app.crud import crud_ibu_hamil, crud_perawat
        
        has_access = False
        if user.role == "ibu_hamil":
            ibu_hamil = crud_ibu_hamil.get_by_field(db, "user_id", user.id)
            if ibu_hamil and ibu_hamil.id == conversation.ibu_hamil_id:
                has_access = True
        elif user.role == "perawat":
            perawat = crud_perawat.get_by_field(db, "user_id", user.id)
            if perawat and perawat.id == conversation.perawat_id:
                has_access = True
        
        if not has_access:
            await websocket.close(code=1008, reason="Access denied")
            return
    finally:
        db.close()
    
    # Connect
    await manager.connect(websocket, user.id)
    
    try:
        # Send connection confirmation
        await websocket.send_json({
            "type": "connection",
            "message": "Connected to chat",
            "conversation_id": conversation_id,
            "user_id": user.id
        })
        
        # Listen for messages
        while True:
            data = await websocket.receive_text()
            
            try:
                message_data = json.loads(data)
                message_type = message_data.get("type")
                
                if message_type == "ping":
                    # Heartbeat
                    await websocket.send_json({"type": "pong"})
                
                elif message_type == "message":
                    # Handle incoming message (if needed for typing indicators, etc.)
                    # For now, messages are sent via REST API
                    pass
                
            except json.JSONDecodeError:
                await websocket.send_json({
                    "type": "error",
                    "message": "Invalid JSON format"
                })
    
    except WebSocketDisconnect:
        manager.disconnect(websocket)


# Function to broadcast new message via WebSocket
async def broadcast_new_message(message_id: int, conversation_id: int):
    """Broadcast a new message to all connected clients in the conversation."""
    from app.database import SessionLocal
    db = SessionLocal()
    
    try:
        # Get message details
        message = crud_message.get(db, message_id)
        if not message:
            return
        
        # Get sender info
        sender = crud_user.get(db, message.sender_user_id)
        
        # Prepare message payload
        payload = {
            "type": "new_message",
            "message": {
                "id": message.id,
                "conversation_id": message.conversation_id,
                "sender_user_id": message.sender_user_id,
                "sender_name": sender.full_name if sender else None,
                "sender_role": sender.role if sender else None,
                "message_text": message.message_text,
                "is_read": message.is_read,
                "read_at": message.read_at.isoformat() if message.read_at else None,
                "created_at": message.created_at.isoformat(),
            }
        }
        
        # Broadcast to conversation participants
        await manager.broadcast_to_conversation(payload, conversation_id, db)
    finally:
        db.close()


# Function to broadcast read receipt
async def broadcast_read_receipt(db: Session, conversation_id: int, reader_user_id: int, read_count: int):
    """Broadcast read receipt to conversation participants."""
    payload = {
        "type": "read_receipt",
        "conversation_id": conversation_id,
        "reader_user_id": reader_user_id,
        "read_count": read_count,
    }
    
    await manager.broadcast_to_conversation(payload, conversation_id, db)
