"""PostLike model for post likes."""

from sqlalchemy import Column, Integer, TIMESTAMP, ForeignKey, UniqueConstraint, Index
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from ..database import Base


class PostLike(Base):
    """Model untuk like pada postingan."""
    
    __tablename__ = "post_likes"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # Foreign Keys
    post_id = Column(
        Integer, 
        ForeignKey("posts.id", ondelete="CASCADE"), 
        nullable=False, 
        index=True
    )
    user_id = Column(
        Integer, 
        ForeignKey("users.id", ondelete="CASCADE"), 
        nullable=False, 
        index=True
    )
    
    # Timestamps
    created_at = Column(TIMESTAMP, server_default=func.now())
    
    # Constraints
    __table_args__ = (
        # Satu user hanya bisa like sekali per post
        UniqueConstraint('post_id', 'user_id', name='uq_post_like'),
        # Index untuk query likes by post
        Index('idx_post_like_post', 'post_id', 'created_at'),
        # Index untuk query likes by user
        Index('idx_post_like_user', 'user_id', 'created_at'),
    )
    
    # Relationships
    post = relationship("Post", back_populates="likes")
    user = relationship("User", foreign_keys=[user_id])
