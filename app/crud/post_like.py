"""CRUD operations for PostLike."""

from typing import Optional, Tuple
from sqlalchemy import select, and_
from sqlalchemy.orm import Session

from app.crud.base import CRUDBase
from app.models.post import Post
from app.models.post_like import PostLike


class CRUDPostLike(CRUDBase[PostLike, dict, dict]):
    """CRUD operations for PostLike."""
    
    def toggle_like(
        self,
        db: Session,
        *,
        post_id: int,
        user_id: int
    ) -> Tuple[bool, int]:
        """
        Toggle like on a post.
        
        Returns:
            (is_liked: bool, new_like_count: int)
        """
        # Check if post exists and is not deleted
        post = db.get(Post, post_id)
        if not post or post.is_deleted:
            raise ValueError("Post not found or deleted")
        
        # Check if user already liked
        stmt = select(PostLike).where(
            and_(
                PostLike.post_id == post_id,
                PostLike.user_id == user_id
            )
        )
        existing_like = db.scalars(stmt).first()
        
        if existing_like:
            # Unlike: delete the like
            db.delete(existing_like)
            post.like_count = max(0, post.like_count - 1)
            is_liked = False
        else:
            # Like: create new like
            new_like = PostLike(
                post_id=post_id,
                user_id=user_id
            )
            db.add(new_like)
            post.like_count = post.like_count + 1
            is_liked = True
        
        db.add(post)
        db.commit()
        db.refresh(post)
        
        return is_liked, post.like_count
    
    def get_like(
        self,
        db: Session,
        *,
        post_id: int,
        user_id: int
    ) -> Optional[PostLike]:
        """Get like record if exists."""
        stmt = select(PostLike).where(
            and_(
                PostLike.post_id == post_id,
                PostLike.user_id == user_id
            )
        )
        return db.scalars(stmt).first()


# Singleton instance
crud_post_like = CRUDPostLike(PostLike)
