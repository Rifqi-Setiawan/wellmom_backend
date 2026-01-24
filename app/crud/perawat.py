"""CRUD operations for `Perawat` model."""

from __future__ import annotations

from typing import List, Optional

from sqlalchemy import select, and_, func
from sqlalchemy.orm import Session

from app.crud.base import CRUDBase
from app.models.perawat import Perawat
from app.models.ibu_hamil import IbuHamil
from app.schemas.perawat import PerawatCreate, PerawatUpdate


class CRUDPerawat(CRUDBase[Perawat, PerawatCreate, PerawatUpdate]):
    def get_by_puskesmas(self, db: Session, *, puskesmas_id: int) -> List[Perawat]:
        """Get all Perawat in a specific Puskesmas."""
        stmt = select(Perawat).where(Perawat.puskesmas_id == puskesmas_id)
        return db.scalars(stmt).all()

    def get_active_by_puskesmas(self, db: Session, *, puskesmas_id: int) -> List[Perawat]:
        """Get all active Perawat in a specific Puskesmas."""
        stmt = select(Perawat).where(
            and_(
                Perawat.puskesmas_id == puskesmas_id,
                Perawat.is_active == True
            )
        )
        return db.scalars(stmt).all()

    def get_by_nip(self, db: Session, *, nip: str) -> Optional[Perawat]:
        """Get Perawat by NIP."""
        stmt = select(Perawat).where(Perawat.nip == nip).limit(1)
        return db.scalars(stmt).first()

    def get_by_email(self, db: Session, *, email: str) -> Optional[Perawat]:
        """Get Perawat by email."""
        stmt = select(Perawat).where(Perawat.email == email).limit(1)
        return db.scalars(stmt).first()

    def get_by_user_id(self, db: Session, *, user_id: int) -> Optional[Perawat]:
        """Get Perawat by user_id."""
        stmt = select(Perawat).where(Perawat.user_id == user_id).limit(1)
        return db.scalars(stmt).first()

    def get_with_patient_count(self, db: Session, *, perawat_id: int) -> Optional[dict]:
        """Get Perawat with patient count."""
        perawat = self.get(db, perawat_id)
        if not perawat:
            return None
        
        # Count ibu hamil assigned to this perawat
        patient_count = db.scalar(
            select(func.count(IbuHamil.id)).where(IbuHamil.perawat_id == perawat_id)
        ) or 0
        
        return {
            "perawat": perawat,
            "jumlah_ibu_hamil": patient_count
        }

    def assign_patient(
        self, db: Session, *, perawat_id: int, ibu_hamil_id: int
    ) -> Optional[Perawat]:
        """Assign an Ibu Hamil to this Perawat.
        
        Note: This updates the IbuHamil.perawat_id field.
        """
        perawat = self.get(db, perawat_id)
        if not perawat:
            return None
        
        # Update IbuHamil record
        ibu_hamil = db.get(IbuHamil, ibu_hamil_id)
        if not ibu_hamil:
            return None
        
        ibu_hamil.perawat_id = perawat_id
        
        try:
            db.add(ibu_hamil)
            db.commit()
            db.refresh(perawat)
        except Exception:
            db.rollback()
            raise
        return perawat

    def get_available(self, db: Session, *, puskesmas_id: int, max_patients: int = 50) -> List[Perawat]:
        stmt = (
            select(Perawat)
            .where(Perawat.puskesmas_id == puskesmas_id)
            .where(Perawat.is_active == True)
            .where(Perawat.current_patients < max_patients)
            .order_by(Perawat.current_patients)
        )
        return db.scalars(stmt).all()

    def update_workload(self, db: Session, *, perawat_id: int, increment: int = 1) -> Optional[Perawat]:
        perawat = self.get(db, perawat_id)
        if not perawat:
            return None
        perawat.current_patients = (perawat.current_patients or 0) + increment
        db.add(perawat)
        db.commit()
        db.refresh(perawat)
        return perawat


# Singleton instance
crud_perawat = CRUDPerawat(Perawat)
