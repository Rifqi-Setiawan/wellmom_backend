"""CRUD operations for `Notification` model."""

from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from sqlalchemy import select, and_
from sqlalchemy.orm import Session

from app.crud.base import CRUDBase
from app.models.notification import Notification
from app.schemas.notification import NotificationCreate, NotificationUpdate


class CRUDNotification(CRUDBase[Notification, NotificationCreate, NotificationUpdate]):
    def get_by_user(
        self, db: Session, *, user_id: int, unread_only: bool = False
    ) -> List[Notification]:
        """Get notifications for a specific user, optionally filter unread only."""
        conditions = [Notification.user_id == user_id]
        
        if unread_only:
            conditions.append(Notification.is_read == False)
        
        stmt = (
            select(Notification)
            .where(and_(*conditions))
            .order_by(Notification.created_at.desc())
        )
        return db.scalars(stmt).all()

    def mark_as_read(self, db: Session, *, notification_id: int) -> Optional[Notification]:
        """Mark a notification as read."""
        notification = self.get(db, notification_id)
        if not notification:
            return None
        
        notification.is_read = True
        notification.read_at = datetime.utcnow()
        
        try:
            db.add(notification)
            db.commit()
            db.refresh(notification)
        except Exception:
            db.rollback()
            raise
        return notification

    def mark_all_read(self, db: Session, *, user_id: int) -> int:
        """Mark all notifications for a user as read.
        
        Returns the number of notifications marked.
        """
        notifications = self.get_by_user(db, user_id=user_id, unread_only=True)
        count = 0
        
        for notification in notifications:
            notification.is_read = True
            notification.read_at = datetime.utcnow()
            db.add(notification)
            count += 1
        
        try:
            db.commit()
        except Exception:
            db.rollback()
            raise
        return count

    def get_scheduled(self, db: Session) -> List[Notification]:
        """Get notifications that are scheduled but not yet sent."""
        stmt = (
            select(Notification)
            .where(
                and_(
                    Notification.scheduled_for.isnot(None),
                    Notification.sent_at.is_(None),
                )
            )
            .order_by(Notification.scheduled_for)
        )
        return db.scalars(stmt).all()

    def create_for_multiple_users(
        self, db: Session, *, user_ids: List[int], notification_in: NotificationCreate
    ) -> List[Notification]:
        """Create the same notification for multiple users.
        
        Returns list of created notification objects.
        """
        created = []
        notification_data = notification_in.model_dump(exclude={"user_id"}, exclude_unset=True)
        
        for user_id in user_ids:
            db_obj = Notification(user_id=user_id, **notification_data)
            db.add(db_obj)
            created.append(db_obj)
        
        try:
            db.commit()
            for obj in created:
                db.refresh(obj)
        except Exception:
            db.rollback()
            raise
        return created


# Singleton instance
crud_notification = CRUDNotification(Notification)
