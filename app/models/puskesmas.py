from sqlalchemy import Column, Integer, String, Boolean, TIMESTAMP, Text, ForeignKey, CheckConstraint
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from geoalchemy2 import Geography
from ..database import Base


class Puskesmas(Base):
    __tablename__ = "puskesmas"
    
    # Primary Key
    id = Column(Integer, primary_key=True, index=True)
    
    # Link to User
    admin_user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), unique=True)
    
    # Basic Info
    name = Column(String(255), nullable=False)
    code = Column(String(50), unique=True, nullable=False)
    
    # Legal Documents
    sk_number = Column(String(100), nullable=False)
    sk_document_url = Column(String(500), nullable=False)
    operational_license_number = Column(String(100), nullable=False)
    license_document_url = Column(String(500), nullable=False)
    npwp = Column(String(20))
    npwp_document_url = Column(String(500))
    
    # Accreditation
    accreditation_level = Column(String(50), default='none')
    accreditation_cert_url = Column(String(500))
    
    # Address
    address = Column(Text, nullable=False)
    kelurahan = Column(String(100))
    kecamatan = Column(String(100))
    kabupaten = Column(String(100), default='Kerinci')
    provinsi = Column(String(100), default='Jambi')
    postal_code = Column(String(5))
    
    # Contact
    phone = Column(String(20), nullable=False)
    email = Column(String(255), nullable=False)
    
    # Geolocation (PostGIS!)
    location = Column(Geography(geometry_type='POINT', srid=4326))
    building_photo_url = Column(String(500), nullable=False)
    
    # Kepala Puskesmas Info
    kepala_name = Column(String(255), nullable=False)
    kepala_nip = Column(String(18), nullable=False)
    kepala_sk_number = Column(String(100), nullable=False)
    kepala_sk_document_url = Column(String(500), nullable=False)
    kepala_nik = Column(String(16), nullable=False)
    kepala_ktp_url = Column(String(500), nullable=False)
    kepala_phone = Column(String(20), nullable=False)
    kepala_email = Column(String(255), nullable=False)
    kepala_phone_verified = Column(Boolean, default=False)
    kepala_email_verified = Column(Boolean, default=False)
    verification_photo_url = Column(String(500), nullable=False)
    
    # Operational Info
    total_perawat = Column(Integer, default=0)
    operational_hours = Column(Text)
    facilities = Column(Text)
    
    # Capacity Management
    max_patients = Column(Integer, default=100)
    current_patients = Column(Integer, default=0)
    
    # Registration & Approval
    registration_status = Column(String(50), default='pending', index=True)
    registration_date = Column(TIMESTAMP, server_default=func.now())
    approved_by_admin_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"))
    approved_at = Column(TIMESTAMP)
    rejection_reason = Column(Text)
    suspension_reason = Column(Text)
    suspended_at = Column(TIMESTAMP)
    admin_notes = Column(Text)
    is_active = Column(Boolean, default=False, index=True)
    
    # Timestamps
    created_at = Column(TIMESTAMP, server_default=func.now())
    updated_at = Column(TIMESTAMP, server_default=func.now(), onupdate=func.now())
    
    # Constraints
    __table_args__ = (
        CheckConstraint(
            "registration_status IN ('pending', 'approved', 'rejected', 'suspended')",
            name="check_puskesmas_status"
        ),
    )
    
    # Relationships
    admin_user = relationship("User", foreign_keys=[admin_user_id])
    approved_by = relationship("User", foreign_keys=[approved_by_admin_id])
    perawat_list = relationship("Perawat", back_populates="puskesmas")