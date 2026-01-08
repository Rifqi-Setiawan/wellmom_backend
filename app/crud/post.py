"""CRUD operations for Post."""

from typing import List, Optional
from datetime import datetime
from sqlalchemy import select, and_, or_, func, desc
from sqlalchemy.orm import Session

from app.crud.base import CRUDBase
from app.models.post import Post
from app.models.post_like import PostLike
from app.models.post_reply import PostReply
from app.schemas.post import PostCreate, PostUpdate


class CRUDPost(CRUDBase[Post, PostCreate, PostUpdate]):
    """CRUD operations for Post."""
    
    def create_post(
        self,
        db: Session,
        *,
        author_user_id: int,
        title: str,
        details: str
    ) -> Post:
        """Create a new post."""
        post = Post(
            author_user_id=author_user_id,
            title=title,
            details=details,
            like_count=0,
            reply_count=0
        )
        db.add(post)
        db.commit()
        db.refresh(post)
        return post
    
    def get_all(
        self,
        db: Session,
        *,
        skip: int = 0,
        limit: int = 50,
        sort_by: str = "recent"  # "recent", "popular", "most_liked"
    ) -> List[Post]:
        """Get all posts with pagination and sorting."""
        stmt = select(Post).where(Post.is_deleted == False)
        
        # Apply sorting
        if sort_by == "popular":
            stmt = stmt.order_by(
                desc(Post.reply_count),
                desc(Post.like_count),
                desc(Post.created_at)
            )
        elif sort_by == "most_liked":
            stmt = stmt.order_by(
                desc(Post.like_count),
                desc(Post.created_at)
            )
        else:  # recent (default)
            stmt = stmt.order_by(desc(Post.created_at))
        
        stmt = stmt.offset(skip).limit(limit)
        return list(db.scalars(stmt).all())
    
    def get_total_count(self, db: Session) -> int:
        """Get total count of non-deleted posts."""
        stmt = select(func.count(Post.id)).where(Post.is_deleted == False)
        return db.scalar(stmt) or 0
    
    def get_by_id(
        self,
        db: Session,
        *,
        post_id: int,
        include_deleted: bool = False
    ) -> Optional[Post]:
        """Get post by ID."""
        stmt = select(Post).where(Post.id == post_id)
        if not include_deleted:
            stmt = stmt.where(Post.is_deleted == False)
        return db.scalars(stmt).first()
    
    def soft_delete(
        self,
        db: Session,
        *,
        post_id: int,
        user_id: int
    ) -> Optional[Post]:
        """Soft delete a post (only by author)."""
        post = self.get_by_id(db, post_id=post_id)
        if not post:
            return None
        
        if post.author_user_id != user_id:
            raise PermissionError("Only post author can delete the post")
        
        post.is_deleted = True
        post.deleted_at = datetime.utcnow()
        db.add(post)
        db.commit()
        db.refresh(post)
        return post
    
    def check_user_liked(
        self,
        db: Session,
        *,
        post_id: int,
        user_id: int
    ) -> bool:
        """Check if user has liked a post."""
        stmt = select(PostLike).where(
            and_(
                PostLike.post_id == post_id,
                PostLike.user_id == user_id
            )
        )
        like = db.scalars(stmt).first()
        return like is not None


# Singleton instance
crud_post = CRUDPost(Post)
