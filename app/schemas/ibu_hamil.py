"""Pydantic schemas for `IbuHamil` (Pregnant Woman) domain objects."""

from datetime import date, datetime
from typing import Any, Optional, Tuple

from pydantic import BaseModel, ConfigDict, EmailStr, field_serializer, field_validator
from geoalchemy2.elements import WKBElement
from shapely import wkb


RISK_LEVELS = {"low", "normal", "high"}
ASSIGNMENT_METHODS = {"auto", "manual"}


# ============================================================================
# LOGIN SCHEMAS
# ============================================================================

class IbuHamilLoginRequest(BaseModel):
    """Schema untuk login ibu hamil dengan email dan password."""

    email: EmailStr
    password: str

    @field_validator("password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        if len(v) < 6:
            raise ValueError("Password minimal 6 karakter")
        return v

    model_config = ConfigDict(json_schema_extra={
        "example": {
            "email": "siti.aminah@example.com",
            "password": "SecurePassword123!"
        }
    })


class IbuHamilLoginResponse(BaseModel):
    """Schema untuk response login ibu hamil."""

    access_token: str
    token_type: str = "bearer"
    user_id: int
    ibu_hamil_id: int
    nama_lengkap: str
    email: str

    model_config = ConfigDict(json_schema_extra={
        "example": {
            "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
            "token_type": "bearer",
            "user_id": 1,
            "ibu_hamil_id": 1,
            "nama_lengkap": "Siti Aminah",
            "email": "siti.aminah@example.com"
        }
    })


def _validate_nik(value: str) -> str:
    import re
    if not re.match(r"^[0-9]{16}$", value):
        raise ValueError("NIK must be exactly 16 digits")
    return value


def _validate_location(value: Tuple[float, float]) -> Tuple[float, float]:
    if value is None:
        raise ValueError("Location is required")
    if not isinstance(value, tuple) or len(value) != 2:
        raise ValueError("Location must be a (longitude, latitude) tuple")
    lon, lat = value
    if not (-180.0 <= lon <= 180.0 and -90.0 <= lat <= 90.0):
        raise ValueError("Longitude must be between -180 and 180, latitude between -90 and 90")
    return lon, lat


class RiwayatKesehatanIbu(BaseModel):
    """Riwayat kesehatan ibu hamil"""
    darah_tinggi: bool = False
    diabetes: bool = False
    anemia: bool = False
    penyakit_jantung: bool = False
    asma: bool = False
    penyakit_ginjal: bool = False
    tbc_malaria: bool = False

    model_config = ConfigDict(json_schema_extra={
        "example": {
            "darah_tinggi": False,
            "diabetes": False,
            "anemia": False,
            "penyakit_jantung": False,
            "asma": False,
            "penyakit_ginjal": False,
            "tbc_malaria": False,
        }
    })


class IbuHamilBase(BaseModel):
    """Base schema for IbuHamil - common fields for input/output
    
    NOTE: user_id is NOT here because it's set programmatically, not user input
    """
    # Identitas Pribadi
    nama_lengkap: str
    nik: str
    date_of_birth: date
    profile_photo_url: Optional[str] = None  # Foto profil ibu hamil
    
    # Alamat & Lokasi
    address: str
    location: Tuple[float, float]  # (longitude, latitude)
    provinsi: Optional[str] = None
    kota_kabupaten: Optional[str] = None
    kelurahan: Optional[str] = None
    kecamatan: Optional[str] = None
    
    # Data Kehamilan
    last_menstrual_period: Optional[date] = None  # HPHT
    estimated_due_date: Optional[date] = None  # HPL
    usia_kehamilan: Optional[int] = None  # Usia kehamilan dalam minggu
    kehamilan_ke: Optional[int] = 1  # Kehamilan ke berapa
    jumlah_anak: Optional[int] = 0  # Jumlah anak yang sudah dilahirkan
    jarak_kehamilan_terakhir: Optional[str] = None  # Jarak kehamilan terakhir
    miscarriage_number: Optional[int] = 0  # Riwayat keguguran
    previous_pregnancy_complications: Optional[str] = None  # Komplikasi kehamilan sebelumnya
    pernah_caesar: bool = False  # Pernah Caesar
    pernah_perdarahan_saat_hamil: bool = False  # Pernah perdarahan saat hamil
    
    # Riwayat Kesehatan Ibu
    riwayat_kesehatan_ibu: RiwayatKesehatanIbu = RiwayatKesehatanIbu()
    
    # Kontak Darurat
    emergency_contact_name: str
    emergency_contact_phone: str
    emergency_contact_relation: Optional[str] = None
    
    # Optional fields
    age: Optional[int] = None
    blood_type: Optional[str] = None
    risk_level: Optional[str] = "normal"
    healthcare_preference: Optional[str] = None
    whatsapp_consent: Optional[bool] = True
    data_sharing_consent: Optional[bool] = False

    @field_validator("nik")
    @classmethod
    def validate_nik(cls, v: str) -> str:
        return _validate_nik(v)

    @field_validator("location")
    @classmethod
    def validate_location(cls, v: Tuple[float, float]) -> Tuple[float, float]:
        return _validate_location(v)

    @field_validator("risk_level")
    @classmethod
    def validate_risk_level(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and v not in RISK_LEVELS:
            raise ValueError(f"Risk level must be one of {sorted(RISK_LEVELS)}")
        return v

    model_config = ConfigDict(json_schema_extra={
        "example": {
            "nama_lengkap": "Siti Aminah",
            "nik": "3175091201850001",
            "date_of_birth": "1985-12-12",
            "age": 39,
            "blood_type": "O+",
            "address": "Jl. Mawar No. 10, RT 02 RW 05",
            "provinsi": "Jambi",
            "kota_kabupaten": "Kerinci",
            "kelurahan": "Sungai Penuh",
            "kecamatan": "Pesisir Bukit",
            "location": (101.3912, -2.0645),
            "last_menstrual_period": "2024-12-01",
            "estimated_due_date": "2025-09-08",
            "usia_kehamilan": 8,
            "kehamilan_ke": 2,
            "jumlah_anak": 1,
            "jarak_kehamilan_terakhir": "2 tahun",
            "miscarriage_number": 0,
            "previous_pregnancy_complications": "Tidak ada",
            "pernah_caesar": False,
            "pernah_perdarahan_saat_hamil": False,
            "riwayat_kesehatan_ibu": {
                "darah_tinggi": False,
                "diabetes": False,
                "anemia": False,
                "penyakit_jantung": False,
                "asma": False,
                "penyakit_ginjal": False,
                "tbc_malaria": False,
            },
            "emergency_contact_name": "Budi (Suami)",
            "emergency_contact_phone": "+6281234567890",
            "emergency_contact_relation": "Suami",
            "risk_level": "normal",
            "healthcare_preference": "puskesmas",
            "whatsapp_consent": True,
            "data_sharing_consent": False,
        }
    })


class IbuHamilCreate(IbuHamilBase):
    """Schema for creating new IbuHamil
    
    NOTE: user_id is passed separately to CRUD method, not in schema!
    """
    pass  # Inherits all from Base, no additional fields needed for creation


class IbuHamilUpdate(BaseModel):
    """Schema for updating IbuHamil - all fields optional"""
    puskesmas_id: Optional[int] = None
    perawat_id: Optional[int] = None
    assigned_by_user_id: Optional[int] = None
    nama_lengkap: Optional[str] = None
    nik: Optional[str] = None
    date_of_birth: Optional[date] = None
    age: Optional[int] = None
    blood_type: Optional[str] = None
    profile_photo_url: Optional[str] = None
    last_menstrual_period: Optional[date] = None
    estimated_due_date: Optional[date] = None
    usia_kehamilan: Optional[int] = None
    kehamilan_ke: Optional[int] = None
    jumlah_anak: Optional[int] = None
    jarak_kehamilan_terakhir: Optional[str] = None
    miscarriage_number: Optional[int] = None
    previous_pregnancy_complications: Optional[str] = None
    pernah_caesar: Optional[bool] = None
    pernah_perdarahan_saat_hamil: Optional[bool] = None
    riwayat_kesehatan_ibu: Optional[RiwayatKesehatanIbu] = None
    address: Optional[str] = None
    provinsi: Optional[str] = None
    kota_kabupaten: Optional[str] = None
    kelurahan: Optional[str] = None
    kecamatan: Optional[str] = None
    location: Optional[Tuple[float, float]] = None
    emergency_contact_name: Optional[str] = None
    emergency_contact_phone: Optional[str] = None
    emergency_contact_relation: Optional[str] = None
    risk_level: Optional[str] = None
    healthcare_preference: Optional[str] = None
    whatsapp_consent: Optional[bool] = None
    data_sharing_consent: Optional[bool] = None
    is_active: Optional[bool] = None
    assignment_date: Optional[datetime] = None
    assignment_distance_km: Optional[float] = None
    assignment_method: Optional[str] = None

    @field_validator("nik")
    @classmethod
    def validate_nik(cls, v: Optional[str]) -> Optional[str]:
        return _validate_nik(v) if v is not None else v

    @field_validator("location")
    @classmethod
    def validate_location(cls, v: Optional[Tuple[float, float]]) -> Optional[Tuple[float, float]]:
        if v is None:
            return v
        return _validate_location(v)

    @field_validator("risk_level")
    @classmethod
    def validate_risk_level(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and v not in RISK_LEVELS:
            raise ValueError(f"Risk level must be one of {sorted(RISK_LEVELS)}")
        return v

    @field_validator("assignment_method")
    @classmethod
    def validate_assignment_method(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and v not in ASSIGNMENT_METHODS:
            raise ValueError(f"Assignment method must be one of {sorted(ASSIGNMENT_METHODS)}")
        return v

    model_config = ConfigDict(json_schema_extra={
        "example": {
            "perawat_id": 2,
            "location": (101.4, -2.1),
            "risk_level": "high",
        }
    })


class IbuHamilResponse(IbuHamilBase):
    """Schema for IbuHamil API responses - includes all fields + metadata"""
    id: int
    user_id: int  # ✅ NOW it's here (output only)
    puskesmas_id: Optional[int] = None
    perawat_id: Optional[int] = None
    assigned_by_user_id: Optional[int] = None
    assignment_date: Optional[datetime] = None
    assignment_distance_km: Optional[float] = None
    assignment_method: Optional[str] = None
    is_active: bool = True
    created_at: datetime
    updated_at: datetime

    @field_serializer('location')
    def serialize_location(self, location: Any, _info) -> Optional[Tuple[float, float]]:
        """Convert PostGIS Geography POINT to (longitude, latitude) tuple"""
        if location is None:
            return None
        
        # If already a tuple (from schema), return as-is
        if isinstance(location, tuple):
            return location
        
        # If WKBElement (from PostGIS), parse it
        if isinstance(location, WKBElement):
            point = wkb.loads(bytes(location.data))
            return (point.x, point.y)  # (longitude, latitude)
        
        # If string (WKT format like 'POINT(101.3912 -2.0645)')
        if isinstance(location, str):
            import re
            match = re.match(r'POINT\(([0-9.\-]+)\s+([0-9.\-]+)\)', location)
            if match:
                return (float(match.group(1)), float(match.group(2)))
        
        return None

    model_config = ConfigDict(from_attributes=True, json_schema_extra={
        "example": {
            "id": 1,
            "user_id": 20,
            "nama_lengkap": "Siti Aminah",
            "nik": "3175091201850001",
            "date_of_birth": "1985-12-12",
            "profile_photo_url": "/photos/ibu_hamil/1.jpg",
            "puskesmas_id": 1,
            "perawat_id": 1,
            "location": (101.3912, -2.0645),
            "address": "Jl. Mawar No. 10",
            "provinsi": "Jambi",
            "created_at": "2025-01-01T10:00:00Z",
            "updated_at": "2025-01-02T11:00:00Z",
        }
    })