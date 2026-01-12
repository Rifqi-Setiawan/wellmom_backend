"""CRUD operations for PostCategory."""

from typing import List, Optional
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.crud.base import CRUDBase
from app.models.post_category import PostCategory
from app.schemas.post_category import PostCategoryCreate, PostCategoryUpdate


class CRUDPostCategory(CRUDBase[PostCategory, PostCategoryCreate, PostCategoryUpdate]):
    """CRUD operations for PostCategory."""
    
    def get_all_active(self, db: Session) -> List[PostCategory]:
        """Get all active categories."""
        stmt = select(PostCategory).where(PostCategory.is_active == True).order_by(PostCategory.id)
        return list(db.scalars(stmt).all())
    
    def get_by_name(self, db: Session, name: str) -> Optional[PostCategory]:
        """Get category by name (slug)."""
        stmt = select(PostCategory).where(PostCategory.name == name).limit(1)
        return db.scalars(stmt).first()


# Singleton instance
crud_post_category = CRUDPostCategory(PostCategory)
