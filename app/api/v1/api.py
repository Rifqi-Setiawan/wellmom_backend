"""API v1 router aggregator."""

from fastapi import APIRouter

from app.api.v1.endpoints import auth, users, puskesmas, perawat, ibu_hamil, chat, websocket_chat, health_record, forum

api_router = APIRouter(prefix="/api/v1")

api_router.include_router(auth.router)
api_router.include_router(users.router)
api_router.include_router(puskesmas.router)
api_router.include_router(perawat.router)
api_router.include_router(ibu_hamil.router)
api_router.include_router(chat.router)
api_router.include_router(websocket_chat.router)
api_router.include_router(health_record.router)
api_router.include_router(forum.router)

__all__ = ["api_router"]
