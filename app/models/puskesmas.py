from sqlalchemy import Column, Integer, String, Boolean, TIMESTAMP, Text, ForeignKey, CheckConstraint, Float
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from geoalchemy2 import Geography
from ..database import Base


class Puskesmas(Base):
    __tablename__ = "puskesmas"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # Link to User (puskesmas admin account)
    admin_user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), unique=True)
    
    # Basic Info
    name = Column(String(255), nullable=False)  # Nama Puskesmas
    address = Column(Text, nullable=False)  # Alamat lengkap
    email = Column(String(255), nullable=False)  # Email resmi
    phone = Column(String(20), nullable=False)  # Nomor telepon
    
    # Kepala Puskesmas
    kepala_name = Column(String(255), nullable=False)
    kepala_nip = Column(String(18), nullable=False)
    
    # Legal & Tax
    npwp = Column(String(20), nullable=True)
    sk_document_url = Column(String(500), nullable=False)  # Upload SK Pendirian (PDF)
    npwp_document_url = Column(String(500), nullable=True)  # Upload Scan NPWP (PDF/JPG/PNG)
    building_photo_url = Column(String(500), nullable=False)  # Upload Foto Gedung (JPG/PNG)
    max_patients = Column(Integer, default=100)
    current_patients = Column(Integer, default=0)

    # Geolocation
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)
    location = Column(Geography(geometry_type='POINT', srid=4326))  # Optional: keep PostGIS point
    
    # Declaration
    data_truth_confirmed = Column(Boolean, default=False)
    
    # Registration & Approval
    registration_status = Column(String(30), default='draft', index=True)
    registration_date = Column(TIMESTAMP, server_default=func.now())
    approved_by_admin_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"))
    approved_at = Column(TIMESTAMP)
    rejection_reason = Column(Text)
    admin_notes = Column(Text)
    is_active = Column(Boolean, default=False, index=True)
    
    # Timestamps
    created_at = Column(TIMESTAMP, server_default=func.now())
    updated_at = Column(TIMESTAMP, server_default=func.now(), onupdate=func.now())
    
    # Constraints
    __table_args__ = (
        CheckConstraint(
            "registration_status IN ('draft', 'pending_approval', 'approved', 'rejected')",
            name="check_puskesmas_status"
        ),
    )
    
    # Relationships
    admin_user = relationship("User", foreign_keys=[admin_user_id])
    approved_by = relationship("User", foreign_keys=[approved_by_admin_id])
    perawat_list = relationship("Perawat", back_populates="puskesmas")