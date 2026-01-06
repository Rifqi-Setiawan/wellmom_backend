"""CRUD operations for `User` model."""

from __future__ import annotations

from typing import List, Optional

from passlib.context import CryptContext
from sqlalchemy import select
from sqlalchemy.orm import Session
import secrets

from app.crud.base import CRUDBase
from app.models.user import User
from app.schemas.user import UserCreate, UserUpdate


# Use PBKDF2 by default to avoid local bcrypt backend issues; keep bcrypt for legacy hashes
pwd_context = CryptContext(schemes=["pbkdf2_sha256", "bcrypt"], deprecated="auto")


def _normalize_phone(phone: str) -> str:
    """Normalize phone to +62 format when starting with 0; otherwise return as-is."""
    if phone.startswith("0"):
        return "+62" + phone[1:]
    return phone


def verify_password(plain_password: str, hashed_password: str) -> bool:
    try:
        return pwd_context.verify(plain_password, hashed_password)
    except ValueError:
        # Return False if the hash scheme is unsupported in this environment
        return False


def get_password_hash(password: str) -> str:
    try:
        return pwd_context.hash(password)
    except ValueError:
        # Fallback to PBKDF2 if bcrypt backend is unavailable
        fallback_ctx = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")
        return fallback_ctx.hash(password)


class CRUDUser(CRUDBase[User, UserCreate, UserUpdate]):
    def get_by_phone(self, db: Session, phone: str) -> Optional[User]:
        phone_norm = _normalize_phone(phone)
        stmt = select(User).where(User.phone == phone_norm).limit(1)
        return db.scalars(stmt).first()

    def get_by_email(self, db: Session, email: Optional[str]) -> Optional[User]:
        if not email:
            return None
        stmt = select(User).where(User.email == email).limit(1)
        return db.scalars(stmt).first()

    def create_user(self, db: Session, *, user_in: UserCreate) -> User:
        user_data = user_in.model_dump(exclude_unset=True)
        raw_password = user_data.pop("password")
        user_data["password_hash"] = get_password_hash(raw_password)
        user_data["phone"] = _normalize_phone(user_data["phone"])

        db_obj = User(**user_data)
        try:
            db.add(db_obj)
            db.commit()
            db.refresh(db_obj)
        except Exception:
            db.rollback()
            raise
        return db_obj

    def authenticate(self, db: Session, *, phone: str, password: str) -> Optional[User]:
        user = self.get_by_phone(db, phone)
        if not user:
            return None
        if not verify_password(password, user.password_hash):
            return None
        return user

    def update_password(self, db: Session, *, user_id: int, new_password: str) -> Optional[User]:
        user = self.get(db, user_id)
        if not user:
            return None
        user.password_hash = get_password_hash(new_password)
        try:
            db.add(user)
            db.commit()
            db.refresh(user)
        except Exception:
            db.rollback()
            raise
        return user

    def create_verification_token(self, db: Session, *, user_id: int) -> Optional[str]:
        """Generate and store a verification token for the user."""
        user = self.get(db, user_id)
        if not user:
            return None
        token = secrets.token_urlsafe(32)
        user.verification_token = token
        try:
            db.add(user)
            db.commit()
            db.refresh(user)
        except Exception:
            db.rollback()
            raise
        return token

    def verify_by_token(self, db: Session, *, token: str) -> Optional[User]:
        """Verify user using a stored verification token."""
        stmt = select(User).where(User.verification_token == token).limit(1)
        user = db.scalars(stmt).first()
        if not user:
            return None
        user.is_verified = True
        user.verification_token = None
        try:
            db.add(user)
            db.commit()
            db.refresh(user)
        except Exception:
            db.rollback()
            raise
        return user

    def verify_user(self, db: Session, *, user_id: int) -> Optional[User]:
        user = self.get(db, user_id)
        if not user:
            return None
        user.is_verified = True
        try:
            db.add(user)
            db.commit()
            db.refresh(user)
        except Exception:
            db.rollback()
            raise
        return user

    def get_by_role(self, db: Session, *, role: str) -> List[User]:
        stmt = select(User).where(User.role == role)
        return db.scalars(stmt).all()

    def deactivate(self, db: Session, *, user_id: int) -> Optional[User]:
        user = self.get(db, user_id)
        if not user:
            return None
        if hasattr(user, "is_active"):
            user.is_active = False
        try:
            db.add(user)
            db.commit()
            db.refresh(user)
        except Exception:
            db.rollback()
            raise
        return user


# Singleton instance
crud_user = CRUDUser(User)
