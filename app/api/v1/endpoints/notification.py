"""Notification endpoints for all users."""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status, Query, Path
from sqlalchemy.orm import Session

from app.api.deps import get_current_active_user, get_db
from app.crud import crud_notification
from app.models.user import User
from app.models.notification import Notification
from app.schemas.notification import (
    NotificationResponse,
    NotificationListResponse,
    UnreadCountResponse,
    MarkAllReadResponse,
    DeleteNotificationResponse,
    NOTIFICATION_TYPES,
)

router = APIRouter(
    prefix="/notifications",
    tags=["Notifications"],
)


@router.get(
    "",
    response_model=NotificationListResponse,
    status_code=status.HTTP_200_OK,
    summary="List notifications",
    description="""
    Get list of notifications for the current user with optional filters and pagination.

    **Filters:**
    - `is_read`: Filter by read status (true = read only, false = unread only, omit = all)
    - `notification_type`: Filter by type (checkup_reminder, assignment, health_alert, etc.)

    **Pagination:**
    - `skip`: Number of records to skip (default: 0)
    - `limit`: Maximum records to return (default: 50, max: 100)

    Results are ordered by created_at DESC (newest first).
    """,
    responses={
        200: {"description": "List of notifications retrieved successfully"},
        400: {"description": "Invalid notification_type provided"},
        401: {"description": "Not authenticated"},
    },
)
def list_notifications(
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(50, ge=1, le=100, description="Maximum number of records to return"),
    is_read: Optional[bool] = Query(None, description="Filter by read status"),
    notification_type: Optional[str] = Query(
        None,
        description=f"Filter by notification type. Valid values: {sorted(NOTIFICATION_TYPES)}"
    ),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> NotificationListResponse:
    """List all notifications for the current user."""
    # Validate notification_type if provided
    if notification_type is not None and notification_type not in NOTIFICATION_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid notification_type. Must be one of: {sorted(NOTIFICATION_TYPES)}"
        )

    # Get notifications with filters
    notifications = crud_notification.get_by_user(
        db,
        user_id=current_user.id,
        skip=skip,
        limit=limit,
        is_read=is_read,
        notification_type=notification_type,
    )

    # Get total count (with same filters)
    total = crud_notification.get_total_count(
        db,
        user_id=current_user.id,
        is_read=is_read,
        notification_type=notification_type,
    )

    # Get unread count (always unfiltered for badge display)
    unread_count = crud_notification.get_unread_count(db, user_id=current_user.id)

    return NotificationListResponse(
        notifications=[NotificationResponse.model_validate(n) for n in notifications],
        total=total,
        unread_count=unread_count,
    )


@router.get(
    "/unread-count",
    response_model=UnreadCountResponse,
    status_code=status.HTTP_200_OK,
    summary="Get unread notification count",
    description="Get the count of unread notifications for the current user. Useful for displaying badge count in UI.",
    responses={
        200: {"description": "Unread count retrieved successfully"},
        401: {"description": "Not authenticated"},
    },
)
def get_unread_count(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> UnreadCountResponse:
    """Get unread notification count for current user."""
    unread_count = crud_notification.get_unread_count(db, user_id=current_user.id)

    return UnreadCountResponse(unread_count=unread_count)


@router.patch(
    "/{notification_id}/read",
    response_model=NotificationResponse,
    status_code=status.HTTP_200_OK,
    summary="Mark notification as read",
    description="Mark a specific notification as read. Updates the `is_read` field to true and sets `read_at` timestamp.",
    responses={
        200: {"description": "Notification marked as read successfully"},
        401: {"description": "Not authenticated"},
        403: {"description": "User does not have access to this notification"},
        404: {"description": "Notification not found"},
    },
)
def mark_notification_as_read(
    notification_id: int = Path(..., gt=0, description="Notification ID"),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> NotificationResponse:
    """Mark a notification as read."""
    # Get notification
    notification = crud_notification.get(db, notification_id)

    if not notification:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Notifikasi tidak ditemukan."
        )

    # Authorization: check if notification belongs to current user
    if notification.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Anda tidak memiliki akses ke notifikasi ini."
        )

    # Mark as read
    updated_notification = crud_notification.mark_as_read(
        db, notification_id=notification_id
    )

    return NotificationResponse.model_validate(updated_notification)


@router.post(
    "/mark-all-read",
    response_model=MarkAllReadResponse,
    status_code=status.HTTP_200_OK,
    summary="Mark all notifications as read",
    description="Mark all unread notifications for the current user as read. Returns the count of notifications that were marked as read.",
    responses={
        200: {"description": "All unread notifications marked as read"},
        401: {"description": "Not authenticated"},
    },
)
def mark_all_notifications_as_read(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> MarkAllReadResponse:
    """Mark all notifications as read for current user."""
    read_count = crud_notification.mark_all_as_read(db, user_id=current_user.id)

    return MarkAllReadResponse(
        message=f"{read_count} notifikasi telah ditandai sebagai sudah dibaca",
        read_count=read_count,
    )


@router.delete(
    "/{notification_id}",
    response_model=DeleteNotificationResponse,
    status_code=status.HTTP_200_OK,
    summary="Delete notification",
    description="Permanently delete a specific notification. This action cannot be undone.",
    responses={
        200: {"description": "Notification deleted successfully"},
        401: {"description": "Not authenticated"},
        403: {"description": "User does not have access to this notification"},
        404: {"description": "Notification not found"},
        500: {"description": "Database error occurred while deleting"},
    },
)
def delete_notification(
    notification_id: int = Path(..., gt=0, description="Notification ID"),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> DeleteNotificationResponse:
    """Delete a notification."""
    # Get notification
    notification = crud_notification.get(db, notification_id)

    if not notification:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Notifikasi tidak ditemukan."
        )

    # Authorization: check if notification belongs to current user
    if notification.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Anda tidak memiliki akses ke notifikasi ini."
        )

    # Delete notification (hard delete since Notification model doesn't have is_active)
    try:
        db.delete(notification)
        db.commit()
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Gagal menghapus notifikasi: {str(e)}"
        )

    return DeleteNotificationResponse(message="Notifikasi berhasil dihapus")
