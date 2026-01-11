"""Forum Discussion endpoints."""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session

from app.api.deps import get_current_active_user, get_db, require_role
from app.crud import (
    crud_post,
    crud_post_like,
    crud_post_reply,
    crud_user,
)
from app.models.user import User
from app.models.post import Post
from app.schemas.post import (
    PostCreate,
    PostUpdate,
    PostResponse,
    PostListResponse,
    PostDetailResponse,
    PostLikeResponse,
    PostReplyCreate,
    PostReplyResponse,
    PostReplyListResponse,
)

router = APIRouter(
    prefix="/forum",
    tags=["Forum Discussion"],
)


def _enrich_post_response(
    db: Session,
    post: Post,
    current_user_id: Optional[int] = None
) -> PostResponse:
    """Enrich post with author info and like status."""
    author = crud_user.get(db, post.author_user_id)
    is_liked = False
    
    if current_user_id:
        is_liked = crud_post.check_user_liked(
            db, post_id=post.id, user_id=current_user_id
        )
    
    return PostResponse(
        id=post.id,
        author_user_id=post.author_user_id,
        author_name=author.full_name if author else None,
        author_role=author.role if author else None,
        title=post.title,
        details=post.details,
        like_count=post.like_count,
        reply_count=post.reply_count,
        is_liked=is_liked,
        created_at=post.created_at,
        updated_at=post.updated_at,
    )


@router.post(
    "",
    response_model=PostResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create new post",
    description="""
    Create a new forum post.
    
    **Access:** Ibu Hamil and Perawat only
    """,
)
def create_post(
    post_in: PostCreate,
    current_user: User = Depends(require_role("ibu_hamil", "perawat")),
    db: Session = Depends(get_db),
) -> PostResponse:
    """Create a new forum post."""
    post = crud_post.create_post(
        db,
        author_user_id=current_user.id,
        title=post_in.title,
        details=post_in.details
    )
    
    return _enrich_post_response(db, post, current_user.id)


