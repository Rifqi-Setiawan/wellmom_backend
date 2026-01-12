"""Pydantic schemas for PostCategory."""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class PostCategoryBase(BaseModel):
    """Base schema for PostCategory."""
    name: str = Field(..., min_length=1, max_length=100, description="Category name (slug)")
    display_name: str = Field(..., min_length=1, max_length=100, description="Category display name")
    description: Optional[str] = Field(None, description="Category description")
    icon: Optional[str] = Field(None, max_length=100, description="Icon name/url")


class PostCategoryCreate(PostCategoryBase):
    """Schema for creating a new category."""
    pass


class PostCategoryUpdate(BaseModel):
    """Schema for updating a category."""
    display_name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = None
    icon: Optional[str] = Field(None, max_length=100)
    is_active: Optional[bool] = None


class PostCategoryResponse(PostCategoryBase):
    """Schema for PostCategory response."""
    id: int
    is_active: bool
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class PostCategoryListResponse(BaseModel):
    """Response for listing categories."""
    categories: list[PostCategoryResponse]
