"""Post model for forum discussion."""

from enum import Enum
from sqlalchemy import Column, Integer, String, Text, TIMESTAMP, ForeignKey, Index, Boolean, Enum as SQLEnum
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from ..database import Base


class PostCategory(str, Enum):
    """Forum post categories."""
    KESEHATAN = "kesehatan"
    NUTRISI = "nutrisi"
    PERSIAPAN = "persiapan"
    CURHAT = "curhat"
    TIPS = "tips"
    TANYA_JAWAB = "tanya_jawab"


class Post(Base):
    """Model untuk postingan forum diskusi."""
    
    __tablename__ = "posts"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # Foreign Keys
    author_user_id = Column(
        Integer, 
        ForeignKey("users.id", ondelete="CASCADE"), 
        nullable=False, 
        index=True
    )
    
    # Post Content
    title = Column(String(500), nullable=False)
    details = Column(Text, nullable=False)
    category = Column(
        SQLEnum(PostCategory, name="post_category"),
        nullable=False,
        default=PostCategory.TANYA_JAWAB,
        index=True
    )
    
    # Metadata
    like_count = Column(Integer, default=0, index=True)  # Denormalized untuk performance
    reply_count = Column(Integer, default=0, index=True)  # Denormalized untuk performance
    
    # Timestamps
    created_at = Column(TIMESTAMP, server_default=func.now(), index=True)
    updated_at = Column(TIMESTAMP, server_default=func.now(), onupdate=func.now())
    
    # Soft delete
    is_deleted = Column(Boolean, default=False, index=True)
    deleted_at = Column(TIMESTAMP, nullable=True)
    
    # Constraints & Indexes
    __table_args__ = (
        # Index untuk query posts by author
        Index('idx_post_author_created', 'author_user_id', 'created_at'),
        # Index untuk query posts by popularity (like_count, reply_count)
        Index('idx_post_popularity', 'like_count', 'reply_count', 'created_at'),
        # Index untuk query posts by category
        Index('idx_post_category_created', 'category', 'created_at'),
    )
    
    # Relationships
    author = relationship("User", foreign_keys=[author_user_id])
    likes = relationship(
        "PostLike", 
        back_populates="post",
        cascade="all, delete-orphan"
    )
    replies = relationship(
        "PostReply",
        back_populates="post",
        cascade="all, delete-orphan",
        order_by="PostReply.created_at.asc()"
    )
