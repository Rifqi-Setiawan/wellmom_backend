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


class KerabatCompleteProfileResponse(BaseModel):
    """Response untuk complete profile kerabat - termasuk token baru jika phone di-update."""
    kerabat: KerabatResponse
    access_token: Optional[str] = None  # Token baru jika phone di-update
    token_type: str = "bearer"
    message: str = "Profile berhasil diupdate"

    model_config = ConfigDict(json_schema_extra={
        "example": {
            "kerabat": {
                "id": 1,
                "kerabat_user_id": 25,
                "ibu_hamil_id": 1,
                "relation_type": "Suami",
                "can_view_records": True,
                "can_receive_notifications": True,
                "created_at": "2025-01-01T10:00:00Z",
                "updated_at": "2025-01-02T11:00:00Z"
            },
            "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
            "token_type": "bearer",
            "message": "Profile berhasil diupdate. Gunakan access_token baru untuk request selanjutnya."
        }
    })


# ============================================================================
# KERABAT DASHBOARD & FEATURE SCHEMAS
# ============================================================================

class IbuHamilSummary(BaseModel):
    """Summary info ibu hamil untuk kerabat dashboard."""
    id: int
    nama_lengkap: str
    usia_kehamilan_minggu: Optional[int] = None
    usia_kehamilan_hari: Optional[int] = None
    tanggal_hpht: Optional[datetime] = None
    tanggal_taksiran_persalinan: Optional[datetime] = None
    risk_level: Optional[str] = None  # rendah, sedang, tinggi
    risk_level_set_at: Optional[datetime] = None
    golongan_darah: Optional[str] = None

    model_config = ConfigDict(from_attributes=True, json_schema_extra={
        "example": {
            "id": 1,
            "nama_lengkap": "Siti Aminah",
            "usia_kehamilan_minggu": 28,
            "usia_kehamilan_hari": 3,
            "tanggal_hpht": "2024-07-01T00:00:00Z",
            "tanggal_taksiran_persalinan": "2025-04-07T00:00:00Z",
            "risk_level": "rendah",
            "risk_level_set_at": "2025-01-15T10:00:00Z",
            "golongan_darah": "O"
        }
    })


class LatestHealthRecordSummary(BaseModel):
    """Summary health record terbaru untuk dashboard."""
    id: int
    checkup_date: datetime
    blood_pressure_systolic: int
    blood_pressure_diastolic: int
    heart_rate: int
    body_temperature: float
    weight: float
    complaints: str
    checked_by: str
    notes: Optional[str] = None

    model_config = ConfigDict(from_attributes=True, json_schema_extra={
        "example": {
            "id": 1,
            "checkup_date": "2025-01-20T00:00:00Z",
            "blood_pressure_systolic": 120,
            "blood_pressure_diastolic": 80,
            "heart_rate": 72,
            "body_temperature": 36.8,
            "weight": 65.5,
            "complaints": "Tidak ada keluhan",
            "checked_by": "perawat",
            "notes": "Kondisi ibu dan janin sehat"
        }
    })


class EmergencyContact(BaseModel):
    """Info kontak darurat (perawat/puskesmas)."""
    perawat_name: Optional[str] = None
    perawat_phone: Optional[str] = None
    puskesmas_name: Optional[str] = None
    puskesmas_phone: Optional[str] = None
    puskesmas_address: Optional[str] = None

    model_config = ConfigDict(json_schema_extra={
        "example": {
            "perawat_name": "Ns. Dewi Sartika",
            "perawat_phone": "+6281234567891",
            "puskesmas_name": "Puskesmas Sungai Penuh",
            "puskesmas_phone": "+62748123456",
            "puskesmas_address": "Jl. Kesehatan No. 1, Sungai Penuh"
        }
    })


class KerabatDashboardResponse(BaseModel):
    """Response untuk dashboard kerabat."""
    kerabat_id: int
    kerabat_name: str
    relation_type: Optional[str] = None
    ibu_hamil: IbuHamilSummary
    latest_health_record: Optional[LatestHealthRecordSummary] = None
    emergency_contact: EmergencyContact
    unread_notifications_count: int = 0
    risk_alert: Optional[str] = None  # Pesan alert jika risiko tinggi

    model_config = ConfigDict(json_schema_extra={
        "example": {
            "kerabat_id": 1,
            "kerabat_name": "Budi Santoso",
            "relation_type": "Suami",
            "ibu_hamil": {
                "id": 1,
                "nama_lengkap": "Siti Aminah",
                "usia_kehamilan_minggu": 28,
                "usia_kehamilan_hari": 3,
                "risk_level": "tinggi",
                "risk_level_set_at": "2025-01-15T10:00:00Z"
            },
            "latest_health_record": {
                "id": 1,
                "checkup_date": "2025-01-20T00:00:00Z",
                "blood_pressure_systolic": 140,
                "blood_pressure_diastolic": 95,
                "heart_rate": 88,
                "body_temperature": 37.2,
                "weight": 68.0,
                "complaints": "Pusing, kaki bengkak",
                "checked_by": "perawat"
            },
            "emergency_contact": {
                "perawat_name": "Ns. Dewi Sartika",
                "perawat_phone": "+6281234567891",
                "puskesmas_name": "Puskesmas Sungai Penuh"
            },
            "unread_notifications_count": 2,
            "risk_alert": "PERHATIAN: Ibu hamil memiliki status risiko TINGGI. Harap pantau kondisi dan segera hubungi perawat jika ada keluhan."
        }
    })


class KerabatHealthRecordListResponse(BaseModel):
    """Response untuk daftar health record yang bisa diakses kerabat."""
    ibu_hamil_id: int
    ibu_hamil_name: str
    records: list
    total: int
    page: int
    per_page: int

    model_config = ConfigDict(json_schema_extra={
        "example": {
            "ibu_hamil_id": 1,
            "ibu_hamil_name": "Siti Aminah",
            "records": [],
            "total": 10,
            "page": 1,
            "per_page": 10
        }
    })


class KerabatNotificationListResponse(BaseModel):
    """Response untuk daftar notifikasi kerabat."""
    notifications: list
    total: int
    unread_count: int

    model_config = ConfigDict(json_schema_extra={
        "example": {
            "notifications": [],
            "total": 5,
            "unread_count": 2
        }
    })


class MarkNotificationReadRequest(BaseModel):
    """Request untuk mark notification as read."""
    notification_ids: Optional[list] = None  # None = mark all as read

    model_config = ConfigDict(json_schema_extra={
        "example": {
            "notification_ids": [1, 2, 3]
        }
    })


class MarkNotificationReadResponse(BaseModel):
    """Response untuk mark notification as read."""
    marked_count: int
    message: str

    model_config = ConfigDict(json_schema_extra={
        "example": {
            "marked_count": 3,
            "message": "3 notifikasi berhasil ditandai sudah dibaca"
        }
    })


class KerabatProfileResponse(BaseModel):
    """Response untuk profile kerabat."""
    id: int
    user_id: int
    full_name: str
    phone: Optional[str] = None
    relation_type: Optional[str] = None
    ibu_hamil_id: int
    ibu_hamil_name: str
    can_view_records: bool
    can_receive_notifications: bool
    created_at: datetime

    model_config = ConfigDict(json_schema_extra={
        "example": {
            "id": 1,
            "user_id": 25,
            "full_name": "Budi Santoso",
            "phone": "+6281234567890",
            "relation_type": "Suami",
            "ibu_hamil_id": 1,
            "ibu_hamil_name": "Siti Aminah",
            "can_view_records": True,
            "can_receive_notifications": True,
            "created_at": "2025-01-01T10:00:00Z"
        }
    })
