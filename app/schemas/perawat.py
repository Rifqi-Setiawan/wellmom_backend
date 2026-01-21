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
    nomor_hp: str = Field(..., min_length=10, max_length=20)
    nip: str = Field(..., min_length=5, max_length=50)
    is_active: bool = Field(default=True)
    profile_photo_url: Optional[str] = Field(None, max_length=500)

    @field_validator('nomor_hp')
    @classmethod
    def validate_phone(cls, v: str) -> str:
        cleaned = v.replace(' ', '').replace('-', '')
        if not cleaned.replace('+', '').isdigit():
            raise ValueError('Nomor HP hanya boleh berisi angka')
        if len(cleaned) < 10 or len(cleaned) > 15:
            raise ValueError('Nomor HP harus 10-15 digit')
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

class PerawatGenerate(BaseModel):
    """Schema untuk membuat akun perawat oleh Puskesmas.

    Puskesmas memasukkan data lengkap perawat.
    Password otomatis menggunakan NIP.
    Akun langsung aktif tanpa proses aktivasi email.
    """
    nama_lengkap: str = Field(..., min_length=3, max_length=255, description="Nama lengkap perawat")
    nomor_hp: str = Field(..., min_length=10, max_length=20, description="Nomor HP perawat (format: 08xx atau +628xx)")
    nip: str = Field(..., min_length=5, max_length=50, description="NIP perawat (juga digunakan sebagai password awal)")
    email: EmailStr = Field(..., description="Email aktif perawat untuk login")

    @field_validator('nomor_hp')
    @classmethod
    def validate_phone(cls, v: str) -> str:
        # Bersihkan spasi dan dash terlebih dahulu
        cleaned = v.replace(' ', '').replace('-', '')
        # Validasi hanya angka (dan optional + di depan)
        if not cleaned.replace('+', '').isdigit():
            raise ValueError('Nomor HP hanya boleh berisi angka')
        # Validasi panjang setelah dibersihkan
        if len(cleaned) < 10 or len(cleaned) > 15:
            raise ValueError('Nomor HP harus 10-15 digit')
        return cleaned

    model_config = ConfigDict(json_schema_extra={
        "example": {
            "nama_lengkap": "Siti Nurhaliza",
            "nomor_hp": "+6281234567890",
            "nip": "198501012015011001",
            "email": "siti.nurhaliza@puskesmas.go.id"
        }
    })


