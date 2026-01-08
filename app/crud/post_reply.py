"""CRUD operations for PostReply."""

from typing import List, Optional
from datetime import datetime
from sqlalchemy import select, and_
from sqlalchemy.orm import Session

from app.crud.base import CRUDBase
from app.models.post import Post
from app.models.post_reply import PostReply


class CRUDPostReply(CRUDBase[PostReply, dict, dict]):
    """CRUD operations for PostReply."""
    
    def create_reply(
        self,
        db: Session,
        *,
        post_id: int,
        author_user_id: int,
        reply_text: str,
        parent_reply_id: Optional[int] = None
    ) -> PostReply:
        """Create a new reply to a post."""
        # Verify post exists and is not deleted
        post = db.get(Post, post_id)
        if not post or post.is_deleted:
            raise ValueError("Post not found or deleted")
        
        # If parent_reply_id is provided, verify it exists
        if parent_reply_id:
            parent_reply = db.get(PostReply, parent_reply_id)
            if not parent_reply or parent_reply.is_deleted or parent_reply.post_id != post_id:
                raise ValueError("Parent reply not found or invalid")
        
        # Create reply
        reply = PostReply(
            post_id=post_id,
            author_user_id=author_user_id,
            reply_text=reply_text,
            parent_reply_id=parent_reply_id
        )
        db.add(reply)
        
        # Update post reply_count
        post.reply_count = post.reply_count + 1
        db.add(post)
        
        db.commit()
        db.refresh(reply)
        return reply
    
    def get_by_post(
        self,
        db: Session,
        *,
        post_id: int,
        skip: int = 0,
        limit: int = 100
    ) -> List[PostReply]:
        """Get all replies for a post."""
        stmt = (
            select(PostReply)
            .where(
                and_(
                    PostReply.post_id == post_id,
                    PostReply.is_deleted == False
                )
            )
            .order_by(PostReply.created_at.asc())
            .offset(skip)
            .limit(limit)
        )
        return list(db.scalars(stmt).all())
    
    def get_total_count(
        self,
        db: Session,
        *,
        post_id: int
    ) -> int:
        """Get total count of replies for a post."""
        from sqlalchemy import func
        stmt = select(func.count(PostReply.id)).where(
            and_(
                PostReply.post_id == post_id,
                PostReply.is_deleted == False
            )
        )
        return db.scalar(stmt) or 0
    
    def get_by_id(
        self,
        db: Session,
        *,
        reply_id: int,
        include_deleted: bool = False
    ) -> Optional[PostReply]:
        """Get reply by ID."""
        stmt = select(PostReply).where(PostReply.id == reply_id)
        if not include_deleted:
            stmt = stmt.where(PostReply.is_deleted == False)
        return db.scalars(stmt).first()
    
    def soft_delete(
        self,
        db: Session,
        *,
        reply_id: int,
        user_id: int
    ) -> Optional[PostReply]:
        """Soft delete a reply (only by author)."""
        reply = self.get_by_id(db, reply_id=reply_id)
        if not reply:
            return None
        
        if reply.author_user_id != user_id:
            raise PermissionError("Only reply author can delete the reply")
        
        reply.is_deleted = True
        reply.deleted_at = datetime.utcnow()
        
        # Update post reply_count
        post = db.get(Post, reply.post_id)
        if post:
            post.reply_count = max(0, post.reply_count - 1)
            db.add(post)
        
        db.add(reply)
        db.commit()
        db.refresh(reply)
        return reply


# Singleton instance
crud_post_reply = CRUDPostReply(PostReply)
