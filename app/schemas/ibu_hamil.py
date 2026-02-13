"""Pydantic schemas for `IbuHamil` (Pregnant Woman) domain objects."""

from datetime import date, datetime
from typing import Any, Optional, Tuple, TYPE_CHECKING

from pydantic import BaseModel, ConfigDict, EmailStr, field_serializer, field_validator
from geoalchemy2.elements import WKBElement
from shapely import wkb

if TYPE_CHECKING:
    from app.schemas.user import UserResponse


RISK_LEVELS = {"rendah", "sedang", "tinggi"}
ASSIGNMENT_METHODS = {"auto", "manual"}
VALID_BLOOD_TYPES = {"A", "B", "AB", "O"}


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
    """
    Base schema for IbuHamil - common fields for input/output.

    NOTE:
    - user_id is NOT here because it's set programmatically, not user input
    - risk_level akan diabaikan saat registrasi (ditentukan oleh perawat setelah assessment)
    - profile_photo_url akan diabaikan saat registrasi (upload via endpoint terpisah)

    Field Wajib:
    - nama_lengkap: Nama lengkap ibu hamil
    - nik: NIK 16 digit (harus unik)
    - date_of_birth: Tanggal lahir
    - address: Alamat lengkap
    - location: Koordinat [longitude, latitude]
    - emergency_contact_name: Nama kontak darurat
    - emergency_contact_phone: Nomor telepon kontak darurat (8-15 digit)

    Field Opsional:
    - Data kehamilan (usia_kehamilan, kehamilan_ke, jumlah_anak, dll)
    - Riwayat kesehatan (riwayat_kesehatan_ibu)
    - Data demografis (age, blood_type)
    - Preferensi (healthcare_preference, whatsapp_consent, data_sharing_consent)
    """
    # Identitas Pribadi
    nama_lengkap: str
    nik: str
    date_of_birth: date
    profile_photo_url: Optional[str] = None  # Foto profil (diabaikan saat registrasi)

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
    blood_type: Optional[str] = None  # A, B, AB, O
    risk_level: Optional[str] = None  # DIABAIKAN saat registrasi! Ditentukan oleh perawat (rendah/sedang/tinggi)
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

    @field_validator("blood_type")
    @classmethod
    def validate_blood_type(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and v not in VALID_BLOOD_TYPES:
            raise ValueError(f"Blood type must be one of {sorted(VALID_BLOOD_TYPES)}")
        return v

    @field_validator("emergency_contact_phone")
    @classmethod
    def validate_emergency_phone(cls, v: str) -> str:
        import re
        if not re.match(r"^\+?\d{8,15}$", v):
            raise ValueError("Emergency contact phone must be 8-15 digits, optional leading '+'")
        return v

    model_config = ConfigDict(json_schema_extra={
        "example": {
            "nama_lengkap": "Siti Aminah",
            "nik": "3175091201850001",
            "date_of_birth": "1985-12-12",
            "age": 39,
            "blood_type": "O",
            "address": "Jl. Mawar No. 10, RT 02 RW 05",
            "provinsi": "Jambi",
            "kota_kabupaten": "Kerinci",
            "kelurahan": "Sungai Penuh",
            "kecamatan": "Pesisir Bukit",
            "location": [101.3912, -2.0645],
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
                "tbc_malaria": False
            },
            "emergency_contact_name": "Budi (Suami)",
            "emergency_contact_phone": "+6281234567890",
            "emergency_contact_relation": "Suami",
            "healthcare_preference": "puskesmas",
            "whatsapp_consent": True,
            "data_sharing_consent": False
        }
    })


