from sqlalchemy import Column, Integer, String, Boolean, TIMESTAMP, ForeignKey, UniqueConstraint
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from ..database import Base


class KerabatIbuHamil(Base):
    __tablename__ = "kerabat_ibu_hamil"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # Foreign Keys
    kerabat_user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    ibu_hamil_id = Column(Integer, ForeignKey("ibu_hamil.id", ondelete="CASCADE"), nullable=False, index=True)
    
    # Relationship Info
    relation_type = Column(String(50), nullable=False)
    invite_code = Column(String(50), unique=True, index=True)
    
    # Permissions
    is_primary_contact = Column(Boolean, default=False, index=True)
    can_view_records = Column(Boolean, default=True)
    can_receive_notifications = Column(Boolean, default=True)
    
    # Timestamps
    created_at = Column(TIMESTAMP, server_default=func.now())
    updated_at = Column(TIMESTAMP, server_default=func.now(), onupdate=func.now())
    
    # Constraints
    __table_args__ = (
        UniqueConstraint('kerabat_user_id', 'ibu_hamil_id', name='uq_kerabat_ibu'),
    )
    
    # Relationships
    kerabat_user = relationship("User", foreign_keys=[kerabat_user_id])
    ibu_hamil = relationship("IbuHamil", foreign_keys=[ibu_hamil_id])