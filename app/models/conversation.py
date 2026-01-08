"""Conversation model for chat between Ibu Hamil and Perawat."""

from sqlalchemy import Column, Integer, TIMESTAMP, ForeignKey, UniqueConstraint, Index
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from ..database import Base


class Conversation(Base):
    """Model untuk percakapan antara Ibu Hamil dan Perawat."""
    
    __tablename__ = "conversations"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # Foreign Keys
    ibu_hamil_id = Column(
        Integer, 
        ForeignKey("ibu_hamil.id", ondelete="CASCADE"), 
        nullable=False, 
        index=True
    )
    perawat_id = Column(
        Integer, 
        ForeignKey("perawat.id", ondelete="CASCADE"), 
        nullable=False, 
        index=True
    )
    
    # Metadata
    last_message_at = Column(TIMESTAMP, nullable=True, index=True)  # Untuk sorting conversations
    
    # Timestamps
    created_at = Column(TIMESTAMP, server_default=func.now())
    updated_at = Column(TIMESTAMP, server_default=func.now(), onupdate=func.now())
    
    # Constraints
    __table_args__ = (
        # Satu conversation unik per pasangan (ibu_hamil, perawat)
        UniqueConstraint('ibu_hamil_id', 'perawat_id', name='uq_conversation_pair'),
        # Index untuk query conversations by ibu_hamil atau perawat
        Index('idx_conversation_ibu_hamil', 'ibu_hamil_id', 'last_message_at'),
        Index('idx_conversation_perawat', 'perawat_id', 'last_message_at'),
    )
    
    # Relationships
    ibu_hamil = relationship("IbuHamil", foreign_keys=[ibu_hamil_id])
    perawat = relationship("Perawat", foreign_keys=[perawat_id])
    messages = relationship(
        "Message", 
        back_populates="conversation",
        cascade="all, delete-orphan"
    )
