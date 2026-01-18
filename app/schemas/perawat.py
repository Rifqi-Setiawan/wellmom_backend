"""Pydantic schemas for `Perawat` (Healthcare Worker) domain objects."""

from datetime import datetime
from typing import Optional
from enum import Enum

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

# ============================================
# ENUMS
# ============================================
class PerawatStatus(str, Enum):
    """Status akun untuk perawat"""
    ACTIVE = "active"        # Akun aktif
    INACTIVE = "inactive"    # Akun tidak aktif

# ============================================
# BASE SCHEMAS
# ============================================
class PerawatBase(BaseModel):
    """Base schema dengan field umum"""
    puskesmas_id: int = Field(..., gt=0)
    nama_lengkap: str = Field(..., min_length=3, max_length=255)
    email: EmailStr
    nomor_hp: str = Field(..., pattern=r'^\+?[0-9]{10,15}$')
    nip: str = Field(..., min_length=5, max_length=50)
    is_active: bool = Field(default=True)
    profile_photo_url: Optional[str] = Field(None, max_length=500)

    @field_validator('nomor_hp')
    @classmethod
    def validate_phone(cls, v: str) -> str:
        cleaned = v.replace(' ', '').replace('-', '')
        if not cleaned.replace('+', '').isdigit():
            raise ValueError('Phone must contain only numbers')
        return cleaned

    model_config = ConfigDict(json_schema_extra={
        "example": {
            "puskesmas_id": 1,
            "nama_lengkap": "Siti Nurhaliza",
            "email": "siti.nurhaliza@example.com",
            "nomor_hp": "+6281234567890",
            "nip": "198501012015011001",
            "is_active": True,
            "profile_photo_url": "/uploads/photos/profiles/perawat/perawat_1_20250118_123456.jpg",
        }
    })

# ============================================
# CREATE SCHEMAS
# ============================================
class PerawatCreate(PerawatBase):
    """Schema untuk membuat perawat baru"""
    pass

class PerawatRegisterWithUser(BaseModel):
    """Schema untuk registrasi perawat dengan user oleh Puskesmas (legacy, deprecated)"""
    # User fields
    phone: str = Field(..., pattern=r'^\+?[0-9]{10,15}$')
    email: EmailStr
    full_name: str = Field(..., min_length=3, max_length=255)
    
    # Perawat fields
    nip: Optional[str] = Field(None, min_length=5, max_length=50)
    nik: Optional[str] = Field(None, min_length=16, max_length=16)
    job_title: Optional[str] = Field(None, max_length=100)
    license_number: Optional[str] = Field(None, max_length=50)
    max_patients: Optional[int] = Field(10, ge=1, le=50)
    
    @field_validator('phone')
    @classmethod
    def validate_phone(cls, v: str) -> str:
        cleaned = v.replace(' ', '').replace('-', '')
        if not cleaned.replace('+', '').isdigit():
            raise ValueError('Phone must contain only numbers')
        return cleaned
    
    model_config = ConfigDict(json_schema_extra={
        "example": {
            "phone": "+6281234567890",
            "email": "siti@example.com",
            "full_name": "Siti Nurhaliza",
            "nik": "3175091201850001",
            "job_title": "Bidan",
            "license_number": "BID-123456",
            "max_patients": 15
        }
    })


class PerawatGenerate(BaseModel):
    """Schema untuk generate akun perawat oleh Puskesmas (simplified).
    
    Puskesmas hanya perlu memasukkan email dan NIP.
    Password otomatis menggunakan NIP.
    Perawat dapat mengubah password setelah aktivasi.
    """
    email: EmailStr = Field(..., description="Email perawat untuk login dan aktivasi")
    nip: str = Field(..., min_length=5, max_length=50, description="NIP perawat (juga digunakan sebagai password awal)")
    
    model_config = ConfigDict(json_schema_extra={
        "example": {
            "email": "siti.nurhaliza@puskesmas.go.id",
            "nip": "198501012015011001"
        }
    })


class PerawatLoginRequest(BaseModel):
    """Schema untuk login perawat dengan email dan password."""
    email: EmailStr = Field(..., description="Email perawat")
    password: str = Field(..., min_length=1, description="Password perawat")
    
    model_config = ConfigDict(json_schema_extra={
        "example": {
            "email": "siti.nurhaliza@puskesmas.go.id",
            "password": "198501012015011001"
        }
    })


