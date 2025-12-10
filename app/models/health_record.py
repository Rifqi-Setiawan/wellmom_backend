from sqlalchemy import Column, Integer, String, Boolean, TIMESTAMP, ForeignKey, Float, Date, Text, CheckConstraint
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
    checkup_type = Column(String(50), nullable=False, index=True)
    data_source = Column(String(50), default='manual', index=True)
    
    # Gestational Age
    gestational_age_weeks = Column(Integer)
    gestational_age_days = Column(Integer)
    
    # Vital Signs (Manual OR IoT)
    blood_pressure_systolic = Column(Integer)
    blood_pressure_diastolic = Column(Integer)
    blood_glucose = Column(Float)
    body_temperature = Column(Float)
    heart_rate = Column(Integer)
    
    # Obstetric Examination (Manual only)
    fundal_height_cm = Column(Float)
    fetal_heart_rate = Column(Integer)
    
    # Subjective & Objective
    complaints = Column(Text)
    physical_examination = Column(Text)
    diagnosis = Column(Text)
    
    # Treatment Plan
    treatment_plan = Column(Text)
    medications = Column(Text)
    supplements = Column(Text)
    
    # Referral
    referral_needed = Column(Boolean, default=False, index=True)
    referral_notes = Column(Text)
    
    # Follow-up
    next_checkup_date = Column(Date)
    next_checkup_notes = Column(Text)
    
    # Additional Notes
    notes = Column(Text)
    
    # Timestamps
    created_at = Column(TIMESTAMP, server_default=func.now())
    updated_at = Column(TIMESTAMP, server_default=func.now(), onupdate=func.now())
    
    # Constraints
    __table_args__ = (
        CheckConstraint("checkup_type IN ('berkala', 'ad-hoc')", name="check_checkup_type"),
        CheckConstraint("data_source IN ('manual', 'iot_device')", name="check_data_source"),
    )
    
    # Relationships
    ibu_hamil = relationship("IbuHamil", foreign_keys=[ibu_hamil_id])
    perawat = relationship("Perawat", foreign_keys=[perawat_id])