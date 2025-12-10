"""Pydantic schemas for `Notification` domain objects."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, field_validator


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
    user_id: int
    title: str
    message: str
    notification_type: str
    priority: Optional[str] = "normal"
    sent_via: str
    whatsapp_status: Optional[str] = None
    related_entity_type: Optional[str] = None
    related_entity_id: Optional[int] = None
    scheduled_for: Optional[datetime] = None

    @field_validator("notification_type")
    @classmethod
    def validate_notification_type(cls, v: str) -> str:
        if v not in NOTIFICATION_TYPES:
            raise ValueError(f"Notification type must be one of {sorted(NOTIFICATION_TYPES)}")
        return v

    @field_validator("priority")
    @classmethod
    def validate_priority(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and v not in PRIORITIES:
            raise ValueError(f"Priority must be one of {sorted(PRIORITIES)}")
        return v

    @field_validator("sent_via")
    @classmethod
    def validate_sent_via(cls, v: str) -> str:
        if v not in SENT_VIA_OPTIONS:
            raise ValueError(f"Sent via must be one of {sorted(SENT_VIA_OPTIONS)}")
        return v

    @field_validator("whatsapp_status")
    @classmethod
    def validate_whatsapp_status(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and v not in WHATSAPP_STATUSES:
            raise ValueError(f"WhatsApp status must be one of {sorted(WHATSAPP_STATUSES)}")
        return v

    model_config = ConfigDict(json_schema_extra={
        "example": {
            "user_id": 20,
            "title": "Pengingat Pemeriksaan Rutin",
            "message": "Halo Ibu Siti, saatnya untuk pemeriksaan rutin bulan ini. Jadwal: 15 Februari 2025.",
            "notification_type": "checkup_reminder",
            "priority": "normal",
            "sent_via": "both",
            "whatsapp_status": "pending",
            "related_entity_type": "health_record",
            "related_entity_id": 5,
            "scheduled_for": "2025-02-14T08:00:00Z",
        }
    })


class NotificationCreate(NotificationBase):
    model_config = ConfigDict(json_schema_extra={
        "example": NotificationBase.model_config.get("json_schema_extra", {}).get("example", {})
    })


class NotificationUpdate(BaseModel):
    title: Optional[str] = None
    message: Optional[str] = None
    notification_type: Optional[str] = None
    priority: Optional[str] = None
    is_read: Optional[bool] = None
    read_at: Optional[datetime] = None
    sent_via: Optional[str] = None
    whatsapp_status: Optional[str] = None
    sent_at: Optional[datetime] = None

    @field_validator("notification_type")
    @classmethod
    def validate_notification_type(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and v not in NOTIFICATION_TYPES:
            raise ValueError(f"Notification type must be one of {sorted(NOTIFICATION_TYPES)}")
        return v

    @field_validator("priority")
    @classmethod
    def validate_priority(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and v not in PRIORITIES:
            raise ValueError(f"Priority must be one of {sorted(PRIORITIES)}")
        return v

    @field_validator("sent_via")
    @classmethod
    def validate_sent_via(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and v not in SENT_VIA_OPTIONS:
            raise ValueError(f"Sent via must be one of {sorted(SENT_VIA_OPTIONS)}")
        return v

    @field_validator("whatsapp_status")
    @classmethod
    def validate_whatsapp_status(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and v not in WHATSAPP_STATUSES:
            raise ValueError(f"WhatsApp status must be one of {sorted(WHATSAPP_STATUSES)}")
        return v

    model_config = ConfigDict(json_schema_extra={
        "example": {
            "is_read": True,
            "read_at": "2025-02-14T10:00:00Z",
            "whatsapp_status": "delivered",
            "sent_at": "2025-02-14T08:00:00Z",
        }
    })


class NotificationResponse(NotificationBase):
    id: int
    is_read: bool
    read_at: Optional[datetime] = None
    sent_at: Optional[datetime] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True, json_schema_extra={
        "example": {
            **NotificationBase.model_config.get("json_schema_extra", {}).get("example", {}),
            "id": 1,
            "is_read": False,
            "read_at": None,
            "sent_at": None,
            "created_at": "2025-02-13T10:00:00Z",
        }
    })
