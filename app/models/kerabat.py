from sqlalchemy import Column, Integer, String, Boolean, TIMESTAMP, ForeignKey, UniqueConstraint
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from ..database import Base


class KerabatIbuHamil(Base):
    __tablename__ = "kerabat_ibu_hamil"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # Foreign Keys
    kerabat_user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=True, index=True)  # Nullable karena belum ada user saat generate invite
    ibu_hamil_id = Column(Integer, ForeignKey("ibu_hamil.id", ondelete="CASCADE"), nullable=False, index=True)
    
    # Relationship Info
    relation_type = Column(String(50), nullable=True)  # Nullable karena akan diisi setelah kerabat login
    invite_code = Column(String(50), unique=True, index=True)
    invite_code_created_at = Column(TIMESTAMP, server_default=func.now())  # Waktu invitation code dibuat
    invite_code_expires_at = Column(TIMESTAMP, nullable=True)  # Waktu expiration (24 jam dari created_at)
    
    # Permissions
    is_primary_contact = Column(Boolean, default=False, index=True)
    can_view_records = Column(Boolean, default=True)
    can_receive_notifications = Column(Boolean, default=True)
    
    # Timestamps
    created_at = Column(TIMESTAMP, server_default=func.now())
    updated_at = Column(TIMESTAMP, server_default=func.now(), onupdate=func.now())
    
    # Constraints
    # Note: kerabat_user_id bisa null saat generate invite, jadi constraint hanya berlaku jika keduanya tidak null
    # UniqueConstraint akan di-handle di application layer untuk mencegah duplicate
    __table_args__ = (
        # Partial unique constraint: hanya jika kerabat_user_id tidak null
        # Akan di-handle di application layer karena SQLAlchemy tidak support partial unique constraint dengan mudah
    )
    
    # Relationships
    kerabat_user = relationship("User", foreign_keys=[kerabat_user_id])
    ibu_hamil = relationship("IbuHamil", foreign_keys=[ibu_hamil_id])