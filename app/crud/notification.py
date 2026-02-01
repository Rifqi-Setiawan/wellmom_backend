"""CRUD operations for `Notification` model."""

from __future__ import annotations

import logging
from datetime import datetime
from typing import List, Optional

from sqlalchemy import select, and_, func, update
from sqlalchemy.orm import Session

from app.crud.base import CRUDBase
from app.models.notification import Notification
from app.schemas.notification import NotificationCreate, NotificationUpdate

logger = logging.getLogger(__name__)


class CRUDNotification(CRUDBase[Notification, NotificationCreate, NotificationUpdate]):
    """CRUD operations for Notification model."""

    def get_by_user(
        self,
        db: Session,
        *,
        user_id: int,
        skip: int = 0,
        limit: int = 50,
        is_read: Optional[bool] = None,
        notification_type: Optional[str] = None,
    ) -> List[Notification]:
        """
        Get notifications for a specific user with optional filters and pagination.

        Args:
            db: Database session
            user_id: ID of the user
            skip: Number of records to skip (for pagination)
            limit: Maximum number of records to return
            is_read: Filter by read status (None = all, True = read only, False = unread only)
            notification_type: Filter by notification type (e.g., 'health_alert', 'assignment')

        Returns:
            List of Notification objects ordered by created_at DESC
        """
        try:
            conditions = [Notification.user_id == user_id]

            # Optional filter by is_read
            if is_read is not None:
                conditions.append(Notification.is_read == is_read)

            # Optional filter by notification_type
            if notification_type is not None:
                conditions.append(Notification.notification_type == notification_type)

            stmt = (
                select(Notification)
                .where(and_(*conditions))
                .order_by(Notification.created_at.desc())
                .offset(skip)
                .limit(limit)
            )
            return list(db.scalars(stmt).all())

        except Exception as e:
            logger.error(f"Failed to get notifications for user {user_id}: {str(e)}")
            return []

    def get_unread_count(self, db: Session, *, user_id: int) -> int:
        """
        Get the count of unread notifications for a user.

        Args:
            db: Database session
            user_id: ID of the user

        Returns:
            Number of unread notifications
        """
        try:
            stmt = select(func.count(Notification.id)).where(
                and_(
                    Notification.user_id == user_id,
                    Notification.is_read == False
                )
            )
            count = db.scalar(stmt) or 0
            return count

        except Exception as e:
            logger.error(f"Failed to get unread count for user {user_id}: {str(e)}")
            return 0

    def get_total_count(
        self,
        db: Session,
        *,
        user_id: int,
        is_read: Optional[bool] = None,
        notification_type: Optional[str] = None,
    ) -> int:
        """
        Get the total count of notifications for a user with optional filters.

        Args:
            db: Database session
            user_id: ID of the user
            is_read: Filter by read status (None = all)
            notification_type: Filter by notification type

        Returns:
            Total number of notifications matching the criteria
        """
        try:
            conditions = [Notification.user_id == user_id]

            if is_read is not None:
                conditions.append(Notification.is_read == is_read)

            if notification_type is not None:
                conditions.append(Notification.notification_type == notification_type)

            stmt = select(func.count(Notification.id)).where(and_(*conditions))
            count = db.scalar(stmt) or 0
            return count

        except Exception as e:
            logger.error(f"Failed to get total count for user {user_id}: {str(e)}")
            return 0

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

    def mark_all_as_read(self, db: Session, *, user_id: int) -> int:
        """
        Mark all unread notifications for a user as read.

        Uses bulk UPDATE query for better performance instead of
        fetching all records into memory.

        Args:
            db: Database session
            user_id: ID of the user

        Returns:
            Number of notifications that were marked as read
        """
        now = datetime.utcnow()

        try:
            # Use bulk UPDATE for better performance
            stmt = (
                update(Notification)
                .where(
                    and_(
                        Notification.user_id == user_id,
                        Notification.is_read == False
                    )
                )
                .values(is_read=True, read_at=now)
            )
            result = db.execute(stmt)
            db.commit()

            # rowcount gives us the number of affected rows
            return result.rowcount

        except Exception:
            db.rollback()
            raise

    # Alias for backward compatibility
    def mark_all_read(self, db: Session, *, user_id: int) -> int:
        """Alias for mark_all_as_read (backward compatibility)."""
        return self.mark_all_as_read(db, user_id=user_id)

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
