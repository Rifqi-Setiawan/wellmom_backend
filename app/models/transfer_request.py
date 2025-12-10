from sqlalchemy import Column, Integer, String, TIMESTAMP, ForeignKey, Text, CheckConstraint
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from geoalchemy2 import Geography
from ..database import Base


class TransferRequest(Base):
    __tablename__ = "transfer_requests"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # Request Info
    requester_user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    requester_type = Column(String(50), nullable=False, index=True)
    
    # For Perawat Transfer
    perawat_id = Column(Integer, ForeignKey("perawat.id", ondelete="CASCADE"), index=True)
    from_puskesmas_id = Column(Integer, ForeignKey("puskesmas.id", ondelete="SET NULL"))
    to_puskesmas_id = Column(Integer, ForeignKey("puskesmas.id", ondelete="SET NULL"))
    
    # For Ibu Hamil Transfer
    ibu_hamil_id = Column(Integer, ForeignKey("ibu_hamil.id", ondelete="CASCADE"), index=True)
    new_address = Column(Text)
    new_location = Column(Geography(geometry_type='POINT', srid=4326))
    
    # Request Details
    reason = Column(Text, nullable=False)
    status = Column(String(50), default='pending', index=True)
    
    # Approval Info
    reviewed_by_user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"))
    reviewed_at = Column(TIMESTAMP)
    rejection_reason = Column(Text)
    
    # Timestamps
    created_at = Column(TIMESTAMP, server_default=func.now())
    updated_at = Column(TIMESTAMP, server_default=func.now(), onupdate=func.now())
    
    # Constraints
    __table_args__ = (
        CheckConstraint("requester_type IN ('perawat', 'ibu_hamil')", name="check_requester_type"),
        CheckConstraint("status IN ('pending', 'approved', 'rejected', 'cancelled')", name="check_status"),
        CheckConstraint(
            "(requester_type = 'perawat' AND perawat_id IS NOT NULL) OR (requester_type = 'ibu_hamil' AND ibu_hamil_id IS NOT NULL)",
            name="check_requester_validity"
        ),
    )
    
    # Relationships
    requester_user = relationship("User", foreign_keys=[requester_user_id])
    perawat = relationship("Perawat", foreign_keys=[perawat_id])
    from_puskesmas = relationship("Puskesmas", foreign_keys=[from_puskesmas_id])
    to_puskesmas = relationship("Puskesmas", foreign_keys=[to_puskesmas_id])
    ibu_hamil = relationship("IbuHamil", foreign_keys=[ibu_hamil_id])
    reviewed_by = relationship("User", foreign_keys=[reviewed_by_user_id])