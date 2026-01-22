from sqlalchemy import Column, Integer, String, Boolean, TIMESTAMP, ForeignKey
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from ..database import Base


class Perawat(Base):
    __tablename__ = "perawat"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # Foreign Keys
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=True)
    puskesmas_id = Column(Integer, ForeignKey("puskesmas.id", ondelete="CASCADE"), nullable=False, index=True)
    
    # Data Perawat
    nama_lengkap = Column(String(255), nullable=False)
    email = Column(String(255), unique=True, nullable=False, index=True)
    nomor_hp = Column(String(20), nullable=False)
    nip = Column(String(50), unique=True, nullable=False, index=True)
    profile_photo_url = Column(String(500), nullable=True)
    current_patients = Column(Integer, default=0)

    # Status Akun
    is_active = Column(Boolean, default=True, index=True)
    
    # Timestamps
    created_at = Column(TIMESTAMP, server_default=func.now())
    updated_at = Column(TIMESTAMP, server_default=func.now(), onupdate=func.now())
    
    # Relationships
    puskesmas = relationship("Puskesmas", back_populates="perawat_list")
    ibu_hamil_list = relationship("IbuHamil", back_populates="perawat", foreign_keys="[IbuHamil.perawat_id]")