class PerawatLoginResponse(BaseModel):
    """Response untuk login perawat."""
    access_token: str
    token_type: str = "bearer"
    role: str = "perawat"
    user: "PerawatLoginUserInfo"
    perawat: "PerawatLoginPerawatInfo"
    
    model_config = ConfigDict(json_schema_extra={
        "example": {
            "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
            "token_type": "bearer",
            "role": "perawat",
            "user": {
                "id": 10,
                "email": "siti.nurhaliza@puskesmas.go.id",
                "full_name": "Siti Nurhaliza"
            },
            "perawat": {
                "id": 1,
                "nip": "198501012015011001",
                "puskesmas_id": 1,
                "puskesmas_name": "Puskesmas Hamparan Pugu",
                "is_active": True
            }
        }
    })


class PerawatLoginUserInfo(BaseModel):
    """Info user untuk response login perawat."""
    id: int
    email: Optional[str] = None
    full_name: str


class PerawatLoginPerawatInfo(BaseModel):
    """Info perawat untuk response login."""
    id: int
    nip: str
    puskesmas_id: int
    puskesmas_name: Optional[str] = None
    is_active: bool


class PerawatResetPasswordRequest(BaseModel):
    """Schema untuk reset password perawat."""
    current_password: str = Field(..., min_length=1, description="Password saat ini")
    new_password: str = Field(..., min_length=6, description="Password baru (minimal 6 karakter)")
    
    model_config = ConfigDict(json_schema_extra={
        "example": {
            "current_password": "198501012015011001",
            "new_password": "NewSecurePassword123!"
        }
    })

# ============================================
# UPDATE SCHEMAS
# ============================================
class PerawatUpdate(BaseModel):
    """Schema untuk update data perawat"""
    nama_lengkap: Optional[str] = Field(None, min_length=3, max_length=255)
    email: Optional[EmailStr] = None
    nomor_hp: Optional[str] = Field(None, pattern=r'^\+?[0-9]{10,15}$')
    nip: Optional[str] = Field(None, min_length=5, max_length=50)
    is_active: Optional[bool] = None
    profile_photo_url: Optional[str] = Field(None, max_length=500)
    
    @field_validator('nomor_hp')
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
            "nama_lengkap": "Siti Nurhaliza Binti Ahmad",
            "nomor_hp": "+6281234567890",
            "email": "newemail@example.com",
            "is_active": True,
        }
    })

# ============================================
# RESPONSE SCHEMAS
# ============================================
class PerawatResponse(BaseModel):
    """Response schema untuk perawat"""
    id: int
    puskesmas_id: int
    nama_lengkap: str
    email: str
    nomor_hp: str
    nip: str
    is_active: bool
    profile_photo_url: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    
    # Untuk menampilkan jumlah ibu hamil yang di-assign
    jumlah_ibu_hamil: Optional[int] = 0

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "id": 1,
                "puskesmas_id": 1,
                "nama_lengkap": "Siti Nurhaliza",
                "email": "siti@example.com",
                "nomor_hp": "+6281234567890",
                "nip": "198501012015011001",
                "is_active": True,
                "profile_photo_url": "/uploads/photos/profiles/perawat/perawat_1_20250118_123456.jpg",
                "jumlah_ibu_hamil": 5,
                "created_at": "2025-01-01T10:00:00Z",
                "updated_at": "2025-01-02T11:00:00Z",
            }
        }
    )

class PerawatListResponse(BaseModel):
    """Simplified response for list endpoints"""
    id: int
    nama_lengkap: str
    email: str
    nomor_hp: str
    nip: str
    is_active: bool
    jumlah_ibu_hamil: Optional[int] = 0
    puskesmas_nama: Optional[str] = None
    
    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "id": 1,
                "nama_lengkap": "Siti Nurhaliza",
                "email": "siti@example.com",
                "nomor_hp": "+6281234567890",
                "nip": "198501012015011001",
                "is_active": True,
                "jumlah_ibu_hamil": 5,
                "puskesmas_nama": "Puskesmas Hamparan Pugu"
            }
        }
    )

# ============================================
# ASSIGNMENT RESPONSE SCHEMA
# ============================================
class PerawatAssignmentInfo(BaseModel):
    """Info perawat untuk assignment (simplified)"""
    perawat_id: int
    nama_lengkap: str
    email: str
    nomor_hp: str
    nip: str
    jumlah_ibu_hamil: int
    is_active: bool
    
    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "perawat_id": 1,
                "nama_lengkap": "Siti Nurhaliza",
                "email": "siti@example.com",
                "nomor_hp": "+6281234567890",
                "nip": "198501012015011001",
                "jumlah_ibu_hamil": 5,
                "is_active": True
            }
        }
    )