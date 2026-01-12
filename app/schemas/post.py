"""Pydantic schemas for Post (Forum Discussion)."""

from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field


class PostBase(BaseModel):
    """Base schema for Post."""
    title: str = Field(..., min_length=1, max_length=500, description="Post title")
    details: str = Field(..., min_length=1, description="Post content/details")
    category_id: int = Field(..., gt=0, description="Post category ID")


class PostCreate(PostBase):
    """Schema for creating a new post."""
    pass


class PostUpdate(BaseModel):
    """Schema for updating a post."""
    title: Optional[str] = Field(None, min_length=1, max_length=500)
    details: Optional[str] = Field(None, min_length=1)
    category_id: Optional[int] = Field(None, gt=0, description="Post category ID")


class PostResponse(PostBase):
    """Schema for Post response."""
    id: int
    author_user_id: int
    author_name: Optional[str] = None  # Will be populated from user relationship
    author_role: Optional[str] = None  # Will be populated from user relationship
    category_id: int
    category_name: Optional[str] = None  # Will be populated from category relationship
    category_display_name: Optional[str] = None  # Will be populated from category relationship
    like_count: int
    reply_count: int
    is_liked: bool = False  # Will be populated based on current user
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class PostListResponse(BaseModel):
    """Response for listing posts."""
    posts: List[PostResponse]
    total: int
    has_more: bool = Field(..., description="Whether there are more posts to load")


class PostDetailResponse(PostResponse):
    """Detailed post response with replies."""
    replies: List["PostReplyResponse"] = []


class PostLikeRequest(BaseModel):
    """Schema for liking/unliking a post."""
    pass  # No body needed, just endpoint action


class PostLikeResponse(BaseModel):
    """Response for like action."""
    post_id: int
    is_liked: bool
    like_count: int
    message: str


class PostReplyCreate(BaseModel):
    """Schema for creating a reply."""
    reply_text: str = Field(..., min_length=1, description="Reply content")


class PostReplyResponse(BaseModel):
    """Schema for PostReply response."""
    id: int
    post_id: int
    author_user_id: int
    author_name: Optional[str] = None
    author_role: Optional[str] = None
    reply_text: str
    parent_reply_id: Optional[int] = None
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class PostReplyListResponse(BaseModel):
    """Response for listing replies."""
    replies: List[PostReplyResponse]
    total: int
