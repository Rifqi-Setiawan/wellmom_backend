"""PostReply model for post replies/comments."""

from sqlalchemy import Column, Integer, Text, TIMESTAMP, ForeignKey, Index, Boolean
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from ..database import Base


class PostReply(Base):
    """Model untuk reply/comment pada postingan."""
    
    __tablename__ = "post_replies"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # Foreign Keys
    post_id = Column(
        Integer, 
        ForeignKey("posts.id", ondelete="CASCADE"), 
        nullable=False, 
        index=True
    )
    author_user_id = Column(
        Integer, 
        ForeignKey("users.id", ondelete="CASCADE"), 
        nullable=False, 
        index=True
    )
    parent_reply_id = Column(
        Integer, 
        ForeignKey("post_replies.id", ondelete="CASCADE"), 
        nullable=True, 
        index=True
    )  # Untuk nested replies (optional, bisa diimplementasikan nanti)
    
    # Reply Content
    reply_text = Column(Text, nullable=False)
    
    # Timestamps
    created_at = Column(TIMESTAMP, server_default=func.now(), index=True)
    updated_at = Column(TIMESTAMP, server_default=func.now(), onupdate=func.now())
    
    # Soft delete
    is_deleted = Column(Boolean, default=False, index=True)
    deleted_at = Column(TIMESTAMP, nullable=True)
    
    # Constraints & Indexes
    __table_args__ = (
        # Index untuk query replies by post
        Index('idx_post_reply_post', 'post_id', 'created_at'),
        # Index untuk query replies by author
        Index('idx_post_reply_author', 'author_user_id', 'created_at'),
    )
    
    # Relationships
    post = relationship("Post", back_populates="replies")
    author = relationship("User", foreign_keys=[author_user_id])
    parent_reply = relationship("PostReply", remote_side=[id], backref="child_replies")
