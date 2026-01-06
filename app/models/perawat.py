from sqlalchemy import Column, Integer, String, Boolean, TIMESTAMP, ForeignKey
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from ..database import Base


class Perawat(Base):
    __tablename__ = "perawat"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # Foreign Keys
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False)
    puskesmas_id = Column(Integer, ForeignKey("puskesmas.id", ondelete="CASCADE"), nullable=False, index=True)
    created_by_user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"))
    
    # Professional Info
    nip = Column(String(50), unique=True, nullable=False)
    job_title = Column(String(100), nullable=False)
    license_number = Column(String(100))
    license_document_url = Column(String(500))
    
    # Workload Management
    max_patients = Column(Integer, default=15)
    current_patients = Column(Integer, default=0)
    
    # Work Area & Location removed per FR (use Puskesmas location only)
    
    # Status
    is_available = Column(Boolean, default=True, index=True)
    is_active = Column(Boolean, default=True, index=True)
    
    # Timestamps
    created_at = Column(TIMESTAMP, server_default=func.now())
    updated_at = Column(TIMESTAMP, server_default=func.now(), onupdate=func.now())
    
    # Relationships
    user = relationship("User", foreign_keys=[user_id])
    puskesmas = relationship("Puskesmas", foreign_keys=[puskesmas_id])
    created_by = relationship("User", foreign_keys=[created_by_user_id])