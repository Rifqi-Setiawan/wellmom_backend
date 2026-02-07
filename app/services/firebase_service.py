"""Firebase Cloud Messaging service for WellMom push notifications."""

import logging
from typing import Optional, List, Dict, Any

import firebase_admin
from firebase_admin import credentials, messaging

from app.config import settings

logger = logging.getLogger(__name__)


class FirebaseService:
    """
    Service for sending push notifications via Firebase Cloud Messaging.

    Handles initialization of Firebase Admin SDK and provides methods
    for sending notifications to individual devices, multiple devices,
    and topic subscribers.
    """

    def __init__(self):
        self._app: Optional[firebase_admin.App] = None
        self._initialized: bool = False

    def initialize(self) -> bool:
        """
        Initialize Firebase Admin SDK with credentials from config.

        Returns:
            bool: True if initialization succeeded, False otherwise.
        """
        if self._initialized:
            logger.debug("Firebase already initialized, skipping.")
            return True

        if not settings.FIREBASE_ENABLED:
            logger.info("Firebase is disabled via FIREBASE_ENABLED=false.")
            return False

        try:
            cred = credentials.Certificate(settings.FIREBASE_CREDENTIALS_PATH)
            self._app = firebase_admin.initialize_app(cred, {
                "projectId": settings.FIREBASE_PROJECT_ID,
            })
            self._initialized = True
            logger.info(
                f"Firebase initialized successfully for project: {settings.FIREBASE_PROJECT_ID}"
            )
            return True
        except FileNotFoundError:
            logger.error(
                f"Firebase credentials file not found: {settings.FIREBASE_CREDENTIALS_PATH}"
            )
            return False
        except Exception as e:
            logger.error(f"Failed to initialize Firebase: {e}")
            return False

    def is_initialized(self) -> bool:
        """Check whether Firebase Admin SDK is ready."""
        return self._initialized

    def _build_message(
        self,
        title: str,
        body: str,
        token: Optional[str] = None,
        topic: Optional[str] = None,
        data: Optional[Dict[str, str]] = None,
        priority: str = "high",
        image_url: Optional[str] = None,
    ) -> messaging.Message:
        """Build an FCM Message with Android and APNS (iOS) config."""
        android_priority = "high" if priority == "high" else "normal"

        android_config = messaging.AndroidConfig(
            priority=android_priority,
            notification=messaging.AndroidNotification(
                title=title,
                body=body,
                icon="ic_notification",
                color="#FF6B9D",
                sound="default",
                channel_id="wellmom_notifications",
                image=image_url,
            ),
        )

        apns_config = messaging.APNSConfig(
            payload=messaging.APNSPayload(
                aps=messaging.Aps(
                    alert=messaging.ApsAlert(title=title, body=body),
                    sound="default",
                    badge=1,
                    mutable_content=True,
                ),
            ),
        )

        notification = messaging.Notification(
            title=title,
            body=body,
            image=image_url,
        )

        return messaging.Message(
            notification=notification,
            android=android_config,
            apns=apns_config,
            data=data,
            token=token,
            topic=topic,
        )

    def send_notification(
        self,
        token: str,
        title: str,
        body: str,
        data: Optional[Dict[str, str]] = None,
        priority: str = "high",
        image_url: Optional[str] = None,
        db: Optional[Any] = None,
        user_id: Optional[int] = None,
    ) -> Optional[str]:
        """
        Send a push notification to a single device.

        Args:
            token: FCM device registration token.
            title: Notification title.
            body: Notification body text.
            data: Optional data payload for deep linking.
            priority: "high" or "normal".
            image_url: Optional image URL for rich notifications.
            db: Optional database session for token cleanup on error.
            user_id: Optional user ID for token cleanup on error.

        Returns:
            Message ID string on success, None on failure.
        """
        if not self._initialized:
            logger.warning("Firebase not initialized. Call initialize() first.")
            return None

        try:
            message = self._build_message(
                title=title,
                body=body,
                token=token,
                data=data,
                priority=priority,
                image_url=image_url,
            )
            message_id = messaging.send(message)
            logger.info(f"FCM sent to token={token[:20]}...: message_id={message_id}")
            return message_id

        except messaging.UnregisteredError:
            logger.warning(f"FCM token unregistered (device removed app): {token[:20]}...")
            # Remove invalid token from database if db and user_id provided
            if db and user_id:
                self._remove_invalid_token(db, user_id, token)
            return None
        except messaging.InvalidArgumentError as e:
            logger.error(f"FCM invalid token argument: {e}")
            # Remove invalid token from database if db and user_id provided
            if db and user_id:
                self._remove_invalid_token(db, user_id, token)
            return None
        except ValueError as e:
            logger.error(f"FCM invalid argument: {e}")
            return None
        except Exception as e:
            logger.error(f"FCM send failed: {e}")
            return None

    def _remove_invalid_token(self, db: Any, user_id: int, token: str) -> None:
        """
        Remove invalid FCM token from user's record in database.

        Args:
            db: Database session
            user_id: User ID whose token should be removed
            token: The invalid token (for logging)
        """
        try:
            from app.models.user import User

            user = db.query(User).filter(User.id == user_id).first()
            if user and user.fcm_token == token:
                user.fcm_token = None
                user.fcm_token_updated_at = None
                db.add(user)
                db.commit()
                logger.info(f"Removed invalid FCM token for user_id={user_id}")
        except Exception as e:
            logger.error(f"Failed to remove invalid token for user_id={user_id}: {e}")
            db.rollback()

    def send_notification_to_user(
        self,
        db,
        user_id: int,
        title: str,
        body: str,
        data: Optional[Dict[str, str]] = None,
        priority: str = "high",
    ) -> Optional[str]:
        """
        Send a push notification to a user by looking up their FCM token.

        Args:
            db: SQLAlchemy database session.
            user_id: Target user ID.
            title: Notification title.
            body: Notification body text.
            data: Optional data payload for deep linking.
            priority: "high" or "normal".

        Returns:
            Message ID string on success, None on failure.
        """
        if not self._initialized:
            logger.warning("Firebase not initialized. Call initialize() first.")
            return None

        try:
            from app.models.user import User

            user = db.query(User).filter(User.id == user_id).first()
            if not user:
                logger.warning(f"User not found: user_id={user_id}")
                return None

            fcm_token = getattr(user, "fcm_token", None)
            if not fcm_token:
                logger.debug(f"No FCM token for user_id={user_id}, skipping push.")
                return None

            return self.send_notification(
                token=fcm_token,
                title=title,
                body=body,
                data=data,
                priority=priority,
                db=db,
                user_id=user_id,
            )

        except Exception as e:
            logger.error(f"Failed to send notification to user_id={user_id}: {e}")
            return None

    def send_multicast(
        self,
        tokens: List[str],
        title: str,
        body: str,
        data: Optional[Dict[str, str]] = None,
        priority: str = "high",
        image_url: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Send a push notification to multiple devices at once.

        Args:
            tokens: List of FCM device tokens (max 500 per call).
            title: Notification title.
            body: Notification body text.
            data: Optional data payload.
            priority: "high" or "normal".
            image_url: Optional image URL.

        Returns:
            Dict with "success_count", "failure_count", and "failed_tokens".
        """
        result = {"success_count": 0, "failure_count": 0, "failed_tokens": []}

        if not self._initialized:
            logger.warning("Firebase not initialized. Call initialize() first.")
            return result

        if not tokens:
            return result

        android_priority = "high" if priority == "high" else "normal"

        try:
            message = messaging.MulticastMessage(
                notification=messaging.Notification(
                    title=title,
                    body=body,
                    image=image_url,
                ),
                android=messaging.AndroidConfig(
                    priority=android_priority,
                    notification=messaging.AndroidNotification(
                        sound="default",
                        channel_id="wellmom_notifications",
                    ),
                ),
                apns=messaging.APNSConfig(
                    payload=messaging.APNSPayload(
                        aps=messaging.Aps(sound="default", badge=1),
                    ),
                ),
                data=data,
                tokens=tokens,
            )

            response = messaging.send_each_for_multicast(message)
            result["success_count"] = response.success_count
            result["failure_count"] = response.failure_count

            for idx, send_response in enumerate(response.responses):
                if not send_response.success:
                    result["failed_tokens"].append(tokens[idx])
                    logger.warning(
                        f"FCM multicast failed for token={tokens[idx][:20]}...: "
                        f"{send_response.exception}"
                    )

            logger.info(
                f"FCM multicast: {result['success_count']} success, "
                f"{result['failure_count']} failed out of {len(tokens)} tokens"
            )
            return result

        except Exception as e:
            logger.error(f"FCM multicast failed: {e}")
            return result

    def send_topic_notification(
        self,
        topic: str,
        title: str,
        body: str,
        data: Optional[Dict[str, str]] = None,
        priority: str = "high",
        image_url: Optional[str] = None,
    ) -> Optional[str]:
        """
        Send a push notification to all devices subscribed to a topic.

        Args:
            topic: Topic name (e.g. "health_tips", "puskesmas_123").
            title: Notification title.
            body: Notification body text.
            data: Optional data payload.
            priority: "high" or "normal".
            image_url: Optional image URL.

        Returns:
            Message ID string on success, None on failure.
        """
        if not self._initialized:
            logger.warning("Firebase not initialized. Call initialize() first.")
            return None

        try:
            message = self._build_message(
                title=title,
                body=body,
                topic=topic,
                data=data,
                priority=priority,
                image_url=image_url,
            )
            message_id = messaging.send(message)
            logger.info(f"FCM topic notification sent: topic={topic}, message_id={message_id}")
            return message_id

        except Exception as e:
            logger.error(f"FCM topic send failed for topic={topic}: {e}")
            return None

    def subscribe_to_topic(
        self,
        tokens: List[str],
        topic: str,
    ) -> Dict[str, Any]:
        """
        Subscribe devices to a topic.

        Args:
            tokens: List of FCM device tokens.
            topic: Topic name to subscribe to.

        Returns:
            Dict with "success_count" and "failure_count".
        """
        result = {"success_count": 0, "failure_count": 0}

        if not self._initialized:
            logger.warning("Firebase not initialized. Call initialize() first.")
            return result

        if not tokens:
            return result

        try:
            response = messaging.subscribe_to_topic(tokens, topic)
            result["success_count"] = response.success_count
            result["failure_count"] = response.failure_count

            logger.info(
                f"FCM topic subscribe: topic={topic}, "
                f"{result['success_count']} success, {result['failure_count']} failed"
            )
            return result

        except Exception as e:
            logger.error(f"FCM topic subscribe failed for topic={topic}: {e}")
            return result


# Singleton instance
firebase_service = FirebaseService()