@router.get(
    "",
    response_model=PostListResponse,
    status_code=status.HTTP_200_OK,
    summary="List all posts",
    description="""
    Get list of all forum posts with pagination and sorting.
    
    **Sorting options:**
    - `recent` (default): Most recent posts first
    - `popular`: Most replies first, then most likes
    - `most_liked`: Most likes first
    
    **Access:** All authenticated users
    """,
)
def list_posts(
    skip: int = Query(0, ge=0, description="Number of posts to skip"),
    limit: int = Query(50, ge=1, le=100, description="Maximum number of posts to return"),
    sort_by: str = Query("recent", regex="^(recent|popular|most_liked)$", description="Sorting option"),
    current_user: Optional[User] = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> PostListResponse:
    """List all forum posts."""
    posts = crud_post.get_all(
        db, skip=skip, limit=limit, sort_by=sort_by
    )
    
    total = crud_post.get_total_count(db)
    
    # Enrich posts with author info and like status
    enriched_posts = [
        _enrich_post_response(db, post, current_user.id if current_user else None)
        for post in posts
    ]
    
    return PostListResponse(
        posts=enriched_posts,
        total=total,
        has_more=(skip + len(posts) < total)
    )


@router.get(
    "/recent",
    response_model=PostListResponse,
    status_code=status.HTTP_200_OK,
    summary="Get recent forum posts",
    description="""
    Get list of recent forum posts sorted by creation date (newest first).
    
    **Features:**
    - Posts are sorted by `created_at` descending (newest first)
    - Only non-deleted posts are returned
    - Optional filter by days (e.g., `days=7` for posts from last week)
    
    **Query Parameters:**
    - `skip`: Number of posts to skip (for pagination)
    - `limit`: Maximum number of posts to return (default: 20, max: 100)
    - `days`: Optional filter to get posts from last N days (e.g., 7 for last week, 30 for last month)
    
    **Access:** All authenticated users
    """,
    responses={
        200: {
            "description": "List of recent posts",
            "content": {
                "application/json": {
                    "example": {
                        "posts": [
                            {
                                "id": 1,
                                "author_user_id": 10,
                                "author_name": "Siti Aminah",
                                "author_role": "ibu_hamil",
                                "title": "Tips menjaga kesehatan saat hamil",
                                "details": "Bagaimana cara menjaga kesehatan...",
                                "like_count": 5,
                                "reply_count": 3,
                                "is_liked": False,
                                "created_at": "2026-01-09T10:00:00Z",
                                "updated_at": "2026-01-09T10:00:00Z"
                            }
                        ],
                        "total": 50,
                        "has_more": True
                    }
                }
            }
        }
    }
)
def get_recent_posts(
    skip: int = Query(0, ge=0, description="Number of posts to skip"),
    limit: int = Query(20, ge=1, le=100, description="Maximum number of posts to return"),
    days: Optional[int] = Query(None, ge=1, description="Filter posts from last N days (e.g., 7 for last week)"),
    current_user: Optional[User] = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> PostListResponse:
    """
    Get recent forum posts sorted by creation date (newest first).
    
    Args:
        skip: Number of posts to skip (for pagination)
        limit: Maximum number of posts to return
        days: Optional filter to get posts from last N days
        current_user: Current authenticated user (optional)
        db: Database session
        
    Returns:
        PostListResponse: List of recent posts with pagination info
    """
    # Get recent posts
    posts = crud_post.get_recent_posts(
        db, skip=skip, limit=limit, days=days
    )
    
    # Get total count
    total = crud_post.get_recent_posts_count(db, days=days)
    
    # Enrich posts with author info and like status
    enriched_posts = [
        _enrich_post_response(db, post, current_user.id if current_user else None)
        for post in posts
    ]
    
    return PostListResponse(
        posts=enriched_posts,
        total=total,
        has_more=(skip + len(posts) < total)
    )


@router.get(
    "/{post_id}",
    response_model=PostDetailResponse,
    status_code=status.HTTP_200_OK,
    summary="Get post detail",
    description="""
    Get post detail with all replies.
    
    **Access:** All authenticated users
    """,
)
def get_post_detail(
    post_id: int,
    current_user: Optional[User] = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> PostDetailResponse:
    """Get post detail with replies."""
    post = crud_post.get_by_id(db, post_id=post_id)
    if not post:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Post tidak ditemukan."
        )
    
    # Get replies
    replies = crud_post_reply.get_by_post(db, post_id=post_id, skip=0, limit=1000)
    
    # Enrich replies with author info
    enriched_replies = []
    for reply in replies:
        author = crud_user.get(db, reply.author_user_id)
        enriched_replies.append(PostReplyResponse(
            id=reply.id,
            post_id=reply.post_id,
            author_user_id=reply.author_user_id,
            author_name=author.full_name if author else None,
            author_role=author.role if author else None,
            reply_text=reply.reply_text,
            parent_reply_id=reply.parent_reply_id,
            created_at=reply.created_at,
            updated_at=reply.updated_at,
        ))
    
    # Enrich post
    enriched_post = _enrich_post_response(db, post, current_user.id if current_user else None)
    
    return PostDetailResponse(
        **enriched_post.model_dump(),
        replies=enriched_replies
    )


@router.put(
    "/{post_id}",
    response_model=PostResponse,
    status_code=status.HTTP_200_OK,
    summary="Update post",
    description="""
    Update a post. Only the author can update their own post.
    
    **Access:** Post author only
    """,
)
def update_post(
    post_id: int,
    post_update: PostUpdate,
    current_user: User = Depends(require_role("ibu_hamil", "perawat")),
    db: Session = Depends(get_db),
) -> PostResponse:
    """Update a post."""
    post = crud_post.get_by_id(db, post_id=post_id)
    if not post:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Post tidak ditemukan."
        )
    
    if post.author_user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Anda tidak memiliki izin untuk mengupdate post ini."
        )
    
    updated_post = crud_post.update(db, db_obj=post, obj_in=post_update)
    return _enrich_post_response(db, updated_post, current_user.id)


@router.delete(
    "/{post_id}",
    status_code=status.HTTP_200_OK,
    summary="Delete post",
    description="""
    Soft delete a post. Only the author can delete their own post.
    
    **Access:** Post author only
    """,
)
def delete_post(
    post_id: int,
    current_user: User = Depends(require_role("ibu_hamil", "perawat")),
    db: Session = Depends(get_db),
) -> dict:
    """Delete a post (soft delete)."""
    try:
        deleted_post = crud_post.soft_delete(
            db, post_id=post_id, user_id=current_user.id
        )
        if not deleted_post:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Post tidak ditemukan."
            )
        return {"message": "Post berhasil dihapus."}
    except PermissionError:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Anda tidak memiliki izin untuk menghapus post ini."
        )


