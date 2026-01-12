"""PostCategory model for forum discussion categories."""

from sqlalchemy import Column, Integer, String, Text, TIMESTAMP, Boolean
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from ..database import Base


class PostCategory(Base):
    """Model untuk kategori forum diskusi."""
    
    __tablename__ = "post_categories"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False, unique=True, index=True)  # kesehatan, nutrisi, etc.
    display_name = Column(String(100), nullable=False)  # Kesehatan, Nutrisi, etc.
    description = Column(Text, nullable=True)  # Optional description
    icon = Column(String(100), nullable=True)  # Optional icon name/url
    is_active = Column(Boolean, default=True, index=True)
    
    # Timestamps
    created_at = Column(TIMESTAMP, server_default=func.now())
    updated_at = Column(TIMESTAMP, server_default=func.now(), onupdate=func.now())
    
    # Relationships
    posts = relationship("Post", back_populates="category_obj")
