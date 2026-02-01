from sqlalchemy import Column, Integer, String, Boolean, TIMESTAMP, ForeignKey, Text, CheckConstraint, Index
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from ..database import Base


class Notification(Base):
    __tablename__ = "notifications"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # Recipient
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    
    # Notification Content
    title = Column(String(255), nullable=False)
    message = Column(Text, nullable=False)
    
    # Classification
    notification_type = Column(String(50), nullable=False, index=True)
    priority = Column(String(20), default='normal', index=True)
    
    # Status
    is_read = Column(Boolean, default=False, index=True)
    read_at = Column(TIMESTAMP)
    
    # Delivery Channels
    sent_via = Column(String(50), nullable=False)
    whatsapp_status = Column(String(50))
    
    # Related Entity
    related_entity_type = Column(String(50))
    related_entity_id = Column(Integer)
    
    # Scheduling
    scheduled_for = Column(TIMESTAMP, index=True)
    sent_at = Column(TIMESTAMP)
    
    # Timestamps
    created_at = Column(TIMESTAMP, server_default=func.now(), index=True)
    
    # Constraints and Indexes
    __table_args__ = (
        # Check constraints
        CheckConstraint(
            "notification_type IN ('checkup_reminder', 'assignment', 'health_alert', 'iot_alert', 'referral', 'transfer_update', 'system')",
            name="check_notification_type"
        ),
        CheckConstraint(
            "priority IN ('low', 'normal', 'high', 'urgent')",
            name="check_priority"
        ),
        CheckConstraint(
            "sent_via IN ('in_app', 'whatsapp', 'both')",
            name="check_sent_via"
        ),
        CheckConstraint(
            "whatsapp_status IN ('pending', 'sent', 'delivered', 'failed')",
            name="check_whatsapp_status"
        ),
        # Composite indexes for common query patterns
        Index("ix_notifications_user_unread", "user_id", "is_read", "created_at"),
        Index("ix_notifications_user_type", "user_id", "notification_type", "created_at"),
    )
    
    # Relationships
    user = relationship("User", foreign_keys=[user_id])