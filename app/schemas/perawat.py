"""Pydantic schemas for `Perawat` (Healthcare Worker) domain objects."""

from datetime import datetime
from typing import Optional
from enum import Enum

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

# ============================================
# ENUMS
# ============================================
class PerawatStatus(str, Enum):
    """Status workflow untuk perawat"""
    PENDING = "pending"      # Baru dibuat, belum login
    ACTIVE = "active"        # Sudah verified & aktif
    INACTIVE = "inactive"    # Tidak aktif sementara
    SUSPENDED = "suspended"  # Suspended oleh admin

# ============================================
# BASE SCHEMAS
# ============================================
class PerawatBase(BaseModel):
    """Base schema dengan field umum"""
    puskesmas_id: int = Field(..., gt=0)
    nip: str = Field(..., min_length=5, max_length=50)
    job_title: str = Field(..., min_length=3, max_length=100)
    license_number: Optional[str] = Field(None, max_length=100)
    license_document_url: Optional[str] = Field(None, max_length=500)
    max_patients: int = Field(default=15, ge=1, le=50)
    is_available: bool = Field(default=True)

    model_config = ConfigDict(json_schema_extra={
        "example": {
            "puskesmas_id": 1,
            "nip": "198501012015011001",
            "job_title": "Bidan",
            "license_number": "STR-1234567890",
            "license_document_url": "/files/str_bidan.pdf",
            "max_patients": 20,
            "is_available": True,
        }
    })

# ============================================
# CREATE SCHEMAS (FR-PK-002: Generate Akun)
# ============================================
class PerawatRegisterWithUser(BaseModel):
    """
    Schema untuk Puskesmas generate akun perawat BARU
    (creates both User + Perawat records atomically)
    FR-PK-002: Generate Akun Tenaga Kesehatan
    """
    # User data (akan create user baru)
    full_name: str = Field(..., min_length=3, max_length=255)
    phone: str = Field(..., pattern=r'^\+?[0-9]{10,15}$')
    email: EmailStr
    
    # Perawat data
    nik: str = Field(..., pattern=r'^\d{16}$')
    nip: str = Field(..., min_length=5, max_length=50)
    job_title: str = Field(..., min_length=3, max_length=100)
    license_number: Optional[str] = Field(None, max_length=100)
    max_patients: int = Field(default=15, ge=1, le=50)
    
    # Auto-assigned: puskesmas_id (dari current_user yang login)
    # Auto-assigned: created_by_user_id (dari current_user)
    
    @field_validator('nik')
    @classmethod
    def validate_nik(cls, v: str) -> str:
        if not v.isdigit():
            raise ValueError('NIK must contain only digits')
        if len(v) != 16:
            raise ValueError('NIK must be exactly 16 digits')
        return v
    
    @field_validator('phone')
    @classmethod
    def validate_phone(cls, v: str) -> str:
        cleaned = v.replace(' ', '').replace('-', '')
        if not cleaned.replace('+', '').isdigit():
            raise ValueError('Phone must contain only numbers')
        return cleaned
    
    
    model_config = ConfigDict(json_schema_extra={
        "example": {
            "full_name": "Siti Nurhaliza",
            "phone": "+6281234567890",
            "email": "siti.nurhaliza@example.com",
            "nik": "1234567890123456",
            "nip": "198501012015011001",
            "job_title": "Bidan",
            "license_number": "STR-1234567890",
            "max_patients": 15,
            
        }
    })

class PerawatCreate(PerawatBase):
    """
    Schema untuk create perawat (user_id sudah ada)
    Use case: jarang dipakai, mostly pakai PerawatRegisterWithUser
    """
    user_id: int = Field(..., gt=0)
    nik: str = Field(..., pattern=r'^\d{16}$')
    created_by_user_id: Optional[int] = None
    
    @field_validator('nik')
    @classmethod
    def validate_nik(cls, v: str) -> str:
        if not v.isdigit():
            raise ValueError('NIK must contain only digits')
        if len(v) != 16:
            raise ValueError('NIK must be exactly 16 digits')
        return v

    model_config = ConfigDict(json_schema_extra={
        "example": {
            "user_id": 15,
            "puskesmas_id": 1,
            "nik": "1234567890123456",
            "nip": "198501012015011001",
            "job_title": "Bidan",
            "license_number": "STR-1234567890",
            "max_patients": 20,
            "is_available": True,
            "created_by_user_id": 10,
        }
    })

