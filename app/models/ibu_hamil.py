from sqlalchemy import Column, Integer, String, Boolean, TIMESTAMP, ForeignKey, Float, Date, Text, CheckConstraint
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from geoalchemy2 import Geography
from ..database import Base


class IbuHamil(Base):
    __tablename__ = "ibu_hamil"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # Foreign Keys (Dual Assignment)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False)
    puskesmas_id = Column(Integer, ForeignKey("puskesmas.id", ondelete="SET NULL"), index=True)
    perawat_id = Column(Integer, ForeignKey("perawat.id", ondelete="SET NULL"), index=True)
    assigned_by_user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"))
    
    # Identitas Pribadi
    nama_lengkap = Column(String(255), nullable=False)
    nik = Column(String(16), unique=True, nullable=False, index=True)
    date_of_birth = Column(Date, nullable=False)
    age = Column(Integer)
    blood_type = Column(String(5))
    profile_photo_url = Column(String(500), nullable=True)  # Foto profil
    
    # Data Kehamilan
    last_menstrual_period = Column(Date)  # HPHT
    estimated_due_date = Column(Date)  # HPL
    usia_kehamilan = Column(Integer)  # Usia kehamilan (minggu/bulan)
    kehamilan_ke = Column(Integer, default=1)  # Kehamilan ke-berapa
    jumlah_anak = Column(Integer, default=0)  # Jumlah anak yang telah dilahirkan
    miscarriage_number = Column(Integer, default=0)  # Riwayat keguguran
    jarak_kehamilan_terakhir = Column(String(100))  # Jarak kehamilan terakhir
    previous_pregnancy_complications = Column(Text)  # Komplikasi kehamilan sebelumnya
    pernah_caesar = Column(Boolean, default=False)
    pernah_perdarahan_saat_hamil = Column(Boolean, default=False)
    
    # Alamat & Lokasi
    address = Column(Text, nullable=False)
    provinsi = Column(String(100))
    kota_kabupaten = Column(String(100))
    kelurahan = Column(String(100))
    kecamatan = Column(String(100))
    location = Column(Geography(geometry_type='POINT', srid=4326), nullable=False)
    
    # Kontak Darurat
    emergency_contact_name = Column(String(255), nullable=False)
    emergency_contact_phone = Column(String(20), nullable=False)
    emergency_contact_relation = Column(String(50))
    
    # Riwayat Kesehatan
    darah_tinggi = Column(Boolean, default=False)
    diabetes = Column(Boolean, default=False)
    anemia = Column(Boolean, default=False)
    penyakit_jantung = Column(Boolean, default=False)
    asma = Column(Boolean, default=False)
    penyakit_ginjal = Column(Boolean, default=False)
    tbc_malaria = Column(Boolean, default=False)
    
    # Risk Assessment (ditentukan oleh perawat)
    risk_level = Column(String(20), nullable=True, index=True)  # rendah, sedang, tinggi (null jika belum ditentukan)
    risk_level_set_by = Column(Integer, ForeignKey("perawat.id", ondelete="SET NULL"), nullable=True)  # Perawat yang menentukan
    risk_level_set_at = Column(TIMESTAMP, nullable=True)  # Waktu penentuan risiko
    
    # Assignment Info
    assignment_date = Column(TIMESTAMP)
    assignment_distance_km = Column(Float)
    assignment_method = Column(String(50))
    
    # Consent & Preferences
    healthcare_preference = Column(String(50))
    whatsapp_consent = Column(Boolean, default=True)
    data_sharing_consent = Column(Boolean, default=False)
    
    # Status
    is_active = Column(Boolean, default=True, index=True)
    
    # Timestamps
    created_at = Column(TIMESTAMP, server_default=func.now())
    updated_at = Column(TIMESTAMP, server_default=func.now(), onupdate=func.now())
    
    # Constraints
    __table_args__ = (
        CheckConstraint("risk_level IS NULL OR risk_level IN ('rendah', 'sedang', 'tinggi')", name="check_risk_level"),
        CheckConstraint("assignment_method IN ('auto', 'manual')", name="check_assignment_method"),
    )
    
    # Relationships
    user = relationship("User", foreign_keys=[user_id])
    puskesmas = relationship("Puskesmas", foreign_keys=[puskesmas_id])
    perawat = relationship("Perawat", back_populates="ibu_hamil_list", foreign_keys=[perawat_id])
    assigned_by = relationship("User", foreign_keys=[assigned_by_user_id])
    risk_assessor = relationship("Perawat", foreign_keys=[risk_level_set_by])  # Perawat yang menentukan risiko