"""Service layer for notification management in WellMom."""

import logging
from datetime import datetime
from typing import Optional, List

from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import select, func, update

from app.models.notification import Notification
from app.models.ibu_hamil import IbuHamil
from app.schemas.notification import NotificationCreate
from app.services.firebase_service import firebase_service

logger = logging.getLogger(__name__)


class NotificationService:
    """
    Service for managing notifications.

    Provides centralized methods for creating, reading, and managing
    notifications across the WellMom application.
    """

    # Risk level notification configurations
    RISK_LEVEL_CONFIG = {
        "rendah": {
            "title": "✅ Kondisi Kehamilan Normal",
            "message_template": (
                "Hasil assessment dari {perawat_name} menunjukkan kondisi kehamilan Anda dalam kategori RISIKO RENDAH. "
                "Tetap jaga kesehatan dengan pola makan bergizi, istirahat cukup, dan rutin kontrol kehamilan."
            ),
            "priority": "normal",
            "sent_via": "in_app",
        },
        "sedang": {
            "title": "⚠️ Perhatian: Risiko Kehamilan Sedang",
            "message_template": (
                "Hasil assessment dari {perawat_name} menunjukkan kondisi kehamilan Anda dalam kategori RISIKO SEDANG. "
                "Harap lebih waspada dan segera hubungi perawat jika mengalami keluhan. "
                "Pastikan untuk rutin melakukan pemeriksaan sesuai jadwal."
            ),
            "priority": "high",
            "sent_via": "in_app",
        },
        "tinggi": {
            "title": "🚨 PENTING: Risiko Kehamilan Tinggi",
            "message_template": (
                "Hasil assessment dari {perawat_name} menunjukkan kondisi kehamilan Anda dalam kategori RISIKO TINGGI. "
                "SEGERA hubungi perawat atau kunjungi puskesmas jika mengalami keluhan apapun. "
                "Ikuti semua anjuran perawat dan jangan lewatkan jadwal pemeriksaan."
            ),
            "priority": "urgent",
            "sent_via": "both",
        },
    }

    def create_notification(
        self,
        db: Session,
        *,
        user_id: int,
        title: str,
        message: str,
        notification_type: str,
        priority: str = "normal",
        sent_via: str = "in_app",
        related_entity_type: Optional[str] = None,
        related_entity_id: Optional[int] = None,
        scheduled_for: Optional[datetime] = None,
    ) -> Notification:
        """
        Create a new notification.

        Args:
            db: Database session
            user_id: ID of the user to receive the notification
            title: Notification title
            message: Notification message content
            notification_type: Type of notification (checkup_reminder, assignment,
                             health_alert, iot_alert, referral, transfer_update, system, new_message)
            priority: Priority level (low, normal, high, urgent)
            sent_via: Delivery channel (in_app, whatsapp, both)
            related_entity_type: Optional related entity type
            related_entity_id: Optional related entity ID
            scheduled_for: Optional scheduled delivery time

        Returns:
            Notification: The created notification object

        Raises:
            HTTPException: If validation fails or database error occurs
        """
        # Validate notification_type
        valid_types = {
            "checkup_reminder", "assignment", "health_alert",
            "iot_alert", "referral", "transfer_update", "system", "new_message"
        }
        if notification_type not in valid_types:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid notification_type. Must be one of: {sorted(valid_types)}"
            )

        # Validate priority
        valid_priorities = {"low", "normal", "high", "urgent"}
        if priority not in valid_priorities:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid priority. Must be one of: {sorted(valid_priorities)}"
            )

        # Validate sent_via
        valid_channels = {"in_app", "whatsapp", "both"}
        if sent_via not in valid_channels:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid sent_via. Must be one of: {sorted(valid_channels)}"
            )

        try:
            notification = Notification(
                user_id=user_id,
                title=title,
                message=message,
                notification_type=notification_type,
                priority=priority,
                sent_via=sent_via,
                related_entity_type=related_entity_type,
                related_entity_id=related_entity_id,
                scheduled_for=scheduled_for,
                is_read=False,
            )

            db.add(notification)
            db.commit()
            db.refresh(notification)

            logger.info(
                f"Notification created: id={notification.id}, "
                f"user_id={user_id}, type={notification_type}, priority={priority}"
            )

            # Send push notification via Firebase
            try:
                firebase_service.send_notification_to_user(
                    db=db,
                    user_id=user_id,
                    title=title,
                    body=message,
                    data={
                        "notification_id": str(notification.id),
                        "notification_type": notification_type,
                        "priority": priority,
                        "related_entity_type": related_entity_type or "",
                        "related_entity_id": str(related_entity_id) if related_entity_id else "",
                    },
                    priority=priority,
                )
            except Exception as e:
                logger.warning(f"Failed to send push notification: {str(e)}")
                # Don't fail the whole operation if push notification fails

            return notification

        except Exception as e:
            db.rollback()
            logger.error(f"Failed to create notification: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Gagal membuat notifikasi: {str(e)}"
            )

    def create_risk_level_notification(
        self,
        db: Session,
        *,
        ibu_hamil_id: int,
        risk_level: str,
        perawat_name: str,
    ) -> Optional[Notification]:
        """
        Create a notification for risk level assessment result.

        Args:
            db: Database session
            ibu_hamil_id: ID of the ibu hamil
            risk_level: Risk level (rendah, sedang, tinggi)
            perawat_name: Name of the perawat who performed the assessment

        Returns:
            Notification: The created notification object, or None if ibu_hamil not found

        Raises:
            HTTPException: If risk_level is invalid or database error occurs
        """
        # Validate risk_level
        if risk_level not in self.RISK_LEVEL_CONFIG:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid risk_level. Must be one of: {sorted(self.RISK_LEVEL_CONFIG.keys())}"
            )

        # Get ibu_hamil to find user_id
        ibu_hamil = db.get(IbuHamil, ibu_hamil_id)
        if not ibu_hamil:
            logger.warning(f"IbuHamil not found: id={ibu_hamil_id}")
            return None

        if not ibu_hamil.user_id:
            logger.warning(f"IbuHamil has no user_id: id={ibu_hamil_id}")
            return None

        # Get configuration for this risk level
        config = self.RISK_LEVEL_CONFIG[risk_level]

        # Format message with perawat name
        message = config["message_template"].format(perawat_name=perawat_name)

        # Create notification
        notification = self.create_notification(
            db,
            user_id=ibu_hamil.user_id,
            title=config["title"],
            message=message,
            notification_type="health_alert",
            priority=config["priority"],
            sent_via=config["sent_via"],
            related_entity_type="ibu_hamil",
            related_entity_id=ibu_hamil_id,
        )

        logger.info(
            f"Risk level notification created: ibu_hamil_id={ibu_hamil_id}, "
            f"risk_level={risk_level}, notification_id={notification.id}"
        )

        return notification

    def create_new_message_notification(
        self,
        db: Session,
        *,
        conversation_id: int,
        sender_name: str,
        recipient_user_id: int,
    ) -> Notification:
        """
        Create a notification for a new chat message.

        Args:
            db: Database session
            conversation_id: ID of the conversation
            sender_name: Name of the message sender
            recipient_user_id: User ID of the message recipient

        Returns:
            Notification: The created notification object
        """
        title = f"Pesan baru dari {sender_name}"
        message = "Anda menerima pesan baru. Tap untuk melihat."

        notification = self.create_notification(
            db,
            user_id=recipient_user_id,
            title=title,
            message=message,
            notification_type="new_message",
            priority="normal",
            sent_via="in_app",
            related_entity_type="conversation",
            related_entity_id=conversation_id,
        )

        logger.info(
            f"New message notification created: conversation_id={conversation_id}, "
            f"recipient_user_id={recipient_user_id}, notification_id={notification.id}"
        )

        return notification

    def mark_as_read(
        self,
        db: Session,
        *,
        notification_id: int,
        user_id: int,
    ) -> Notification:
        """
        Mark a notification as read.

        Args:
            db: Database session
            notification_id: ID of the notification to mark as read
            user_id: ID of the user (for authorization check)

        Returns:
            Notification: The updated notification object

        Raises:
            HTTPException: If notification not found or user not authorized
        """
        notification = db.get(Notification, notification_id)

        if not notification:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Notifikasi tidak ditemukan."
            )

        # Authorization check
        if notification.user_id != user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Anda tidak memiliki akses ke notifikasi ini."
            )

        # Already read, return as is
        if notification.is_read:
            return notification

        try:
            notification.is_read = True
            notification.read_at = datetime.utcnow()

            db.add(notification)
            db.commit()
            db.refresh(notification)

            logger.info(f"Notification marked as read: id={notification_id}, user_id={user_id}")

            return notification

        except Exception as e:
            db.rollback()
            logger.error(f"Failed to mark notification as read: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Gagal menandai notifikasi sebagai dibaca: {str(e)}"
            )

    def mark_all_as_read(
        self,
        db: Session,
        *,
        user_id: int,
    ) -> int:
        """
        Mark all notifications for a user as read.

        Uses bulk UPDATE query for better performance instead of
        fetching all records into memory.

        Args:
            db: Database session
            user_id: ID of the user

        Returns:
            int: Number of notifications marked as read
        """
        try:
            now = datetime.utcnow()

            # Use bulk UPDATE for better performance
            stmt = (
                update(Notification)
                .where(
                    Notification.user_id == user_id,
                    Notification.is_read == False
                )
                .values(is_read=True, read_at=now)
            )
            result = db.execute(stmt)
            db.commit()

            count = result.rowcount
            logger.info(f"Marked {count} notifications as read for user_id={user_id}")

            return count

        except Exception as e:
            db.rollback()
            logger.error(f"Failed to mark all notifications as read: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Gagal menandai semua notifikasi sebagai dibaca: {str(e)}"
            )

    def get_unread_count(
        self,
        db: Session,
        *,
        user_id: int,
    ) -> int:
        """
        Get the count of unread notifications for a user.

        Args:
            db: Database session
            user_id: ID of the user

        Returns:
            int: Number of unread notifications
        """
        try:
            stmt = select(func.count(Notification.id)).where(
                Notification.user_id == user_id,
                Notification.is_read == False
            )
            count = db.scalar(stmt) or 0

            return count

        except Exception as e:
            logger.error(f"Failed to get unread count: {str(e)}")
            return 0

    def get_notifications(
        self,
        db: Session,
        *,
        user_id: int,
        unread_only: bool = False,
        skip: int = 0,
        limit: int = 50,
    ) -> List[Notification]:
        """
        Get notifications for a user with pagination.

        Args:
            db: Database session
            user_id: ID of the user
            unread_only: If True, only return unread notifications
            skip: Number of records to skip (for pagination)
            limit: Maximum number of records to return

        Returns:
            List[Notification]: List of notification objects
        """
        try:
            stmt = select(Notification).where(Notification.user_id == user_id)

            if unread_only:
                stmt = stmt.where(Notification.is_read == False)

            stmt = stmt.order_by(Notification.created_at.desc())
            stmt = stmt.offset(skip).limit(limit)

            notifications = db.scalars(stmt).all()

            return list(notifications)

        except Exception as e:
            logger.error(f"Failed to get notifications: {str(e)}")
            return []

    def delete_notification(
        self,
        db: Session,
        *,
        notification_id: int,
        user_id: int,
    ) -> bool:
        """
        Delete a notification.

        Args:
            db: Database session
            notification_id: ID of the notification to delete
            user_id: ID of the user (for authorization check)

        Returns:
            bool: True if deleted successfully

        Raises:
            HTTPException: If notification not found or user not authorized
        """
        notification = db.get(Notification, notification_id)

        if not notification:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Notifikasi tidak ditemukan."
            )

        # Authorization check
        if notification.user_id != user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Anda tidak memiliki akses ke notifikasi ini."
            )

        try:
            db.delete(notification)
            db.commit()

            logger.info(f"Notification deleted: id={notification_id}, user_id={user_id}")

            return True

        except Exception as e:
            db.rollback()
            logger.error(f"Failed to delete notification: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Gagal menghapus notifikasi: {str(e)}"
            )


# Singleton instance
notification_service = NotificationService()
