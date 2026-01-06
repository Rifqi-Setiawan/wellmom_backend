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
        }
    })

# ============================================
# CREATE SCHEMAS
# ============================================
class PerawatCreate(PerawatBase):
    """Schema untuk membuat perawat baru"""
    pass

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