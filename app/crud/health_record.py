"""CRUD operations for `HealthRecord` model."""

from __future__ import annotations

from datetime import date, timedelta
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
        category: str,  # 'blood_pressure', 'blood_glucose', 'temperature', 'heart_rate', 'hemoglobin'
    ) -> List[HealthRecord]:
        """Get health records from last 7 days filtered by category.

        Categories:
        - 'blood_pressure': Returns records with blood_pressure_systolic OR blood_pressure_diastolic
        - 'blood_glucose': Returns records with blood_glucose
        - 'temperature': Returns records with body_temperature
        - 'heart_rate': Returns records with heart_rate
        - 'hemoglobin': Returns records with hemoglobin
        """
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
        elif category == "hemoglobin":
            conditions.append(HealthRecord.hemoglobin.isnot(None))
        else:
            raise ValueError(f"Invalid category: {category}. Must be one of: blood_pressure, blood_glucose, temperature, heart_rate, hemoglobin")

        stmt = (
            select(HealthRecord)
            .where(and_(*conditions))
            .order_by(HealthRecord.checkup_date.asc(), HealthRecord.created_at.asc())
        )
        return list(db.scalars(stmt).all())

    def get_by_checked_by(
        self,
        db: Session,
        *,
        ibu_hamil_id: int,
        checked_by: str,  # 'perawat' or 'mandiri'
        limit: int = 50,
    ) -> List[HealthRecord]:
        """Get health records filtered by who checked (perawat or mandiri)."""
        stmt = (
            select(HealthRecord)
            .where(
                and_(
                    HealthRecord.ibu_hamil_id == ibu_hamil_id,
                    HealthRecord.checked_by == checked_by,
                )
            )
            .order_by(HealthRecord.checkup_date.desc())
            .limit(limit)
        )
        return list(db.scalars(stmt).all())


# Singleton instance
crud_health_record = CRUDHealthRecord(HealthRecord)
