"""Pydantic schemas for Notification."""

from datetime import datetime
from typing import Optional, List

from pydantic import BaseModel, ConfigDict, Field, field_validator


# Valid values for notification fields
NOTIFICATION_TYPES = {
    "checkup_reminder",
    "assignment",
    "health_alert",
    "iot_alert",
    "referral",
    "transfer_update",
    "system",
}

PRIORITIES = {"low", "normal", "high", "urgent"}
SENT_VIA_OPTIONS = {"in_app", "whatsapp", "both"}
WHATSAPP_STATUSES = {"pending", "sent", "delivered", "failed"}


class NotificationBase(BaseModel):
    """Base schema for Notification - common fields."""
    title: str = Field(..., min_length=1, max_length=255, description="Notification title")
    message: str = Field(..., min_length=1, description="Notification message content")
    notification_type: str = Field(..., description="Type of notification")
    priority: str = Field(default="normal", description="Priority level")
    sent_via: str = Field(default="in_app", description="Delivery channel")
    related_entity_type: Optional[str] = Field(None, description="Related entity type (e.g., 'ibu_hamil', 'conversation')")
    related_entity_id: Optional[int] = Field(None, description="Related entity ID")

    @field_validator("notification_type")
    @classmethod
    def validate_notification_type(cls, v: str) -> str:
        if v not in NOTIFICATION_TYPES:
            raise ValueError(f"notification_type must be one of: {sorted(NOTIFICATION_TYPES)}")
        return v

    @field_validator("priority")
    @classmethod
    def validate_priority(cls, v: str) -> str:
        if v not in PRIORITIES:
            raise ValueError(f"priority must be one of: {sorted(PRIORITIES)}")
        return v

    @field_validator("sent_via")
    @classmethod
    def validate_sent_via(cls, v: str) -> str:
        if v not in SENT_VIA_OPTIONS:
            raise ValueError(f"sent_via must be one of: {sorted(SENT_VIA_OPTIONS)}")
        return v


class NotificationCreate(NotificationBase):
    """Schema for creating a new notification."""
    user_id: int = Field(..., description="ID of the user to receive the notification")
    whatsapp_status: Optional[str] = Field(None, description="WhatsApp delivery status")
    scheduled_for: Optional[datetime] = Field(None, description="Scheduled delivery time")

    @field_validator("whatsapp_status")
    @classmethod
    def validate_whatsapp_status(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and v not in WHATSAPP_STATUSES:
            raise ValueError(f"whatsapp_status must be one of: {sorted(WHATSAPP_STATUSES)}")
        return v

    model_config = ConfigDict(json_schema_extra={
        "example": {
            "user_id": 20,
            "title": "Pengingat Pemeriksaan Rutin",
            "message": "Halo Ibu Siti, saatnya untuk pemeriksaan rutin bulan ini.",
            "notification_type": "checkup_reminder",
            "priority": "normal",
            "sent_via": "in_app",
            "related_entity_type": "health_record",
            "related_entity_id": 5,
        }
    })


class NotificationUpdate(BaseModel):
    """Schema for updating a notification."""
    is_read: Optional[bool] = Field(None, description="Mark as read/unread")
    read_at: Optional[datetime] = Field(None, description="Timestamp when notification was read")

    model_config = ConfigDict(json_schema_extra={
        "example": {
            "is_read": True,
            "read_at": "2025-02-14T10:00:00Z",
        }
    })


class NotificationResponse(BaseModel):
    """Schema for Notification API response."""
    id: int
    user_id: int
    title: str
    message: str
    notification_type: str
    priority: str
    sent_via: str
    related_entity_type: Optional[str] = None
    related_entity_id: Optional[int] = None
    is_read: bool
    read_at: Optional[datetime] = None
    created_at: datetime
    sent_at: Optional[datetime] = None
    whatsapp_status: Optional[str] = None
    scheduled_for: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True, json_schema_extra={
        "example": {
            "id": 1,
            "user_id": 20,
            "title": "Pengingat Pemeriksaan Rutin",
            "message": "Halo Ibu Siti, saatnya untuk pemeriksaan rutin bulan ini.",
            "notification_type": "checkup_reminder",
            "priority": "normal",
            "sent_via": "in_app",
            "related_entity_type": "health_record",
            "related_entity_id": 5,
            "is_read": False,
            "read_at": None,
            "created_at": "2025-02-13T10:00:00Z",
            "sent_at": None,
            "whatsapp_status": None,
            "scheduled_for": None,
        }
    })


class NotificationListResponse(BaseModel):
    """Response schema for listing notifications."""
    notifications: List[NotificationResponse]
    total: int
    unread_count: int

    model_config = ConfigDict(json_schema_extra={
        "example": {
            "notifications": [
                {
                    "id": 1,
                    "user_id": 20,
                    "title": "Pengingat Pemeriksaan Rutin",
                    "message": "Halo Ibu Siti, saatnya untuk pemeriksaan rutin.",
                    "notification_type": "checkup_reminder",
                    "priority": "normal",
                    "sent_via": "in_app",
                    "is_read": False,
                    "created_at": "2025-02-13T10:00:00Z",
                }
            ],
            "total": 1,
            "unread_count": 1,
        }
    })


class UnreadCountResponse(BaseModel):
    """Response schema for unread notification count."""
    unread_count: int

    model_config = ConfigDict(json_schema_extra={
        "example": {
            "unread_count": 5
        }
    })


class MarkAllReadResponse(BaseModel):
    """Response schema for mark all notifications as read."""
    message: str
    read_count: int

    model_config = ConfigDict(json_schema_extra={
        "example": {
            "message": "5 notifikasi telah ditandai sebagai sudah dibaca",
            "read_count": 5
        }
    })


class DeleteNotificationResponse(BaseModel):
    """Response schema for delete notification."""
    message: str

    model_config = ConfigDict(json_schema_extra={
        "example": {
            "message": "Notifikasi berhasil dihapus"
        }
    })
