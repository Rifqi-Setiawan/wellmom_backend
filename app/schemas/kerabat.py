"""Pydantic schemas for `KerabatIbuHamil` (Family Member) domain objects."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict


class KerabatBase(BaseModel):
    kerabat_user_id: int
    ibu_hamil_id: int
    relation_type: str
    is_primary_contact: Optional[bool] = False
    can_view_records: Optional[bool] = True
    can_receive_notifications: Optional[bool] = True

    model_config = ConfigDict(json_schema_extra={
        "example": {
            "kerabat_user_id": 25,
            "ibu_hamil_id": 1,
            "relation_type": "Suami",
            "is_primary_contact": True,
            "can_view_records": True,
            "can_receive_notifications": True,
        }
    })


class KerabatCreate(KerabatBase):
    invite_code: Optional[str] = None

    model_config = ConfigDict(json_schema_extra={
        "example": {
            **KerabatBase.model_config.get("json_schema_extra", {}).get("example", {}),
            "invite_code": "INV-ABC123",
        }
    })


class KerabatUpdate(BaseModel):
    relation_type: Optional[str] = None
    is_primary_contact: Optional[bool] = None
    can_view_records: Optional[bool] = None
    can_receive_notifications: Optional[bool] = None

    model_config = ConfigDict(json_schema_extra={
        "example": {
            "is_primary_contact": False,
            "can_view_records": True,
            "can_receive_notifications": False,
        }
    })


class KerabatResponse(KerabatBase):
    id: int
    invite_code: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True, json_schema_extra={
        "example": {
            **KerabatBase.model_config.get("json_schema_extra", {}).get("example", {}),
            "id": 1,
            "invite_code": "INV-ABC123",
            "created_at": "2025-01-01T10:00:00Z",
            "updated_at": "2025-01-02T11:00:00Z",
        }
    })
