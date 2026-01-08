"""CRUD operations for `HealthRecord` model."""

from __future__ import annotations

from datetime import date, datetime
from typing import Any, Dict, List, Optional

from sqlalchemy import select, and_, or_
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
    
    def get_by_date(
        self,
        db: Session,
        *,
        ibu_hamil_id: int,
        checkup_date: date,
    ) -> List[HealthRecord]:
        """Get health records for a specific date."""
        stmt = (
            select(HealthRecord)
            .where(
                and_(
                    HealthRecord.ibu_hamil_id == ibu_hamil_id,
                    HealthRecord.checkup_date == checkup_date,
                )
            )
            .order_by(HealthRecord.created_at.desc())
        )
        return list(db.scalars(stmt).all())
    
    def get_last_7_days_by_category(
        self,
        db: Session,
        *,
        ibu_hamil_id: int,
        category: str,  # 'blood_pressure', 'blood_glucose', 'temperature', 'heart_rate'
    ) -> List[HealthRecord]:
        """Get health records from last 7 days filtered by category.
        
        Categories:
        - 'blood_pressure': Returns records with blood_pressure_systolic OR blood_pressure_diastolic
        - 'blood_glucose': Returns records with blood_glucose
        - 'temperature': Returns records with body_temperature
        - 'heart_rate': Returns records with heart_rate
        """
        from datetime import timedelta
        
        end_date = date.today()
        start_date = end_date - timedelta(days=6)  # Last 7 days (including today)
        
        # Build query based on category
        conditions = [
            HealthRecord.ibu_hamil_id == ibu_hamil_id,
            HealthRecord.checkup_date >= start_date,
            HealthRecord.checkup_date <= end_date,
        ]
        
        # Add category-specific filter
        if category == "blood_pressure":
            conditions.append(
                or_(
                    HealthRecord.blood_pressure_systolic.isnot(None),
                    HealthRecord.blood_pressure_diastolic.isnot(None)
                )
            )
        elif category == "blood_glucose":
            conditions.append(HealthRecord.blood_glucose.isnot(None))
        elif category == "temperature":
            conditions.append(HealthRecord.body_temperature.isnot(None))
        elif category == "heart_rate":
            conditions.append(HealthRecord.heart_rate.isnot(None))
        else:
            raise ValueError(f"Invalid category: {category}. Must be one of: blood_pressure, blood_glucose, temperature, heart_rate")
        
        stmt = (
            select(HealthRecord)
            .where(and_(*conditions))
            .order_by(HealthRecord.checkup_date.asc(), HealthRecord.created_at.asc())
        )
        return list(db.scalars(stmt).all())


# Singleton instance
crud_health_record = CRUDHealthRecord(HealthRecord)