class PerawatGenerateResponse(BaseModel):
    """Response schema untuk pembuatan akun perawat baru."""
    user_id: int = Field(..., description="ID user yang dibuat")
    perawat_id: int = Field(..., description="ID perawat yang dibuat")
    nama_lengkap: str = Field(..., description="Nama lengkap perawat")
    email: str = Field(..., description="Email perawat untuk login")
    nomor_hp: str = Field(..., description="Nomor HP perawat")
    nip: str = Field(..., description="NIP perawat (juga sebagai password awal)")
    puskesmas_id: int = Field(..., description="ID puskesmas tempat perawat terdaftar")
    puskesmas_name: str = Field(..., description="Nama puskesmas")
    is_active: bool = Field(..., description="Status aktif akun")
    login_url: str = Field(..., description="URL untuk login perawat")
    message: str = Field(..., description="Pesan sukses")

    model_config = ConfigDict(json_schema_extra={
        "example": {
            "user_id": 10,
            "perawat_id": 5,
            "nama_lengkap": "Siti Nurhaliza",
            "email": "siti.nurhaliza@puskesmas.go.id",
            "nomor_hp": "+6281234567890",
            "nip": "198501012015011001",
            "puskesmas_id": 1,
            "puskesmas_name": "Puskesmas Hamparan Pugu",
            "is_active": True,
            "login_url": "https://wellmom.example.com/perawat/login",
            "message": "Akun perawat berhasil dibuat dan langsung aktif. Password awal adalah NIP. Perawat dapat langsung login."
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
    nomor_hp: Optional[str] = Field(None, min_length=10, max_length=20)
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
            raise ValueError('Nomor HP hanya boleh berisi angka')
        if len(cleaned) < 10 or len(cleaned) > 15:
            raise ValueError('Nomor HP harus 10-15 digit')
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


# ============================================
# TRANSFER PATIENT SCHEMAS
# ============================================
class TransferAllPatientsRequest(BaseModel):
    """Schema untuk memindahkan semua pasien dari satu perawat ke perawat lain.

    Digunakan saat perawat resign atau tidak aktif lagi.
    """
    target_perawat_id: int = Field(..., gt=0, description="ID perawat tujuan yang akan menerima semua pasien")

    model_config = ConfigDict(json_schema_extra={
        "example": {
            "target_perawat_id": 5
        }
    })


class TransferSinglePatientRequest(BaseModel):
    """Schema untuk memindahkan satu pasien dari perawat ke perawat lain."""
    ibu_hamil_id: int = Field(..., gt=0, description="ID ibu hamil yang akan dipindahkan")
    target_perawat_id: int = Field(..., gt=0, description="ID perawat tujuan")

    model_config = ConfigDict(json_schema_extra={
        "example": {
            "ibu_hamil_id": 10,
            "target_perawat_id": 5
        }
    })


class TransferPatientResponse(BaseModel):
    """Response untuk transfer pasien."""
    success: bool
    message: str
    transferred_count: int = Field(..., description="Jumlah pasien yang berhasil dipindahkan")
    source_perawat: Optional["TransferPerawatInfo"] = None
    target_perawat: Optional["TransferPerawatInfo"] = None
    transferred_patients: Optional[list] = Field(default=None, description="Daftar ID pasien yang dipindahkan")

    model_config = ConfigDict(json_schema_extra={
        "example": {
            "success": True,
            "message": "Berhasil memindahkan 5 pasien",
            "transferred_count": 5,
            "source_perawat": {
                "id": 1,
                "nama_lengkap": "Perawat Lama",
                "current_patients": 0
            },
            "target_perawat": {
                "id": 5,
                "nama_lengkap": "Perawat Baru",
                "current_patients": 5
            },
            "transferred_patients": [10, 11, 12, 13, 14]
        }
    })


class TransferPerawatInfo(BaseModel):
    """Info perawat untuk response transfer."""
    id: int
    nama_lengkap: str
    current_patients: int

    model_config = ConfigDict(from_attributes=True)


# ============================================
# MY NURSES LIST SCHEMAS (for Puskesmas Admin)
# ============================================
class MyNurseItem(BaseModel):
    """Item detail perawat untuk daftar perawat puskesmas."""
    id: int
    user_id: Optional[int] = None
    nama_lengkap: str
    email: str
    nomor_hp: str
    nip: str
    profile_photo_url: Optional[str] = None
    is_active: bool
    current_patients: int = 0
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

    model_config = ConfigDict(json_schema_extra={
        "example": {
            "id": 1,
            "user_id": 10,
            "nama_lengkap": "Siti Nurhaliza",
            "email": "siti.nurhaliza@puskesmas.go.id",
            "nomor_hp": "+6281234567890",
            "nip": "198501012015011001",
            "profile_photo_url": "/uploads/photos/profiles/perawat/perawat_1.jpg",
            "is_active": True,
            "current_patients": 5,
            "created_at": "2025-01-01T10:00:00",
            "updated_at": "2025-01-02T11:00:00"
        }
    })


class MyNursesResponse(BaseModel):
    """Response untuk endpoint list perawat milik puskesmas."""
    puskesmas_id: int
    puskesmas_name: str
    total_perawat: int
    perawat_aktif: int
    perawat_list: list[MyNurseItem]

    model_config = ConfigDict(json_schema_extra={
        "example": {
            "puskesmas_id": 1,
            "puskesmas_name": "Puskesmas Hamparan Pugu",
            "total_perawat": 3,
            "perawat_aktif": 2,
            "perawat_list": [
                {
                    "id": 1,
                    "user_id": 10,
                    "nama_lengkap": "Siti Nurhaliza",
                    "email": "siti.nurhaliza@puskesmas.go.id",
                    "nomor_hp": "+6281234567890",
                    "nip": "198501012015011001",
                    "profile_photo_url": None,
                    "is_active": True,
                    "current_patients": 5,
                    "created_at": "2025-01-01T10:00:00",
                    "updated_at": "2025-01-02T11:00:00"
                },
                {
                    "id": 2,
                    "user_id": 11,
                    "nama_lengkap": "Dewi Lestari",
                    "email": "dewi.lestari@puskesmas.go.id",
                    "nomor_hp": "+6282345678901",
                    "nip": "199001012020012001",
                    "profile_photo_url": None,
                    "is_active": True,
                    "current_patients": 3,
                    "created_at": "2025-01-05T09:00:00",
                    "updated_at": "2025-01-06T10:00:00"
                }
            ]
        }
    })


# ============================================
# RISK LEVEL SCHEMAS
# ============================================
RISK_LEVELS = {"rendah", "sedang", "tinggi"}


class SetRiskLevelRequest(BaseModel):
    """Schema untuk menentukan tingkat risiko kehamilan oleh perawat.

    Tingkat risiko:
    - rendah: Kehamilan dengan risiko rendah
    - sedang: Kehamilan dengan risiko sedang
    - tinggi: Kehamilan dengan risiko tinggi
    """
    risk_level: str = Field(..., description="Tingkat risiko kehamilan: rendah, sedang, atau tinggi")

    @field_validator('risk_level')
    @classmethod
    def validate_risk_level(cls, v: str) -> str:
        v_lower = v.lower().strip()
        if v_lower not in RISK_LEVELS:
            raise ValueError(f"Tingkat risiko harus salah satu dari: {', '.join(sorted(RISK_LEVELS))}")
        return v_lower

    model_config = ConfigDict(json_schema_extra={
        "example": {
            "risk_level": "sedang"
        }
    })


class SetRiskLevelResponse(BaseModel):
    """Response untuk endpoint set risk level."""
    success: bool
    message: str
    ibu_hamil_id: int
    ibu_hamil_nama: str
    risk_level: str
    risk_level_set_by: int = Field(..., description="ID perawat yang menentukan")
    risk_level_set_by_nama: str = Field(..., description="Nama perawat yang menentukan")
    risk_level_set_at: datetime = Field(..., description="Waktu penentuan risiko")

    model_config = ConfigDict(json_schema_extra={
        "example": {
            "success": True,
            "message": "Tingkat risiko kehamilan berhasil ditentukan",
            "ibu_hamil_id": 10,
            "ibu_hamil_nama": "Siti Aminah",
            "risk_level": "sedang",
            "risk_level_set_by": 1,
            "risk_level_set_by_nama": "Siti Nurhaliza",
            "risk_level_set_at": "2026-01-21T10:30:00"
        }
    })