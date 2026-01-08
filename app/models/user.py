from sqlalchemy import Column, Integer, String, Boolean, TIMESTAMP, CheckConstraint
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from ..database import Base


class User(Base):
    __tablename__ = "users"
    
    # Primary Key
    id = Column(Integer, primary_key=True, index=True)
    
    # Authentication & Contact
    email = Column(String(255), unique=True, index=True)
    phone = Column(String(20), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    full_name = Column(String(255), nullable=False)
    
    # Role & Authorization
    role = Column(String(50), nullable=False, index=True)
    
    # Profile
    profile_photo_url = Column(String(500))
    
    # Account Status
    is_active = Column(Boolean, default=True, index=True)
    is_verified = Column(Boolean, default=False)
    verification_token = Column(String(255))
    
    # Timestamps
    created_at = Column(TIMESTAMP, server_default=func.now())
    updated_at = Column(TIMESTAMP, server_default=func.now(), onupdate=func.now())
    
    # Constraints
    __table_args__ = (
        CheckConstraint(
            "role IN ('super_admin', 'puskesmas', 'perawat', 'ibu_hamil', 'kerabat')",
            name="check_user_role"
        ),
    )
    
    # Relationships
    # Will be defined after other models are created