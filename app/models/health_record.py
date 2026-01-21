from sqlalchemy import Column, Integer, String, TIMESTAMP, ForeignKey, Float, Date, Text, CheckConstraint
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from ..database import Base


class HealthRecord(Base):
    __tablename__ = "health_records"

    id = Column(Integer, primary_key=True, index=True)

    # Foreign Keys
    ibu_hamil_id = Column(Integer, ForeignKey("ibu_hamil.id", ondelete="CASCADE"), nullable=False, index=True)
    perawat_id = Column(Integer, ForeignKey("perawat.id", ondelete="SET NULL"), index=True)

    # Checkup Info
    checkup_date = Column(Date, nullable=False, index=True)
    checked_by = Column(String(20), nullable=False, index=True)  # 'perawat' or 'mandiri'

    # Gestational Age
    gestational_age_weeks = Column(Integer)
    gestational_age_days = Column(Integer)

    # Required Vital Signs (wajib diisi)
    blood_pressure_systolic = Column(Integer, nullable=False)
    blood_pressure_diastolic = Column(Integer, nullable=False)
    heart_rate = Column(Integer, nullable=False)
    body_temperature = Column(Float, nullable=False)
    weight = Column(Float, nullable=False)  # berat badan (kg)
    complaints = Column(Text, nullable=False)  # keluhan

    # Optional Lab/Puskesmas Data (tidak wajib)
    hemoglobin = Column(Float)  # g/dL
    blood_glucose = Column(Float)  # gula darah (mg/dL)
    protein_urin = Column(String(20))  # negatif, +1, +2, +3, +4
    upper_arm_circumference = Column(Float)  # lingkar lengan atas / LILA (cm)
    fundal_height = Column(Float)  # tinggi fundus uteri (cm)
    fetal_heart_rate = Column(Integer)  # denyut jantung janin (bpm)

    # Additional Notes
    notes = Column(Text)

    # Timestamps
    created_at = Column(TIMESTAMP, server_default=func.now())
    updated_at = Column(TIMESTAMP, server_default=func.now(), onupdate=func.now())

    # Constraints
    __table_args__ = (
        CheckConstraint("checked_by IN ('perawat', 'mandiri')", name="check_checked_by"),
    )

    # Relationships
    ibu_hamil = relationship("IbuHamil", foreign_keys=[ibu_hamil_id])
    perawat = relationship("Perawat", foreign_keys=[perawat_id])
