"""User endpoints."""

import logging
from datetime import datetime
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.api import deps
from app.models.user import User
from app.schemas.user import FCMTokenUpdate
from app.api.deps import (
    get_current_active_user,
    get_db,
    require_role,
)
from app.crud import crud_user
from app.models.user import User
from app.schemas.user import FCMTokenUpdate, UserResponse, UserUpdate

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/users",
    tags=["Users"],
)


@router.get(
    "",
    response_model=List[UserResponse],
    status_code=status.HTTP_200_OK,
    summary="List all users",
)
async def list_users(
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(require_role("super_admin")),
    db: Session = Depends(get_db),
) -> List[User]:
    """
    Get list of all users (admin atau super admin - read-only untuk super admin).
    
    Args:
        skip: Number of records to skip (pagination)
        limit: Maximum records to return
        current_user: Current admin/super admin user (injected via require_role)
        db: Database session
        
    Returns:
        List[User]: List of user data
    """
    users = crud_user.get_multi(db, skip=skip, limit=limit)
    return users


@router.get(
    "/me",
    response_model=UserResponse,
    status_code=status.HTTP_200_OK,
    summary="Get current user info",
)
async def get_current_user_info(
    current_user: User = Depends(get_current_active_user),
) -> User:
    """
    Get current authenticated user information.
    
    Args:
        current_user: Current active user (injected via JWT token)
        
    Returns:
        User: Current user data
    """
    return current_user


@router.get(
    "/{user_id}",
    response_model=UserResponse,
    status_code=status.HTTP_200_OK,
    summary="Get user by ID",
)
async def get_user(
    user_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> User:
    """
    Get user by ID (admin or self).
    
    Args:
        user_id: User ID to retrieve
        current_user: Current authenticated user
        db: Database session
        
    Returns:
        User: User data
        
    Raises:
        HTTPException: 404 if user not found, 403 if not authorized
    """
    # Check authorization: super admin (read-only), or self
    if current_user.id != user_id and current_user.role != "super_admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to view this user",
        )
    
    user = crud_user.get(db, id=user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )
    
    return user


@router.patch(
    "/{user_id}",
    response_model=UserResponse,
    status_code=status.HTTP_200_OK,
    summary="Update user",
)
async def update_user(
    user_id: int,
    user_update: UserUpdate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> User:
    """
    Update user information (admin or self).
    
    Args:
        user_id: User ID to update
        user_update: Update data (phone, full_name, role - optional fields)
        current_user: Current authenticated user
        db: Database session
        
    Returns:
        User: Updated user data
        
    Raises:
        HTTPException: 404 if user not found, 403 if not authorized, 400 if phone already in use
    """
    # Check authorization: self only (super admin tidak dapat update user lain)
    if current_user.id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to update this user. Hanya dapat update data sendiri.",
        )
    
    # Get existing user
    db_user = crud_user.get(db, id=user_id)
    if not db_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )
    
    # Check if new phone is already in use (if changing phone)
    if user_update.phone and user_update.phone != db_user.phone:
        existing_user = crud_user.get_by_phone(db, phone=user_update.phone)
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Phone number already in use",
            )
    
    # Update user
    updated_user = crud_user.update(db, db_obj=db_user, obj_in=user_update)
    return updated_user


@router.delete(
    "/{user_id}",
    response_model=dict,
    status_code=status.HTTP_200_OK,
    summary="Deactivate user",
)
async def delete_user(
    user_id: int,
    current_user: User = Depends(require_role("super_admin")),
    db: Session = Depends(get_db),
) -> dict:
    """
    Deactivate (soft delete) a user (admin only).
    
    Sets user.is_active = False instead of permanently deleting.
    
    Args:
        user_id: User ID to deactivate
        current_user: Current admin user
        db: Database session
        
    Returns:
        dict: Success message
        
    Raises:
        HTTPException: 404 if user not found
    """
    db_user = crud_user.get(db, id=user_id)
    if not db_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )
    
    # Soft delete via deactivate
    crud_user.deactivate(db, user_id=user_id)
    
    return {"message": "User deactivated successfully"}


@router.patch(
    "/me/fcm-token",
    response_model=UserResponse,
    status_code=status.HTTP_200_OK,
    summary="Update FCM token",
    description="""
    Update FCM token for push notifications.
    
    This endpoint allows mobile apps (Flutter) to register or update their FCM token.
    The token will be used to send push notifications to the device.
    """,
)
async def update_fcm_token(
    token_data: FCMTokenUpdate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> User:
    """
    Update FCM token for push notifications.

    Args:
        token_data: FCM token data containing the token string
        current_user: Current active user (injected via JWT token)
        db: Database session

    Returns:
        User: Updated user data with new FCM token

    Raises:
        HTTPException: If database update fails
    """
    try:
        current_user.fcm_token = token_data.fcm_token
        current_user.fcm_token_updated_at = datetime.utcnow()
        db.add(current_user)
        db.commit()
        db.refresh(current_user)
        
        # Log untuk debugging di VPS
        print(f"DEBUG: FCM Token updated for user {current_user.id}")
        logger.info(f"FCM token updated for user_id={current_user.id}")
        return current_user
    except Exception as e:
        db.rollback()
        print(f"❌ [BACKEND] Error updating token: {str(e)}")
        logger.error(f"Failed to update FCM token for user_id={current_user.id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Gagal memperbarui FCM token"
        )


# Alias PUT untuk kompatibilitas dengan beberapa klien
@router.put(
    "/me/fcm-token",
    response_model=UserResponse,
    status_code=status.HTTP_200_OK,
    summary="Update FCM token (alias PUT)",
    include_in_schema=False,  # Hidden dari docs untuk menghindari duplikasi
)
async def update_fcm_token_put(
    token_data: FCMTokenUpdate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> User:
    """Alias PUT untuk update_fcm_token - delegasi ke handler PATCH."""
    return await update_fcm_token(token_data, current_user, db)


__all__ = ["router"]