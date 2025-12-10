"""CRUD operations for `TransferRequest` model."""

from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.crud.base import CRUDBase
from app.models.transfer_request import TransferRequest
from app.schemas.transfer_request import TransferRequestCreate, TransferRequestUpdate


class CRUDTransferRequest(CRUDBase[TransferRequest, TransferRequestCreate, TransferRequestUpdate]):
    def get_pending(self, db: Session) -> List[TransferRequest]:
        """Get all pending transfer requests."""
        stmt = (
            select(TransferRequest)
            .where(TransferRequest.status == "pending")
            .order_by(TransferRequest.created_at.desc())
        )
        return db.scalars(stmt).all()

    def get_by_requester(self, db: Session, *, user_id: int) -> List[TransferRequest]:
        """Get all transfer requests by a specific requester user."""
        stmt = (
            select(TransferRequest)
            .where(TransferRequest.requester_user_id == user_id)
            .order_by(TransferRequest.created_at.desc())
        )
        return db.scalars(stmt).all()

    def approve(
        self, db: Session, *, request_id: int, reviewer_id: int
    ) -> Optional[TransferRequest]:
        """Approve a transfer request."""
        transfer_request = self.get(db, request_id)
        if not transfer_request:
            return None
        
        transfer_request.status = "approved"
        transfer_request.reviewed_by_user_id = reviewer_id
        transfer_request.reviewed_at = datetime.utcnow()
        transfer_request.rejection_reason = None
        
        try:
            db.add(transfer_request)
            db.commit()
            db.refresh(transfer_request)
        except Exception:
            db.rollback()
            raise
        return transfer_request

    def reject(
        self, db: Session, *, request_id: int, reviewer_id: int, reason: str
    ) -> Optional[TransferRequest]:
        """Reject a transfer request with a reason."""
        transfer_request = self.get(db, request_id)
        if not transfer_request:
            return None
        
        transfer_request.status = "rejected"
        transfer_request.reviewed_by_user_id = reviewer_id
        transfer_request.reviewed_at = datetime.utcnow()
        transfer_request.rejection_reason = reason
        
        try:
            db.add(transfer_request)
            db.commit()
            db.refresh(transfer_request)
        except Exception:
            db.rollback()
            raise
        return transfer_request

    def get_by_type(self, db: Session, *, requester_type: str) -> List[TransferRequest]:
        """Get transfer requests filtered by requester type (perawat or ibu_hamil)."""
        stmt = (
            select(TransferRequest)
            .where(TransferRequest.requester_type == requester_type)
            .order_by(TransferRequest.created_at.desc())
        )
        return db.scalars(stmt).all()


# Singleton instance
crud_transfer_request = CRUDTransferRequest(TransferRequest)
