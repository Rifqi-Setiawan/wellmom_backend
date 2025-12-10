"""CRUD operations for `KerabatIbuHamil` model."""

from __future__ import annotations

import secrets
from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.crud.base import CRUDBase
from app.models.kerabat import KerabatIbuHamil
from app.schemas.kerabat import KerabatCreate, KerabatUpdate


def _generate_invite_code() -> str:
    """Generate unique 8-character invite code."""
    return secrets.token_urlsafe(6).upper()[:8]


class CRUDKerabat(CRUDBase[KerabatIbuHamil, KerabatCreate, KerabatUpdate]):
    def get_by_ibu_hamil(self, db: Session, *, ibu_hamil_id: int) -> List[KerabatIbuHamil]:
        """Get all family members (Kerabat) for a specific Ibu Hamil."""
        stmt = select(KerabatIbuHamil).where(KerabatIbuHamil.ibu_hamil_id == ibu_hamil_id)
        return db.scalars(stmt).all()

    def get_by_kerabat_user(self, db: Session, *, kerabat_user_id: int) -> List[KerabatIbuHamil]:
        """Get all Ibu Hamil relationships for a specific Kerabat user."""
        stmt = select(KerabatIbuHamil).where(KerabatIbuHamil.kerabat_user_id == kerabat_user_id)
        return db.scalars(stmt).all()

    def create_with_invite_code(
        self, db: Session, *, kerabat_in: KerabatCreate
    ) -> KerabatIbuHamil:
        """Create Kerabat relationship with auto-generated unique invite code."""
        kerabat_data = kerabat_in.model_dump(exclude_unset=True)
        
        # Generate unique invite code if not provided
        if "invite_code" not in kerabat_data or not kerabat_data["invite_code"]:
            # Retry until we get a unique code
            max_attempts = 10
            for _ in range(max_attempts):
                code = _generate_invite_code()
                existing = self.verify_invite_code(db, invite_code=code)
                if not existing:
                    kerabat_data["invite_code"] = code
                    break
        
        db_obj = KerabatIbuHamil(**kerabat_data)
        try:
            db.add(db_obj)
            db.commit()
            db.refresh(db_obj)
        except Exception:
            db.rollback()
            raise
        return db_obj

    def verify_invite_code(self, db: Session, *, invite_code: str) -> Optional[KerabatIbuHamil]:
        """Verify and retrieve Kerabat relationship by invite code."""
        stmt = select(KerabatIbuHamil).where(KerabatIbuHamil.invite_code == invite_code).limit(1)
        return db.scalars(stmt).first()


# Singleton instance
crud_kerabat = CRUDKerabat(KerabatIbuHamil)
