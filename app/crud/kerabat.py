"""CRUD operations for `KerabatIbuHamil` model."""

from __future__ import annotations

import secrets
from datetime import datetime, timedelta
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
                existing = self.get_by_invite_code(db, invite_code=code)
                if not existing:
                    kerabat_data["invite_code"] = code
                    break
        
        # Set expiration time (24 hours from now)
        now = datetime.utcnow()
        kerabat_data["invite_code_created_at"] = now
        kerabat_data["invite_code_expires_at"] = now + timedelta(hours=24)
        
        db_obj = KerabatIbuHamil(**kerabat_data)
        try:
            db.add(db_obj)
            db.commit()
            db.refresh(db_obj)
        except Exception:
            db.rollback()
            raise
        return db_obj

    def get_by_invite_code(self, db: Session, *, invite_code: str) -> Optional[KerabatIbuHamil]:
        """Get Kerabat relationship by invite code (without expiration check)."""
        stmt = select(KerabatIbuHamil).where(KerabatIbuHamil.invite_code == invite_code).limit(1)
        return db.scalars(stmt).first()

    def verify_invite_code(self, db: Session, *, invite_code: str) -> Optional[KerabatIbuHamil]:
        """Verify and retrieve Kerabat relationship by invite code (with expiration check)."""
        kerabat = self.get_by_invite_code(db, invite_code=invite_code)
        if not kerabat:
            return None
        
        # Check if code is expired
        if kerabat.invite_code_expires_at and kerabat.invite_code_expires_at < datetime.utcnow():
            return None
        
        # Check if already used (has user_id)
        if kerabat.kerabat_user_id is not None:
            return None
        
        return kerabat
    
    def generate_invite_code_for_ibu_hamil(
        self, db: Session, *, ibu_hamil_id: int
    ) -> KerabatIbuHamil:
        """Generate new invitation code for ibu hamil (creates new KerabatIbuHamil record)."""
        # Generate unique invite code
        max_attempts = 10
        code = None
        for _ in range(max_attempts):
            code = _generate_invite_code()
            existing = self.get_by_invite_code(db, invite_code=code)
            if not existing:
                break
        
        if not code:
            raise ValueError("Failed to generate unique invite code")
        
        # Set expiration time (24 hours from now)
        now = datetime.utcnow()
        
        # Create new KerabatIbuHamil record with invite code
        db_obj = KerabatIbuHamil(
            ibu_hamil_id=ibu_hamil_id,
            kerabat_user_id=None,  # Will be set when kerabat accepts invitation
            relation_type=None,  # Will be set when kerabat completes profile
            invite_code=code,
            invite_code_created_at=now,
            invite_code_expires_at=now + timedelta(hours=24),
            can_view_records=True,
            can_receive_notifications=True,
        )
        try:
            db.add(db_obj)
            db.commit()
            db.refresh(db_obj)
        except Exception:
            db.rollback()
            raise
        return db_obj
    
    def check_duplicate_kerabat(self, db: Session, *, kerabat_user_id: int, ibu_hamil_id: int) -> Optional[KerabatIbuHamil]:
        """Check if kerabat-user relationship already exists."""
        stmt = select(KerabatIbuHamil).where(
            KerabatIbuHamil.kerabat_user_id == kerabat_user_id,
            KerabatIbuHamil.ibu_hamil_id == ibu_hamil_id
        ).limit(1)
        return db.scalars(stmt).first()


# Singleton instance
crud_kerabat = CRUDKerabat(KerabatIbuHamil)
