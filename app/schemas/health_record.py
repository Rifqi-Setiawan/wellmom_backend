"""Pydantic schemas for `HealthRecord` domain objects."""

from datetime import date, datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, field_validator


CHECKUP_TYPES = {"berkala", "ad-hoc"}
DATA_SOURCES = {"manual", "iot_device"}


class HealthRecordBase(BaseModel):
    ibu_hamil_id: int
    perawat_id: Optional[int] = None
    checkup_date: date
    checkup_type: str
    data_source: Optional[str] = "manual"
    gestational_age_weeks: Optional[int] = None
    gestational_age_days: Optional[int] = None
    blood_pressure_systolic: Optional[int] = None
    blood_pressure_diastolic: Optional[int] = None
    blood_glucose: Optional[float] = None
    body_temperature: Optional[float] = None
    heart_rate: Optional[int] = None
    fundal_height_cm: Optional[float] = None
    fetal_heart_rate: Optional[int] = None
    complaints: Optional[str] = None
    physical_examination: Optional[str] = None
    diagnosis: Optional[str] = None
    treatment_plan: Optional[str] = None
    medications: Optional[str] = None
    supplements: Optional[str] = None
    referral_needed: Optional[bool] = False
    referral_notes: Optional[str] = None
    next_checkup_date: Optional[date] = None
    next_checkup_notes: Optional[str] = None
    notes: Optional[str] = None

    @field_validator("checkup_type")
    @classmethod
    def validate_checkup_type(cls, v: str) -> str:
        if v not in CHECKUP_TYPES:
            raise ValueError(f"Checkup type must be one of {sorted(CHECKUP_TYPES)}")
        return v

    @field_validator("data_source")
    @classmethod
    def validate_data_source(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and v not in DATA_SOURCES:
            raise ValueError(f"Data source must be one of {sorted(DATA_SOURCES)}")
        return v

    model_config = ConfigDict(json_schema_extra={
        "example": {
            "ibu_hamil_id": 1,
            "perawat_id": 1,
            "checkup_date": "2025-02-15",
            "checkup_type": "berkala",
            "data_source": "manual",
            "gestational_age_weeks": 28,
            "gestational_age_days": 3,
            "blood_pressure_systolic": 120,
            "blood_pressure_diastolic": 80,
            "blood_glucose": 95.0,
            "body_temperature": 36.8,
            "heart_rate": 72,
            "fundal_height_cm": 28.0,
            "fetal_heart_rate": 140,
            "complaints": "Tidak ada keluhan",
            "physical_examination": "Kondisi baik",
            "diagnosis": "Kehamilan normal trimester 3",
            "treatment_plan": "Kontrol rutin bulanan",
            "medications": "Tidak ada",
            "supplements": "Asam folat, Zat besi",
            "referral_needed": False,
            "referral_notes": None,
            "next_checkup_date": "2025-03-15",
            "next_checkup_notes": "Pemeriksaan rutin bulan ke-7",
            "notes": "Ibu dalam kondisi sehat",
        }
    })


class HealthRecordCreate(HealthRecordBase):
    model_config = ConfigDict(json_schema_extra={
        "example": HealthRecordBase.model_config.get("json_schema_extra", {}).get("example", {})
    })


class HealthRecordUpdate(BaseModel):
    perawat_id: Optional[int] = None
    checkup_date: Optional[date] = None
    checkup_type: Optional[str] = None
    data_source: Optional[str] = None
    gestational_age_weeks: Optional[int] = None
    gestational_age_days: Optional[int] = None
    blood_pressure_systolic: Optional[int] = None
    blood_pressure_diastolic: Optional[int] = None
    blood_glucose: Optional[float] = None
    body_temperature: Optional[float] = None
    heart_rate: Optional[int] = None
    fundal_height_cm: Optional[float] = None
    fetal_heart_rate: Optional[int] = None
    complaints: Optional[str] = None
    physical_examination: Optional[str] = None
    diagnosis: Optional[str] = None
    treatment_plan: Optional[str] = None
    medications: Optional[str] = None
    supplements: Optional[str] = None
    referral_needed: Optional[bool] = None
    referral_notes: Optional[str] = None
    next_checkup_date: Optional[date] = None
    next_checkup_notes: Optional[str] = None
    notes: Optional[str] = None

    @field_validator("checkup_type")
    @classmethod
    def validate_checkup_type(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and v not in CHECKUP_TYPES:
            raise ValueError(f"Checkup type must be one of {sorted(CHECKUP_TYPES)}")
        return v

    @field_validator("data_source")
    @classmethod
    def validate_data_source(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and v not in DATA_SOURCES:
            raise ValueError(f"Data source must be one of {sorted(DATA_SOURCES)}")
        return v

    model_config = ConfigDict(json_schema_extra={
        "example": {
            "blood_pressure_systolic": 125,
            "blood_pressure_diastolic": 82,
            "diagnosis": "Kehamilan normal, tekanan darah sedikit tinggi",
            "treatment_plan": "Monitor tekanan darah harian",
        }
    })


class HealthRecordResponse(HealthRecordBase):
    id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True, json_schema_extra={
        "example": {
            **HealthRecordBase.model_config.get("json_schema_extra", {}).get("example", {}),
            "id": 1,
            "created_at": "2025-02-15T10:00:00Z",
            "updated_at": "2025-02-15T10:00:00Z",
        }
    })


class HealthRecordListResponse(BaseModel):
    """Response for listing health records."""
    records: List[HealthRecordResponse]
    total: int


class HealthRecordLast7DaysResponse(BaseModel):
    """Response for last 7 days health records by category."""
    category: str
    records: List[HealthRecordResponse]
    total: int
    start_date: date
    end_date: date