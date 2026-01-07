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
from app.crud.puskesmas import crud_puskesmas
from app.models.user import User
from app.schemas.user import (
    UserCreate,
    UserLogin,
    UserResponse,
    PuskesmasLoginRequest,
    PuskesmasLoginResponse,
    PuskesmasLoginUserInfo,
    PuskesmasLoginPuskesmasInfo,
)

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


@router.post(
    "/login/puskesmas",
    response_model=PuskesmasLoginResponse,
    status_code=status.HTTP_200_OK,
    summary="Login as Puskesmas Admin",
)
async def login_puskesmas(
    login_data: PuskesmasLoginRequest,
    db: Session = Depends(get_db),
) -> PuskesmasLoginResponse:
    """
    Login endpoint for Puskesmas admin users.

    Only users with role 'puskesmas' can login through this endpoint.
    The puskesmas must be approved and active.

    Args:
        login_data: Email and password credentials
        db: Database session

    Returns:
        PuskesmasLoginResponse: Access token and puskesmas info

    Raises:
        HTTPException:
            - 401 if email/password invalid
            - 403 if role is not 'puskesmas' or puskesmas not approved/active
            - 404 if no puskesmas record found for this user
    """
    # Step 1: Authenticate user by email and password
    user = crud_user.authenticate_by_email(db, email=login_data.email, password=login_data.password)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email atau password salah",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Step 2: Check if user account is active
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Akun pengguna tidak aktif",
        )

    # Step 3: Verify user has puskesmas role
    if user.role != "puskesmas":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Akun ini bukan akun admin puskesmas",
        )

    # Step 4: Get puskesmas record linked to this user
    puskesmas = crud_puskesmas.get_by_admin_user_id(db, admin_user_id=user.id)

    if not puskesmas:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Data puskesmas tidak ditemukan untuk akun ini",
        )

    # Step 5: Check puskesmas registration status
    if puskesmas.registration_status != "approved":
        status_messages = {
            "draft": "Registrasi puskesmas belum diajukan",
            "pending_approval": "Registrasi puskesmas masih menunggu persetujuan",
            "rejected": "Registrasi puskesmas ditolak",
        }
        message = status_messages.get(
            puskesmas.registration_status,
            f"Status registrasi puskesmas: {puskesmas.registration_status}"
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=message,
        )

    # Step 6: Check puskesmas is_active status
    if not puskesmas.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Puskesmas tidak aktif. Hubungi administrator untuk informasi lebih lanjut.",
        )

    # Step 7: Generate access token
    access_token_expires = timedelta(days=30)
    access_token = create_access_token(
        data={"sub": user.phone, "user_id": user.id, "role": user.role},
        expires_delta=access_token_expires,
    )

    # Step 8: Build response
    return PuskesmasLoginResponse(
        access_token=access_token,
        token_type="bearer",
        role=user.role,
        user=PuskesmasLoginUserInfo(
            id=user.id,
            email=user.email,
            full_name=user.full_name,
        ),
        puskesmas=PuskesmasLoginPuskesmasInfo(
            id=puskesmas.id,
            name=puskesmas.name,
            registration_status=puskesmas.registration_status,
            is_active=puskesmas.is_active,
        ),
    )


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
