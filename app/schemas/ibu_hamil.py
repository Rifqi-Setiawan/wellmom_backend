"""Pydantic schemas for `IbuHamil` (Pregnant Woman) domain objects."""

from datetime import date, datetime
from typing import Optional, Tuple

from pydantic import BaseModel, ConfigDict, field_validator


RISK_LEVELS = {"low", "normal", "high"}
ASSIGNMENT_METHODS = {"auto", "manual"}


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


class IbuHamilBase(BaseModel):
    user_id: int
    puskesmas_id: Optional[int] = None
    perawat_id: Optional[int] = None
    nik: str
    date_of_birth: date
    age: Optional[int] = None
    blood_type: Optional[str] = None
    last_menstrual_period: Optional[date] = None
    estimated_due_date: Optional[date] = None
    pregnancy_number: Optional[int] = 1
    birth_number: Optional[int] = 0
    miscarriage_number: Optional[int] = 0
    previous_pregnancy_complications: Optional[str] = None
    address: str
    kelurahan: Optional[str] = None
    kecamatan: Optional[str] = None
    rt_rw: Optional[str] = None
    location: Tuple[float, float]
    house_photo_url: Optional[str] = None
    emergency_contact_name: str
    emergency_contact_phone: str
    emergency_contact_relation: Optional[str] = None
    height_cm: Optional[float] = None
    pre_pregnancy_weight_kg: Optional[float] = None
    medical_history: Optional[str] = None
    current_medications: Optional[str] = None
    risk_level: Optional[str] = "normal"
    healthcare_preference: Optional[str] = None
    whatsapp_consent: Optional[bool] = True
    data_sharing_consent: Optional[bool] = False
    is_active: Optional[bool] = True

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
            "user_id": 20,
            "puskesmas_id": 1,
            "perawat_id": 1,
            "nik": "3175091201850001",
            "date_of_birth": "1985-12-12",
            "age": 39,
            "blood_type": "O+",
            "last_menstrual_period": "2024-12-01",
            "estimated_due_date": "2025-09-08",
            "pregnancy_number": 2,
            "birth_number": 1,
            "miscarriage_number": 0,
            "previous_pregnancy_complications": "None",
            "address": "Jl. Mawar No. 10, RT 02 RW 05",
            "kelurahan": "Sungai Penuh",
            "kecamatan": "Pesisir Bukit",
            "rt_rw": "02/05",
            "location": [101.3912, -2.0645],
            "house_photo_url": "/files/rumah_ibu.jpg",
            "emergency_contact_name": "Budi (Suami)",
            "emergency_contact_phone": "+6281234567890",
            "emergency_contact_relation": "Suami",
            "height_cm": 158.0,
            "pre_pregnancy_weight_kg": 55.0,
            "medical_history": "Tidak ada penyakit kronis",
            "current_medications": "Multivitamin prenatal",
            "risk_level": "normal",
            "healthcare_preference": "puskesmas",
            "whatsapp_consent": True,
            "data_sharing_consent": False,
            "is_active": True,
        }
    })


class IbuHamilCreate(IbuHamilBase):
    assigned_by_user_id: Optional[int] = None
    assignment_date: Optional[datetime] = None
    assignment_distance_km: Optional[float] = None
    assignment_method: Optional[str] = None

    @field_validator("assignment_method")
    @classmethod
    def validate_assignment_method(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and v not in ASSIGNMENT_METHODS:
            raise ValueError(f"Assignment method must be one of {sorted(ASSIGNMENT_METHODS)}")
        return v

    model_config = ConfigDict(json_schema_extra={
        "example": {
            **IbuHamilBase.model_config.get("json_schema_extra", {}).get("example", {}),
            "assigned_by_user_id": 10,
            "assignment_method": "auto",
            "assignment_distance_km": 2.5,
        }
    })


class IbuHamilUpdate(BaseModel):
    puskesmas_id: Optional[int] = None
    perawat_id: Optional[int] = None
    nik: Optional[str] = None
    date_of_birth: Optional[date] = None
    age: Optional[int] = None
    blood_type: Optional[str] = None
    last_menstrual_period: Optional[date] = None
    estimated_due_date: Optional[date] = None
    pregnancy_number: Optional[int] = None
    birth_number: Optional[int] = None
    miscarriage_number: Optional[int] = None
    previous_pregnancy_complications: Optional[str] = None
    address: Optional[str] = None
    kelurahan: Optional[str] = None
    kecamatan: Optional[str] = None
    rt_rw: Optional[str] = None
    location: Optional[Tuple[float, float]] = None
    house_photo_url: Optional[str] = None
    emergency_contact_name: Optional[str] = None
    emergency_contact_phone: Optional[str] = None
    emergency_contact_relation: Optional[str] = None
    height_cm: Optional[float] = None
    pre_pregnancy_weight_kg: Optional[float] = None
    medical_history: Optional[str] = None
    current_medications: Optional[str] = None
    risk_level: Optional[str] = None
    healthcare_preference: Optional[str] = None
    whatsapp_consent: Optional[bool] = None
    data_sharing_consent: Optional[bool] = None
    is_active: Optional[bool] = None
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
            "location": [101.4, -2.1],
            "risk_level": "high",
            "current_medications": "Vitamin D, Asam folat",
        }
    })


class IbuHamilResponse(IbuHamilBase):
    id: int
    assigned_by_user_id: Optional[int] = None
    assignment_date: Optional[datetime] = None
    assignment_distance_km: Optional[float] = None
    assignment_method: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True, json_schema_extra={
        "example": {
            **IbuHamilBase.model_config.get("json_schema_extra", {}).get("example", {}),
            "id": 1,
            "assigned_by_user_id": 10,
            "assignment_date": "2025-01-01T10:00:00Z",
            "assignment_distance_km": 2.5,
            "assignment_method": "auto",
            "created_at": "2025-01-01T10:00:00Z",
            "updated_at": "2025-01-02T11:00:00Z",
        }
    })
