"""Pydantic schemas for `Puskesmas` domain objects (registration flow)."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

REGISTRATION_STATUSES = {"draft", "pending_approval", "approved", "rejected"}
CREATE_ALLOWED_STATUSES = {"draft", "pending_approval"}


def _validate_phone(value: str) -> str:
    if not value:
        raise ValueError("Phone is required")
    digits = value.replace(" ", "").replace("-", "")
    if not digits.replace("+", "").isdigit() or len(digits) < 8:
        raise ValueError("Phone must be numeric and at least 8 digits")
    return value


def _validate_nip(value: str) -> str:
    if not value or len(value) < 5:
        raise ValueError("NIP is required and must be at least 5 characters")
    if len(value) > 18:
        raise ValueError("NIP must be at most 18 characters")
    return value


class PuskesmasBase(BaseModel):
    name: str = Field(..., min_length=3, max_length=255)
    address: str = Field(..., min_length=5)
    email: EmailStr
    phone: str
    kepala_name: str = Field(..., min_length=3, max_length=255)
    kepala_nip: str
    npwp: Optional[str] = None
    sk_document_url: Optional[str] = None  # Upload SK Pendirian (PDF) - opsional untuk draft
    npwp_document_url: Optional[str] = None  # Upload Scan NPWP (PDF/JPG/PNG)
    building_photo_url: Optional[str] = None  # Upload Foto Gedung (JPG/PNG) - opsional untuk draft
    latitude: Optional[float] = None  # Opsional untuk draft
    longitude: Optional[float] = None  # Opsional untuk draft
    data_truth_confirmed: bool = False

    @field_validator("phone")
    @classmethod
    def validate_phone(cls, v: str) -> str:
        return _validate_phone(v)

    @field_validator("kepala_nip")
    @classmethod
    def validate_nip(cls, v: str) -> str:
        return _validate_nip(v)

    model_config = ConfigDict(json_schema_extra={
        "example": {
            "name": "Puskesmas Sungai Penuh",
            "address": "Jl. Merdeka No. 1, Sungai Penuh, Jambi",
            "email": "admin@puskesmas.go.id",
            "phone": "+6281234567890",
            "kepala_name": "dr. Rina",
            "kepala_nip": "198012312010012001",
            "npwp": "12.345.678.9-012.345",
            "sk_document_url": "/uploads/documents/puskesmas/sk_pendirian/uuid.pdf",
            "npwp_document_url": "/uploads/documents/puskesmas/npwp/uuid.pdf",
            "building_photo_url": "/uploads/photos/puskesmas/uuid.jpg",
            "latitude": -2.0645,
            "longitude": 101.3912,
            "data_truth_confirmed": True,
        }
    })


class PuskesmasCreate(PuskesmasBase):
    password: str = Field(..., min_length=8, description="Password untuk akun admin puskesmas (minimal 8 karakter)")
    registration_status: str = Field(default="draft", description="draft or pending_approval")
    admin_user_id: Optional[int] = None  # injected after user creation

    @field_validator("password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("Password minimal 8 karakter")
        return v

    @field_validator("registration_status")
    @classmethod
    def validate_create_status(cls, v: str) -> str:
        if v not in CREATE_ALLOWED_STATUSES:
            raise ValueError(f"registration_status must be one of {sorted(CREATE_ALLOWED_STATUSES)}")
        return v

    model_config = ConfigDict(json_schema_extra={
        "example": {
            **PuskesmasBase.model_config.get("json_schema_extra", {}).get("example", {}),
            "password": "SecurePassword123!",
            "registration_status": "draft",
        }
    })


class PuskesmasSubmitForApproval(BaseModel):
    """Schema untuk submit draft ke pending_approval (Step 3)."""
    latitude: float = Field(..., description="Koordinat latitude dari map")
    longitude: float = Field(..., description="Koordinat longitude dari map")
    data_truth_confirmed: bool = Field(..., description="Konfirmasi kebenaran data")

    model_config = ConfigDict(json_schema_extra={
        "example": {
            "latitude": -2.0645,
            "longitude": 101.3912,
            "data_truth_confirmed": True,
        }
    })


class PuskesmasUpdate(BaseModel):
    name: Optional[str] = None
    address: Optional[str] = None
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    kepala_name: Optional[str] = None
    kepala_nip: Optional[str] = None
    npwp: Optional[str] = None
    sk_document_url: Optional[str] = None
    npwp_document_url: Optional[str] = None
    building_photo_url: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    data_truth_confirmed: Optional[bool] = None
    registration_status: Optional[str] = Field(
        default=None, description="draft or pending_approval during registration"
    )

    @field_validator("phone")
    @classmethod
    def validate_phone(cls, v: Optional[str]) -> Optional[str]:
        return _validate_phone(v) if v is not None else v

    @field_validator("kepala_nip")
    @classmethod
    def validate_nip(cls, v: Optional[str]) -> Optional[str]:
        return _validate_nip(v) if v is not None else v

    @field_validator("registration_status")
    @classmethod
    def validate_update_status(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        if v not in CREATE_ALLOWED_STATUSES:
            raise ValueError(f"registration_status must be one of {sorted(CREATE_ALLOWED_STATUSES)} during update")
        return v

    model_config = ConfigDict(json_schema_extra={
        "example": {
            "name": "Puskesmas Sungai Penuh",
            "registration_status": "pending_approval",
            "data_truth_confirmed": True,
        }
    })


class PuskesmasResponse(PuskesmasBase):
    id: int
    admin_user_id: Optional[int] = None
    registration_status: str
    registration_date: Optional[datetime] = None
    approved_by_admin_id: Optional[int] = None
    approved_at: Optional[datetime] = None
    rejection_reason: Optional[str] = None
    admin_notes: Optional[str] = None
    is_active: bool
    created_at: datetime
    updated_at: datetime

    @field_validator("registration_status")
    @classmethod
    def validate_status(cls, v: str) -> str:
        if v not in REGISTRATION_STATUSES:
            raise ValueError(f"Status must be one of {sorted(REGISTRATION_STATUSES)}")
        return v

    model_config = ConfigDict(from_attributes=True, json_schema_extra={
        "example": {
            **PuskesmasBase.model_config.get("json_schema_extra", {}).get("example", {}),
            "id": 1,
            "admin_user_id": 15,
            "registration_status": "pending_approval",
            "registration_date": "2025-01-01T10:00:00Z",
            "approved_by_admin_id": None,
            "approved_at": None,
            "rejection_reason": None,
            "admin_notes": None,
            "is_active": False,
            "created_at": "2025-01-01T10:00:00Z",
            "updated_at": "2025-01-02T11:00:00Z",
        }
    })


class PuskesmasAdminResponse(PuskesmasResponse):
    active_ibu_hamil_count: int = 0
    active_perawat_count: int = 0

    model_config = ConfigDict(from_attributes=True, json_schema_extra={
        "example": {
            **PuskesmasResponse.model_config.get("json_schema_extra", {}).get("example", {}),
            "active_ibu_hamil_count": 12,
            "active_perawat_count": 5,
        }
    })


class PuskesmasApproval(BaseModel):
    registration_status: str
    rejection_reason: Optional[str] = None
    approved_by_admin_id: Optional[int] = None
    approved_at: Optional[datetime] = None

    @field_validator("registration_status")
    @classmethod
    def validate_status(cls, v: str) -> str:
        if v not in {"approved", "rejected"}:
            raise ValueError("registration_status must be 'approved' or 'rejected'")
        return v

    model_config = ConfigDict(json_schema_extra={
        "example": {
            "registration_status": "approved",
            "approved_by_admin_id": 1,
            "approved_at": "2025-02-01T09:00:00Z",
            "rejection_reason": None,
        }
    })