@router.post(
    "/{post_id}/like",
    response_model=PostLikeResponse,
    status_code=status.HTTP_200_OK,
    summary="Toggle like on post",
    description="""
    Like or unlike a post. If already liked, it will unlike. If not liked, it will like.
    
    **Access:** All authenticated users
    """,
)
def toggle_like_post(
    post_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> PostLikeResponse:
    """Toggle like on a post."""
    try:
        is_liked, like_count = crud_post_like.toggle_like(
            db, post_id=post_id, user_id=current_user.id
        )
        return PostLikeResponse(
            post_id=post_id,
            is_liked=is_liked,
            like_count=like_count,
            message="Post berhasil di-like." if is_liked else "Post berhasil di-unlike."
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )


@router.get(
    "/{post_id}/replies",
    response_model=PostReplyListResponse,
    status_code=status.HTTP_200_OK,
    summary="Get post replies",
    description="""
    Get all replies for a post.
    
    **Access:** All authenticated users
    """,
)
def get_post_replies(
    post_id: int,
    skip: int = Query(0, ge=0, description="Number of replies to skip"),
    limit: int = Query(100, ge=1, le=500, description="Maximum number of replies to return"),
    current_user: Optional[User] = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> PostReplyListResponse:
    """Get replies for a post."""
    # Verify post exists
    post = crud_post.get_by_id(db, post_id=post_id)
    if not post:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Post tidak ditemukan."
        )
    
    replies = crud_post_reply.get_by_post(
        db, post_id=post_id, skip=skip, limit=limit
    )
    
    total = crud_post_reply.get_total_count(db, post_id=post_id)
    
    # Enrich replies with author info
    enriched_replies = []
    for reply in replies:
        author = crud_user.get(db, reply.author_user_id)
        enriched_replies.append(PostReplyResponse(
            id=reply.id,
            post_id=reply.post_id,
            author_user_id=reply.author_user_id,
            author_name=author.full_name if author else None,
            author_role=author.role if author else None,
            reply_text=reply.reply_text,
            parent_reply_id=reply.parent_reply_id,
            created_at=reply.created_at,
            updated_at=reply.updated_at,
        ))
    
    return PostReplyListResponse(
        replies=enriched_replies,
        total=total
    )


@router.post(
    "/{post_id}/replies",
    response_model=PostReplyResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create reply to post",
    description="""
    Create a reply/comment to a post.
    
    **Access:** All authenticated users
    """,
)
def create_reply(
    post_id: int,
    reply_in: PostReplyCreate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> PostReplyResponse:
    """Create a reply to a post."""
    try:
        reply = crud_post_reply.create_reply(
            db,
            post_id=post_id,
            author_user_id=current_user.id,
            reply_text=reply_in.reply_text
        )
        
        # Enrich with author info
        author = crud_user.get(db, reply.author_user_id)
        return PostReplyResponse(
            id=reply.id,
            post_id=reply.post_id,
            author_user_id=reply.author_user_id,
            author_name=author.full_name if author else None,
            author_role=author.role if author else None,
            reply_text=reply.reply_text,
            parent_reply_id=reply.parent_reply_id,
            created_at=reply.created_at,
            updated_at=reply.updated_at,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )


@router.delete(
    "/{post_id}/replies/{reply_id}",
    status_code=status.HTTP_200_OK,
    summary="Delete reply",
    description="""
    Soft delete a reply. Only the author can delete their own reply.
    
    **Access:** Reply author only
    """,
)
def delete_reply(
    post_id: int,
    reply_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> dict:
    """Delete a reply (soft delete)."""
    try:
        deleted_reply = crud_post_reply.soft_delete(
            db, reply_id=reply_id, user_id=current_user.id
        )
        if not deleted_reply:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Reply tidak ditemukan."
            )
        
        # Verify reply belongs to the post
        if deleted_reply.post_id != post_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Reply tidak sesuai dengan post."
            )
        
        return {"message": "Reply berhasil dihapus."}
    except PermissionError:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Anda tidak memiliki izin untuk menghapus reply ini."
        )
