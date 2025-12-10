"""CRUD operations for `HealthRecord` model."""

from __future__ import annotations

from datetime import date, datetime
from typing import Any, Dict, List, Optional

from sqlalchemy import select, and_
from sqlalchemy.orm import Session

from app.crud.base import CRUDBase
from app.models.health_record import HealthRecord
from app.schemas.health_record import HealthRecordCreate, HealthRecordUpdate


class CRUDHealthRecord(CRUDBase[HealthRecord, HealthRecordCreate, HealthRecordUpdate]):
    def get_by_ibu_hamil(
        self, db: Session, *, ibu_hamil_id: int, limit: int = 50
    ) -> List[HealthRecord]:
        """Get health records for a specific Ibu Hamil, ordered by most recent."""
        stmt = (
            select(HealthRecord)
            .where(HealthRecord.ibu_hamil_id == ibu_hamil_id)
            .order_by(HealthRecord.checkup_date.desc())
            .limit(limit)
        )
        return db.scalars(stmt).all()

    def get_latest(self, db: Session, *, ibu_hamil_id: int) -> Optional[HealthRecord]:
        """Get the most recent health record for a specific Ibu Hamil."""
        stmt = (
            select(HealthRecord)
            .where(HealthRecord.ibu_hamil_id == ibu_hamil_id)
            .order_by(HealthRecord.checkup_date.desc())
            .limit(1)
        )
        return db.scalars(stmt).first()

    def get_by_date_range(
        self,
        db: Session,
        *,
        ibu_hamil_id: int,
        start_date: date,
        end_date: date,
    ) -> List[HealthRecord]:
        """Get health records within a date range."""
        stmt = (
            select(HealthRecord)
            .where(
                and_(
                    HealthRecord.ibu_hamil_id == ibu_hamil_id,
                    HealthRecord.checkup_date >= start_date,
                    HealthRecord.checkup_date <= end_date,
                )
            )
            .order_by(HealthRecord.checkup_date.desc())
        )
        return db.scalars(stmt).all()

    def get_with_referral(self, db: Session) -> List[HealthRecord]:
        """Get all health records that need referral."""
        stmt = (
            select(HealthRecord)
            .where(HealthRecord.referral_needed == True)
            .order_by(HealthRecord.checkup_date.desc())
        )
        return db.scalars(stmt).all()

    def create_from_iot(
        self, db: Session, *, ibu_hamil_id: int, vitals_data: Dict[str, Any]
    ) -> HealthRecord:
        """Create health record from IoT device vitals data.
        
        vitals_data should contain keys like:
        - blood_pressure_systolic, blood_pressure_diastolic
        - blood_glucose, body_temperature, heart_rate
        """
        record_data = {
            "ibu_hamil_id": ibu_hamil_id,
            "checkup_date": date.today(),
            "checkup_type": "ad-hoc",
            "data_source": "iot_device",
            **vitals_data,
        }
        
        db_obj = HealthRecord(**record_data)
        try:
            db.add(db_obj)
            db.commit()
            db.refresh(db_obj)
        except Exception:
            db.rollback()
            raise
        return db_obj


# Singleton instance
crud_health_record = CRUDHealthRecord(HealthRecord)
