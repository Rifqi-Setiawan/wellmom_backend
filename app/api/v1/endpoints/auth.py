"""Authentication endpoints."""

from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.api.deps import (
    get_current_active_user,
    get_db,
)
from app.core.security import create_access_token, verify_password
from app.crud import crud_user
from app.models.user import User
from app.schemas.user import UserCreate, UserLogin, UserResponse

router = APIRouter(
    prefix="/auth",
    tags=["Authentication"],
)


@router.post(
    "/register",
    response_model=dict,
    status_code=status.HTTP_201_CREATED,
    summary="Register new user",
)
async def register(
    user_in: UserCreate,
    db: Session = Depends(get_db),
) -> dict:
    """
    Register a new user.
    
    Args:
        user_in: User creation data (phone, password, full_name, role)
        db: Database session
        
    Returns:
        dict: Created user data, access token, and token type
        
    Raises:
        HTTPException: 400 if phone already registered
    """
    # Check if user already exists
    existing_user = crud_user.get_by_phone(db, phone=user_in.phone)
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Phone number already registered",
        )
    
    # Create new user
    db_user = crud_user.create_user(db, user_in=user_in)
    
    # Generate access token
    access_token_expires = timedelta(days=30)
    access_token = create_access_token(
        data={"sub": db_user.phone},
        expires_delta=access_token_expires,
    )
    
    return {
        "user": UserResponse.from_orm(db_user),
        "access_token": access_token,
        "token_type": "bearer",
    }


@router.post(
    "/login",
    response_model=dict,
    status_code=status.HTTP_200_OK,
    summary="Login user",
)
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
) -> dict:
    """
    Login with phone number and password.
    
    OAuth2 compatible endpoint that returns access token.
    
    Args:
        form_data: OAuth2 form data (username=phone, password)
        db: Database session
        
    Returns:
        dict: Access token and token type
        
    Raises:
        HTTPException: 401 if credentials invalid
    """
    # Get user by phone (username field contains phone)
    user = crud_user.get_by_phone(db, phone=form_data.username)
    
    if not user or not verify_password(form_data.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect phone or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User account is inactive",
        )
    
    # Generate access token
    access_token_expires = timedelta(days=30)
    access_token = create_access_token(
        data={"sub": user.phone},
        expires_delta=access_token_expires,
    )
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
    }


@router.get(
    "/me",
    response_model=UserResponse,
    status_code=status.HTTP_200_OK,
    summary="Get current user info",
)
async def get_me(
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


__all__ = ["router"]
