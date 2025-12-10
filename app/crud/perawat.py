"""CRUD operations for `Perawat` model."""

from __future__ import annotations

from typing import List, Optional

from sqlalchemy import select, and_
from sqlalchemy.orm import Session

from app.crud.base import CRUDBase
from app.models.perawat import Perawat
from app.schemas.perawat import PerawatCreate, PerawatUpdate


class CRUDPerawat(CRUDBase[Perawat, PerawatCreate, PerawatUpdate]):
    def get_by_puskesmas(self, db: Session, *, puskesmas_id: int) -> List[Perawat]:
        """Get all Perawat in a specific Puskesmas."""
        stmt = select(Perawat).where(Perawat.puskesmas_id == puskesmas_id)
        return db.scalars(stmt).all()

    def get_available(self, db: Session, *, puskesmas_id: Optional[int] = None) -> List[Perawat]:
        """Get available Perawat (is_available=True and has capacity)."""
        conditions = [
            Perawat.is_available == True,
            Perawat.is_active == True,
            Perawat.current_patients < Perawat.max_patients,
        ]
        
        if puskesmas_id is not None:
            conditions.append(Perawat.puskesmas_id == puskesmas_id)
        
        stmt = select(Perawat).where(and_(*conditions))
        return db.scalars(stmt).all()

    def update_workload(
        self, db: Session, *, perawat_id: int, increment: int
    ) -> Optional[Perawat]:
        """Adjust current_patients count.
        
        Use positive increment to add patients, negative to reduce.
        """
        perawat = self.get(db, perawat_id)
        if not perawat:
            return None
        
        new_count = (perawat.current_patients or 0) + increment
        # Ensure it doesn't go below 0 or exceed max_patients
        perawat.current_patients = max(0, min(new_count, perawat.max_patients))
        
        try:
            db.add(perawat)
            db.commit()
            db.refresh(perawat)
        except Exception:
            db.rollback()
            raise
        return perawat

    def assign_patient(
        self, db: Session, *, perawat_id: int, ibu_hamil_id: int
    ) -> Optional[Perawat]:
        """Assign an Ibu Hamil to this Perawat by incrementing workload.
        
        Note: This only updates the Perawat side. Caller should also update
        the IbuHamil.perawat_id field separately.
        """
        return self.update_workload(db, perawat_id=perawat_id, increment=1)


# Singleton instance
crud_perawat = CRUDPerawat(Perawat)
