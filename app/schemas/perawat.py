"""Pydantic schemas for `Perawat` (Healthcare Worker) domain objects."""

from datetime import datetime
from typing import Optional, Tuple

from pydantic import BaseModel, ConfigDict, field_validator


class PerawatBase(BaseModel):
    user_id: int
    puskesmas_id: int
    nip: str
    job_title: str
    license_number: Optional[str] = None
    license_document_url: Optional[str] = None
    max_patients: Optional[int] = 15
    current_patients: Optional[int] = 0
    work_area: Optional[str] = None
    location: Optional[Tuple[float, float]] = None
    is_available: Optional[bool] = True
    is_active: Optional[bool] = True

    @field_validator("location")
    @classmethod
    def validate_location(cls, v: Optional[Tuple[float, float]]) -> Optional[Tuple[float, float]]:
        if v is None:
            return v
        if not isinstance(v, tuple) or len(v) != 2:
            raise ValueError("Location must be a (longitude, latitude) tuple")
        lon, lat = v
        if not (-180.0 <= lon <= 180.0 and -90.0 <= lat <= 90.0):
            raise ValueError("Longitude must be between -180 and 180, latitude between -90 and 90")
        return lon, lat

    model_config = ConfigDict(json_schema_extra={
        "example": {
            "user_id": 15,
            "puskesmas_id": 1,
            "nip": "198501012015011001",
            "job_title": "Bidan",
            "license_number": "STR-1234567890",
            "license_document_url": "/files/str_bidan.pdf",
            "max_patients": 20,
            "current_patients": 5,
            "work_area": "Kecamatan Pesisir Bukit",
            "location": [101.3912, -2.0645],
            "is_available": True,
            "is_active": True,
        }
    })


class PerawatCreate(PerawatBase):
    created_by_user_id: Optional[int] = None

    model_config = ConfigDict(json_schema_extra={
        "example": {
            **PerawatBase.model_config.get("json_schema_extra", {}).get("example", {}),
            "created_by_user_id": 10,
        }
    })


class PerawatUpdate(BaseModel):
    puskesmas_id: Optional[int] = None
    nip: Optional[str] = None
    job_title: Optional[str] = None
    license_number: Optional[str] = None
    license_document_url: Optional[str] = None
    max_patients: Optional[int] = None
    current_patients: Optional[int] = None
    work_area: Optional[str] = None
    location: Optional[Tuple[float, float]] = None
    is_available: Optional[bool] = None
    is_active: Optional[bool] = None

    @field_validator("location")
    @classmethod
    def validate_location(cls, v: Optional[Tuple[float, float]]) -> Optional[Tuple[float, float]]:
        if v is None:
            return v
        if not isinstance(v, tuple) or len(v) != 2:
            raise ValueError("Location must be a (longitude, latitude) tuple")
        lon, lat = v
        if not (-180.0 <= lon <= 180.0 and -90.0 <= lat <= 90.0):
            raise ValueError("Longitude must be between -180 and 180, latitude between -90 and 90")
        return lon, lat

    model_config = ConfigDict(json_schema_extra={
        "example": {
            "work_area": "Kecamatan Baru",
            "location": [101.4, -2.1],
            "is_available": False,
        }
    })


class PerawatResponse(PerawatBase):
    id: int
    created_by_user_id: Optional[int] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True, json_schema_extra={
        "example": {
            **PerawatBase.model_config.get("json_schema_extra", {}).get("example", {}),
            "id": 1,
            "created_by_user_id": 10,
            "created_at": "2025-01-01T10:00:00Z",
            "updated_at": "2025-01-02T11:00:00Z",
        }
    })
