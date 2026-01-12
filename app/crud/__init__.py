"""CRUD operations package - exports singleton instances for all models."""

from .base import CRUDBase
from .user import crud_user
from .puskesmas import crud_puskesmas
from .perawat import crud_perawat
from .ibu_hamil import crud_ibu_hamil
from .kerabat import crud_kerabat
from .health_record import crud_health_record
from .notification import crud_notification
from .transfer_request import crud_transfer_request
from .conversation import crud_conversation
from .message import crud_message
from .post_category import crud_post_category
from .post import crud_post
from .post_like import crud_post_like
from .post_reply import crud_post_reply
from .chatbot import (
    crud_chatbot_conversation,
    crud_chatbot_message,
    crud_chatbot_user_usage,
    crud_chatbot_global_usage,
)


__all__ = [
    # Base
    "CRUDBase",
    # CRUD instances
    "crud_user",
    "crud_puskesmas",
    "crud_perawat",
    "crud_ibu_hamil",
    "crud_kerabat",
    "crud_health_record",
    "crud_notification",
    "crud_transfer_request",
    "crud_conversation",
    "crud_message",
    "crud_post_category",
    "crud_post",
    "crud_post_like",
    "crud_post_reply",
    # Chatbot CRUD
    "crud_chatbot_conversation",
    "crud_chatbot_message",
    "crud_chatbot_user_usage",
    "crud_chatbot_global_usage",
]