# ============================================
# UPDATE SCHEMAS (FR-TK-002)
# ============================================
class PerawatUpdate(BaseModel):
    """Update perawat profile (FR-TK-002: Profile Management)"""
    phone: Optional[str] = Field(None, pattern=r'^\+?[0-9]{10,15}$')
    email: Optional[EmailStr] = None
    nip: Optional[str] = Field(None, min_length=5, max_length=50)
    job_title: Optional[str] = Field(None, min_length=3, max_length=100)
    license_number: Optional[str] = Field(None, max_length=100)
    license_document_url: Optional[str] = Field(None, max_length=500)
    max_patients: Optional[int] = Field(None, ge=1, le=50)
    is_available: Optional[bool] = None
    
    @field_validator('phone')
    @classmethod
    def validate_phone(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        cleaned = v.replace(' ', '').replace('-', '')
        if not cleaned.replace('+', '').isdigit():
            raise ValueError('Phone must contain only numbers')
        return cleaned

    model_config = ConfigDict(json_schema_extra={
        "example": {
            "phone": "+6281234567890",
            "email": "newemail@example.com",
            
            "is_available": False,
        }
    })

# ============================================
# RESPONSE SCHEMAS
# ============================================
class PerawatResponse(BaseModel):
    """
    Complete perawat response (joined with users table)
    Includes user info for display
    """
    # Perawat table fields
    id: int
    user_id: int
    puskesmas_id: int
    created_by_user_id: Optional[int] = None
    
    # Identity & Professional
    nik: Optional[str] = None
    nip: str
    job_title: str
    license_number: Optional[str] = None
    license_document_url: Optional[str] = None
    
    # Workload
    max_patients: int
    current_patients: int
    
    # Location removed; puskesmas location is used for service area
    
    # Status
    status: Optional[PerawatStatus] = PerawatStatus.ACTIVE  # Default to active
    is_available: bool
    is_active: bool
    is_verified: bool = False
    
    # User info (joined from users table)
    full_name: str
    phone: str
    email: Optional[str] = None
    
    # Timestamps
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "id": 1,
                "user_id": 15,
                "puskesmas_id": 1,
                "created_by_user_id": 10,
                "nik": "1234567890123456",
                "nip": "198501012015011001",
                "job_title": "Bidan",
                "license_number": "STR-1234567890",
                "license_document_url": "/files/str_bidan.pdf",
                "max_patients": 20,
                "current_patients": 5,
                "status": "active",
                "is_available": True,
                "is_active": True,
                "is_verified": True,
                "full_name": "Siti Nurhaliza",
                "phone": "+6281234567890",
                "email": "siti@example.com",
                "created_at": "2025-01-01T10:00:00Z",
                "updated_at": "2025-01-02T11:00:00Z",
            }
        }
    )

class PerawatListResponse(BaseModel):
    """Simplified response for list endpoints (performance)"""
    id: int
    full_name: str
    job_title: str
    current_patients: int
    max_patients: int
    capacity_percentage: float
    is_available: bool
    status: Optional[PerawatStatus] = PerawatStatus.ACTIVE
    puskesmas_name: Optional[str] = None
    
    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "id": 1,
                "full_name": "Siti Nurhaliza",
                "job_title": "Bidan",
                "current_patients": 5,
                "max_patients": 20,
                "capacity_percentage": 25.0,
                "is_available": True,
                "status": "active",
                "puskesmas_name": "Puskesmas Hamparan Pugu"
            }
        }
    )

# ============================================
# WORKLOAD SCHEMAS (FR-PK-003)
# ============================================
class PerawatWorkloadResponse(BaseModel):
    """Workload info untuk assignment logic (FR-PK-003)"""
    perawat_id: int
    full_name: str
    job_title: str
    current_patients: int
    max_patients: int
    capacity_percentage: float
    is_available: bool
    is_at_capacity: bool
    # work_area removed
    
    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "perawat_id": 1,
                "full_name": "Siti Nurhaliza",
                "job_title": "Bidan",
                "current_patients": 18,
                "max_patients": 20,
                "capacity_percentage": 90.0,
                "is_available": True,
                "is_at_capacity": False
            }
        }
    )

# ============================================
# TRANSFER REQUEST SCHEMAS (FR-TK-002)
# ============================================
class PerawatTransferRequest(BaseModel):
    """Create transfer request (FR-TK-002: Request transfer)"""
    to_puskesmas_id: int = Field(..., gt=0)
    reason: str = Field(..., min_length=20, max_length=500)
    
    model_config = ConfigDict(json_schema_extra={
        "example": {
            "to_puskesmas_id": 3,
            "reason": "Saya ingin pindah ke Puskesmas yang lebih dekat dengan tempat tinggal saya di Kecamatan Baru untuk memudahkan mobilitas dan meningkatkan pelayanan."
        }
    })

class TransferRequestResponse(BaseModel):
    """Transfer request detail"""
    id: int
    requester_user_id: int
    requester_type: str
    perawat_id: int
    from_puskesmas_id: Optional[int] = None
    to_puskesmas_id: Optional[int] = None
    reason: str
    status: str
    reviewed_by_user_id: Optional[int] = None
    reviewed_at: Optional[datetime] = None
    rejection_reason: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    
    # Joined data for display
    from_puskesmas_name: Optional[str] = None
    to_puskesmas_name: Optional[str] = None
    
    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "id": 1,
                "requester_user_id": 15,
                "requester_type": "perawat",
                "perawat_id": 1,
                "from_puskesmas_id": 1,
                "to_puskesmas_id": 3,
                "reason": "Pindah domisili ke Kecamatan Baru",
                "status": "pending",
                "reviewed_by_user_id": None,
                "reviewed_at": None,
                "rejection_reason": None,
                "created_at": "2025-01-15T10:00:00Z",
                "updated_at": "2025-01-15T10:00:00Z",
                "from_puskesmas_name": "Puskesmas Hamparan Pugu",
                "to_puskesmas_name": "Puskesmas Baru"
            }
        }
    )