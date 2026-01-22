"""Pydantic schemas for `HealthRecord` domain objects."""

from datetime import date, datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, field_validator


CHECKED_BY_VALUES = {"perawat", "mandiri"}


class HealthRecordBase(BaseModel):
    ibu_hamil_id: int
    perawat_id: Optional[int] = None
    checkup_date: date
    checked_by: str  # 'perawat' or 'mandiri'

    # Gestational Age
    gestational_age_weeks: Optional[int] = None
    gestational_age_days: Optional[int] = None

    # Required Vital Signs (wajib diisi)
    blood_pressure_systolic: int
    blood_pressure_diastolic: int
    heart_rate: int
    body_temperature: float
    weight: float  # berat badan (kg)
    complaints: str  # keluhan

    # Optional Lab/Puskesmas Data (tidak wajib)
    hemoglobin: Optional[float] = None  # g/dL
    blood_glucose: Optional[float] = None  # gula darah (mg/dL)
    protein_urin: Optional[str] = None  # negatif, +1, +2, +3, +4
    upper_arm_circumference: Optional[float] = None  # lingkar lengan atas / LILA (cm)
    fundal_height: Optional[float] = None  # tinggi fundus uteri (cm)
    fetal_heart_rate: Optional[int] = None  # denyut jantung janin (bpm)

    # Additional Notes
    notes: Optional[str] = None

    @field_validator("checked_by")
    @classmethod
    def validate_checked_by(cls, v: str) -> str:
        if v not in CHECKED_BY_VALUES:
            raise ValueError(f"checked_by must be one of {sorted(CHECKED_BY_VALUES)}")
        return v

    model_config = ConfigDict(json_schema_extra={
        "example": {
            "ibu_hamil_id": 1,
            "perawat_id": 1,
            "checkup_date": "2025-02-15",
            "checked_by": "perawat",
            "gestational_age_weeks": 28,
            "gestational_age_days": 3,
            "blood_pressure_systolic": 120,
            "blood_pressure_diastolic": 80,
            "heart_rate": 72,
            "body_temperature": 36.8,
            "weight": 65.5,
            "complaints": "Tidak ada keluhan",
            "hemoglobin": 12.5,
            "blood_glucose": 95.0,
            "protein_urin": "negatif",
            "upper_arm_circumference": 25.0,
            "fundal_height": 28.0,
            "fetal_heart_rate": 140,
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
    checked_by: Optional[str] = None
    gestational_age_weeks: Optional[int] = None
    gestational_age_days: Optional[int] = None

    # Vital Signs (all optional for update)
    blood_pressure_systolic: Optional[int] = None
    blood_pressure_diastolic: Optional[int] = None
    heart_rate: Optional[int] = None
    body_temperature: Optional[float] = None
    weight: Optional[float] = None
    complaints: Optional[str] = None

    # Optional Lab/Puskesmas Data
    hemoglobin: Optional[float] = None
    blood_glucose: Optional[float] = None
    protein_urin: Optional[str] = None
    upper_arm_circumference: Optional[float] = None
    fundal_height: Optional[float] = None
    fetal_heart_rate: Optional[int] = None

    # Additional Notes
    notes: Optional[str] = None

    @field_validator("checked_by")
    @classmethod
    def validate_checked_by(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and v not in CHECKED_BY_VALUES:
            raise ValueError(f"checked_by must be one of {sorted(CHECKED_BY_VALUES)}")
        return v

    model_config = ConfigDict(json_schema_extra={
        "example": {
            "blood_pressure_systolic": 125,
            "blood_pressure_diastolic": 82,
            "complaints": "Sedikit pusing",
            "notes": "Monitor tekanan darah harian",
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
