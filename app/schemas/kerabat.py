"""Pydantic schemas for `KerabatIbuHamil` (Family Member) domain objects."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict


class KerabatBase(BaseModel):
    kerabat_user_id: Optional[int] = None  # Nullable karena belum ada user saat generate invite
    ibu_hamil_id: int
    relation_type: Optional[str] = None  # Nullable karena akan diisi setelah kerabat login
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
    invite_code_created_at: Optional[datetime] = None
    invite_code_expires_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True, json_schema_extra={
        "example": {
            **KerabatBase.model_config.get("json_schema_extra", {}).get("example", {}),
            "id": 1,
            "invite_code": "INV-ABC123",
            "invite_code_created_at": "2025-01-01T10:00:00Z",
            "invite_code_expires_at": "2025-01-02T10:00:00Z",
            "created_at": "2025-01-01T10:00:00Z",
            "updated_at": "2025-01-02T11:00:00Z",
        }
    })


# ============================================================================
# INVITATION CODE SCHEMAS
# ============================================================================

class InviteCodeGenerateResponse(BaseModel):
    """Response untuk generate invitation code."""
    invite_code: str
    expires_at: datetime
    ibu_hamil_id: int
    
    model_config = ConfigDict(json_schema_extra={
        "example": {
            "invite_code": "ABC123XY",
            "expires_at": "2025-01-02T10:00:00Z",
            "ibu_hamil_id": 1
        }
    })


class InviteCodeLoginRequest(BaseModel):
    """Request untuk login dengan invitation code."""
    invite_code: str
    
    model_config = ConfigDict(json_schema_extra={
        "example": {
            "invite_code": "ABC123XY"
        }
    })


class InviteCodeLoginResponse(BaseModel):
    """Response untuk login dengan invitation code."""
    access_token: str
    token_type: str = "bearer"
    kerabat_id: int
    ibu_hamil_id: int
    ibu_hamil_name: str
    requires_profile_completion: bool = True  # True jika belum complete profile
    
    model_config = ConfigDict(json_schema_extra={
        "example": {
            "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
            "token_type": "bearer",
            "kerabat_id": 1,
            "ibu_hamil_id": 1,
            "ibu_hamil_name": "Siti Aminah",
            "requires_profile_completion": True
        }
    })


class KerabatCompleteProfileRequest(BaseModel):
    """Request untuk complete profile kerabat setelah login."""
    full_name: str
    relation_type: str
    phone: Optional[str] = None  # Optional, bisa diisi nanti
    
    model_config = ConfigDict(json_schema_extra={
        "example": {
            "full_name": "Budi Santoso",
            "relation_type": "Suami",
            "phone": "+6281234567890"
        }
    })