class IbuHamilCreate(IbuHamilBase):
    """
    Schema untuk membuat profil ibu hamil baru (registrasi).

    Digunakan sebagai bagian dari IbuHamilRegisterRequest.

    CATATAN PENTING:
    - user_id di-set secara programatik, bukan dari input user
    - risk_level akan DIABAIKAN saat registrasi (di-set ke NULL)
    - profile_photo_url akan DIABAIKAN saat registrasi

    Risk level akan ditentukan oleh perawat setelah melakukan assessment kesehatan.
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

    @field_validator("blood_type")
    @classmethod
    def validate_blood_type(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and v not in VALID_BLOOD_TYPES:
            raise ValueError(f"Blood type must be one of {sorted(VALID_BLOOD_TYPES)}")
        return v

    @field_validator("emergency_contact_phone")
    @classmethod
    def validate_emergency_phone(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        import re
        if not re.match(r"^\+?\d{8,15}$", v):
            raise ValueError("Emergency contact phone must be 8-15 digits, optional leading '+'")
        return v

    model_config = ConfigDict(json_schema_extra={
        "example": {
            "perawat_id": 2,
            "location": (101.4, -2.1),
            "risk_level": "tinggi",
        }
    })


class IbuHamilResponse(BaseModel):
    """Schema for IbuHamil API responses - includes all fields + metadata
    
    NOTE: This class does NOT inherit from IbuHamilBase to avoid validator conflicts
    with PostGIS WKBElement conversion.
    """
    # IDs
    id: int
    user_id: int
    puskesmas_id: Optional[int] = None
    perawat_id: Optional[int] = None
    assigned_by_user_id: Optional[int] = None
    
    # Identitas Pribadi
    nama_lengkap: str
    nik: str
    date_of_birth: date
    age: Optional[int] = None
    blood_type: Optional[str] = None
    profile_photo_url: Optional[str] = None
    
    # Data Kehamilan
    last_menstrual_period: Optional[date] = None
    estimated_due_date: Optional[date] = None
    usia_kehamilan: Optional[int] = None
    kehamilan_ke: Optional[int] = None
    jumlah_anak: Optional[int] = None
    miscarriage_number: Optional[int] = None
    jarak_kehamilan_terakhir: Optional[str] = None
    previous_pregnancy_complications: Optional[str] = None
    pernah_caesar: Optional[bool] = None
    pernah_perdarahan_saat_hamil: Optional[bool] = None
    
    # Alamat & Lokasi - Accept Any for WKBElement conversion
    address: str
    provinsi: Optional[str] = None
    kota_kabupaten: Optional[str] = None
    kelurahan: Optional[str] = None
    kecamatan: Optional[str] = None
    location: Any  # Will be converted from WKBElement to tuple
    
    # Kontak Darurat
    emergency_contact_name: str
    emergency_contact_phone: str
    emergency_contact_relation: Optional[str] = None
    
    # Riwayat Kesehatan (flattened from model)
    darah_tinggi: Optional[bool] = None
    diabetes: Optional[bool] = None
    anemia: Optional[bool] = None
    penyakit_jantung: Optional[bool] = None
    asma: Optional[bool] = None
    penyakit_ginjal: Optional[bool] = None
    tbc_malaria: Optional[bool] = None
    
    # Risk Assessment (ditentukan oleh perawat)
    risk_level: Optional[str] = None  # rendah, sedang, tinggi
    risk_level_set_by: Optional[int] = None  # ID perawat yang menentukan
    risk_level_set_by_name: Optional[str] = None  # Nama perawat yang menentukan
    risk_level_set_at: Optional[datetime] = None  # Waktu penentuan risiko

    # Assignment
    assignment_date: Optional[datetime] = None
    assignment_distance_km: Optional[float] = None
    assignment_method: Optional[str] = None
    
    # Preferences
    healthcare_preference: Optional[str] = None
    whatsapp_consent: Optional[bool] = None
    data_sharing_consent: Optional[bool] = None
    
    # Status & Timestamps
    is_active: bool = True
    created_at: datetime
    updated_at: datetime

    @field_validator('location', mode='before')
    @classmethod
    def convert_location_from_wkb(cls, v: Any) -> Optional[Tuple[float, float]]:
        """Convert PostGIS WKBElement to tuple before validation"""
        if v is None:
            return None
        
        # If already a tuple/list, convert to tuple
        if isinstance(v, (tuple, list)):
            return tuple(v)
        
        # If WKBElement (from PostGIS), parse it
        if isinstance(v, WKBElement):
            point = wkb.loads(bytes(v.data))
            return (point.x, point.y)  # (longitude, latitude)
        
        # If string (WKT format like 'POINT(101.3912 -2.0645)')
        if isinstance(v, str):
            import re
            match = re.match(r'POINT\(([0-9.\-]+)\s+([0-9.\-]+)\)', v)
            if match:
                return (float(match.group(1)), float(match.group(2)))
        
        return v

    @field_serializer('location')
    def serialize_location(self, location: Any, _info) -> Optional[list]:
        """Serialize location to JSON array [longitude, latitude]"""
        if location is None:
            return None
        if isinstance(location, (tuple, list)):
            return list(location)
        return None

    @field_validator('risk_level_set_by_name', mode='before')
    @classmethod
    def extract_risk_assessor_name(cls, v: Any, info) -> Optional[str]:
        """Extract risk assessor name from relationship if available"""
        if v is not None:
            return v
        # Try to get from risk_assessor relationship via info.data
        if hasattr(info, 'data') and info.data:
            risk_assessor = info.data.get('risk_assessor')
            if risk_assessor and hasattr(risk_assessor, 'nama_lengkap'):
                return risk_assessor.nama_lengkap
        return None

    model_config = ConfigDict(from_attributes=True, json_schema_extra={
        "example": {
            "id": 1,
            "user_id": 20,
            "puskesmas_id": 1,
            "perawat_id": 5,
            "assigned_by_user_id": 10,
            "nama_lengkap": "Siti Aminah",
            "nik": "3175091201850001",
            "date_of_birth": "1985-12-12",
            "age": 39,
            "blood_type": "O",
            "profile_photo_url": "/uploads/photos/profiles/ibu_hamil/ibu_hamil_1_20250118_123456.jpg",
            "last_menstrual_period": "2024-12-01",
            "estimated_due_date": "2025-09-08",
            "usia_kehamilan": 8,
            "kehamilan_ke": 2,
            "jumlah_anak": 1,
            "miscarriage_number": 0,
            "jarak_kehamilan_terakhir": "2 tahun",
            "previous_pregnancy_complications": None,
            "pernah_caesar": False,
            "pernah_perdarahan_saat_hamil": False,
            "address": "Jl. Mawar No. 10, RT 02 RW 05",
            "provinsi": "Jambi",
            "kota_kabupaten": "Kerinci",
            "kelurahan": "Sungai Penuh",
            "kecamatan": "Pesisir Bukit",
            "location": [101.3912, -2.0645],
            "emergency_contact_name": "Budi (Suami)",
            "emergency_contact_phone": "+6281234567890",
            "emergency_contact_relation": "Suami",
            "darah_tinggi": False,
            "diabetes": False,
            "anemia": False,
            "penyakit_jantung": False,
            "asma": False,
            "penyakit_ginjal": False,
            "tbc_malaria": False,
            "risk_level": "tinggi",
            "risk_level_set_by": 5,
            "risk_level_set_by_name": "Bidan Rina Wijaya",
            "risk_level_set_at": "2026-01-20T10:30:00Z",
            "assignment_date": "2026-01-15T08:00:00Z",
            "assignment_distance_km": 2.5,
            "assignment_method": "manual",
            "healthcare_preference": "puskesmas",
            "whatsapp_consent": True,
            "data_sharing_consent": False,
            "is_active": True,
            "created_at": "2026-01-10T10:00:00Z",
            "updated_at": "2026-01-20T10:30:00Z",
        }
    })


# ============================================================================
# PROFILE SETTING SCHEMAS
# ============================================================================

class IbuHamilProfileResponse(BaseModel):
    """Schema untuk response profil lengkap ibu hamil (gabungan user + ibu hamil)
    
    Digunakan untuk halaman profile setting yang menampilkan semua data user dan ibu hamil.
    """
    # User data - using forward reference to avoid circular import
    user: Any  # Will be validated as UserResponse at runtime
    
    # Ibu hamil data
    ibu_hamil: IbuHamilResponse
    
    model_config = ConfigDict(json_schema_extra={
        "example": {
            "user": {
                "id": 15,
                "email": "siti.aminah@example.com",
                "phone": "+6281234567890",
                "full_name": "Siti Aminah",
                "role": "ibu_hamil",
                "profile_photo_url": None,
                "is_active": True,
                "is_verified": False,
                "created_at": "2026-01-09T21:18:41.584534",
                "updated_at": "2026-01-09T21:18:41.584534"
            },
            "ibu_hamil": {
                "id": 18,
                "user_id": 15,
                "puskesmas_id": 1,
                "perawat_id": None,
                "nama_lengkap": "Siti Aminah",
                "nik": "3175091201850001",
                "date_of_birth": "1985-12-12",
                "age": 39,
                "blood_type": "O",
                "location": [101.3912, -2.0645],
                "address": "Jl. Mawar No. 10, RT 02 RW 05",
                "provinsi": "Jambi",
                "kota_kabupaten": "Kerinci",
                "kelurahan": "Sungai Penuh",
                "kecamatan": "Pesisir Bukit",
                "is_active": True,
                "created_at": "2026-01-09T21:18:41.640648",
                "updated_at": "2026-01-09T21:18:41.640648"
            }
        }
    })


class UserUpdateProfile(BaseModel):
    """Schema untuk update data user oleh user sendiri (untuk profile setting)
    
    Hanya field yang bisa diupdate oleh user sendiri:
    - email
    - phone
    - full_name
    - password (optional, jika diisi akan diupdate)
    """
    email: Optional[str] = None
    phone: Optional[str] = None
    full_name: Optional[str] = None
    password: Optional[str] = None  # Jika diisi, akan diupdate password
    
    @field_validator("phone")
    @classmethod
    def validate_phone(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        if not __import__("re").match(r"^\+?\d{8,15}$", v):
            raise ValueError("Phone must be 8-15 digits, optional leading '+'")
        return v
    
    @field_validator("password")
    @classmethod
    def validate_password(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        if len(v) < 6:
            raise ValueError("Password minimal 6 karakter")
        return v
    
    model_config = ConfigDict(json_schema_extra={
        "example": {
            "email": "siti.new@example.com",
            "phone": "+628111222333",
            "full_name": "Siti Aminah Updated",
            "password": "NewPassword123!"
        }
    })


class IbuHamilUpdateIdentitas(BaseModel):
    """Schema untuk update identitas pribadi & alamat ibu hamil
    
    Digunakan untuk halaman profile setting identitas pribadi.
    Field yang dapat diupdate:
    - nama_lengkap
    - date_of_birth
    - nik
    - address, provinsi, kota_kabupaten, kelurahan, kecamatan, location
    """
    nama_lengkap: Optional[str] = None
    date_of_birth: Optional[date] = None
    nik: Optional[str] = None
    address: Optional[str] = None
    provinsi: Optional[str] = None
    kota_kabupaten: Optional[str] = None
    kelurahan: Optional[str] = None
    kecamatan: Optional[str] = None
    location: Optional[Tuple[float, float]] = None
    
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
    
    model_config = ConfigDict(json_schema_extra={
        "example": {
            "nama_lengkap": "Siti Aminah Updated",
            "date_of_birth": "1985-12-12",
            "nik": "3175091201850001",
            "address": "Jl. Mawar No. 10, RT 02 RW 05",
            "provinsi": "Jambi",
            "kota_kabupaten": "Kerinci",
            "kelurahan": "Sungai Penuh",
            "kecamatan": "Pesisir Bukit",
            "location": [101.3912, -2.0645]
        }
    })


class IbuHamilUpdateKehamilan(BaseModel):
    """Schema untuk update data kehamilan & riwayat kesehatan ibu hamil
    
    Digunakan untuk halaman profile setting data kehamilan.
    Field yang dapat diupdate:
    - Data kehamilan (usia_kehamilan, kehamilan_ke, jumlah_anak, dll)
    - Riwayat kesehatan (riwayat_kesehatan_ibu)
    """
    # Data Kehamilan
    usia_kehamilan: Optional[int] = None
    kehamilan_ke: Optional[int] = None
    jumlah_anak: Optional[int] = None
    miscarriage_number: Optional[int] = None
    jarak_kehamilan_terakhir: Optional[str] = None
    last_menstrual_period: Optional[date] = None  # HPHT
    estimated_due_date: Optional[date] = None  # HPL
    previous_pregnancy_complications: Optional[str] = None
    pernah_caesar: Optional[bool] = None
    pernah_perdarahan_saat_hamil: Optional[bool] = None
    
    # Riwayat Kesehatan
    riwayat_kesehatan_ibu: Optional[RiwayatKesehatanIbu] = None
    
    model_config = ConfigDict(json_schema_extra={
        "example": {
            "usia_kehamilan": 9,
            "kehamilan_ke": 2,
            "jumlah_anak": 1,
            "miscarriage_number": 0,
            "jarak_kehamilan_terakhir": "2 tahun",
            "last_menstrual_period": "2024-12-01",
            "estimated_due_date": "2025-09-08",
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
                "tbc_malaria": False
            }
        }
    })


# ============================================================================
# MY PERAWAT SCHEMAS (for Ibu Hamil Homepage)
# ============================================================================

class MyPerawatInfo(BaseModel):
    """Info perawat untuk homepage ibu hamil."""
    id: int
    nama_lengkap: str
    email: str
    nomor_hp: str
    profile_photo_url: Optional[str] = None

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "id": 1,
                "nama_lengkap": "Siti Nurhaliza",
                "email": "siti.nurhaliza@puskesmas.go.id",
                "nomor_hp": "+6281234567890",
                "profile_photo_url": "/uploads/photos/profiles/perawat/perawat_1.jpg"
            }
        }
    )


class MyPuskesmasInfo(BaseModel):
    """Info puskesmas untuk homepage ibu hamil."""
    id: int
    name: str
    address: Optional[str] = None
    phone: Optional[str] = None

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "id": 1,
                "name": "Puskesmas Hamparan Pugu",
                "address": "Jl. Raya No. 1, Kec. Hamparan Pugu",
                "phone": "021-1234567"
            }
        }
    )


class MyPerawatResponse(BaseModel):
    """Response untuk data perawat bagi ibu hamil.

    Digunakan di homepage ibu hamil untuk menampilkan data perawat yang ditugaskan.
    Jika ibu hamil belum mendapatkan perawat, field `has_perawat` akan bernilai False
    dan field `perawat` akan bernilai null.

    **Kondisi Response:**
    1. Sudah mendapat perawat: has_perawat=true, perawat dan puskesmas tersedia
    2. Belum mendapat perawat (tapi sudah di puskesmas): has_perawat=false, perawat=null, puskesmas tersedia
    3. Belum terdaftar di puskesmas: has_perawat=false, perawat=null, puskesmas=null
    """
    has_perawat: bool
    perawat: Optional[MyPerawatInfo] = None
    puskesmas: Optional[MyPuskesmasInfo] = None
    message: str

    model_config = ConfigDict(json_schema_extra={
        "example": {
            "has_perawat": True,
            "perawat": {
                "id": 1,
                "nama_lengkap": "Siti Nurhaliza",
                "email": "siti.nurhaliza@puskesmas.go.id",
                "nomor_hp": "+6281234567890",
                "profile_photo_url": "/uploads/photos/profiles/perawat/perawat_1.jpg"
            },
            "puskesmas": {
                "id": 1,
                "name": "Puskesmas Hamparan Pugu",
                "address": "Jl. Raya No. 1",
                "phone": "021-1234567"
            },
            "message": "Anda sudah mendapatkan perawat pendamping"
        }
    })