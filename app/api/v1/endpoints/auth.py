"""Authentication endpoints."""

from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.api.deps import (
    get_current_active_user,
    get_db,
    require_role,
)
from app.core.security import create_access_token, verify_password
from app.crud import crud_user
from app.crud.ibu_hamil import crud_ibu_hamil
from app.crud.perawat import crud_perawat
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
    SuperAdminRegisterRequest,
    SuperAdminLoginRequest,
    SuperAdminLoginResponse,
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
    summary="Login sebagai Admin Puskesmas",
    description="""
Login endpoint khusus untuk admin puskesmas menggunakan email dan password.

## Persyaratan Login

1. **User harus memiliki role `puskesmas`**
2. **Puskesmas harus sudah disetujui** (`registration_status = 'approved'`)
3. **Puskesmas harus aktif** (`is_active = true`)

## Alur Validasi

1. Validasi email dan password
2. Cek status aktif akun user
3. Verifikasi role user adalah 'puskesmas'
4. Cari data puskesmas berdasarkan `admin_user_id`
5. Cek status registrasi puskesmas
6. Cek status aktif puskesmas
7. Generate JWT access token

## Response Sukses

Mengembalikan JWT token beserta informasi user dan puskesmas.
Token berlaku selama 30 hari.
    """,
    responses={
        200: {
            "description": "Login berhasil",
            "content": {
                "application/json": {
                    "example": {
                        "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                        "token_type": "bearer",
                        "role": "puskesmas",
                        "user": {
                            "id": 15,
                            "email": "admin@puskesmas.go.id",
                            "full_name": "Admin Puskesmas Sungai Penuh"
                        },
                        "puskesmas": {
                            "id": 1,
                            "name": "Puskesmas Sungai Penuh",
                            "registration_status": "approved",
                            "is_active": True
                        }
                    }
                }
            }
        },
        401: {
            "description": "Unauthorized - Email/password salah atau akun tidak aktif",
            "content": {
                "application/json": {
                    "examples": {
                        "invalid_credentials": {
                            "summary": "Email atau password salah",
                            "value": {"detail": "Email atau password salah"}
                        },
                        "inactive_account": {
                            "summary": "Akun tidak aktif",
                            "value": {"detail": "Akun pengguna tidak aktif"}
                        }
                    }
                }
            }
        },
        403: {
            "description": "Forbidden - Role bukan puskesmas atau puskesmas belum approved/aktif",
            "content": {
                "application/json": {
                    "examples": {
                        "wrong_role": {
                            "summary": "Bukan akun admin puskesmas",
                            "value": {"detail": "Akun ini bukan akun admin puskesmas"}
                        },
                        "draft_status": {
                            "summary": "Registrasi belum diajukan",
                            "value": {"detail": "Registrasi puskesmas belum diajukan"}
                        },
                        "pending_status": {
                            "summary": "Menunggu persetujuan",
                            "value": {"detail": "Registrasi puskesmas masih menunggu persetujuan"}
                        },
                        "rejected_status": {
                            "summary": "Registrasi ditolak",
                            "value": {"detail": "Registrasi puskesmas ditolak"}
                        },
                        "inactive_puskesmas": {
                            "summary": "Puskesmas tidak aktif",
                            "value": {"detail": "Puskesmas tidak aktif. Hubungi administrator untuk informasi lebih lanjut."}
                        }
                    }
                }
            }
        },
        404: {
            "description": "Not Found - Data puskesmas tidak ditemukan",
            "content": {
                "application/json": {
                    "example": {"detail": "Data puskesmas tidak ditemukan untuk akun ini"}
                }
            }
        },
        422: {
            "description": "Validation Error - Format request tidak valid"
        }
    },
)
async def login_puskesmas(
    login_data: PuskesmasLoginRequest,
    db: Session = Depends(get_db),
) -> PuskesmasLoginResponse:
    """
    Login endpoint untuk admin puskesmas.

    Hanya user dengan role 'puskesmas' yang dapat login melalui endpoint ini.
    Puskesmas harus sudah disetujui (approved) dan aktif.
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


@router.post(
    "/logout/puskesmas",
    response_model=dict,
    status_code=status.HTTP_200_OK,
    summary="Logout Admin Puskesmas",
    description="""
Logout endpoint untuk admin puskesmas.

## Catatan Penting

Karena sistem menggunakan JWT stateless, logout dilakukan dengan:
1. Memanggil endpoint ini untuk invalidate session di server (opsional)
2. **Client harus menghapus token dari storage** (localStorage/sessionStorage/cookies)
3. Client tidak lagi mengirim token di Authorization header

## Response

Mengembalikan konfirmasi logout berhasil beserta informasi puskesmas.
""",
    responses={
        200: {
            "description": "Logout berhasil",
            "content": {
                "application/json": {
                    "example": {
                        "message": "Logout berhasil",
                        "detail": "Token telah di-invalidate. Silakan hapus token dari client storage.",
                        "user_id": 15,
                        "email": "admin@puskesmas.go.id",
                        "puskesmas_id": 1,
                        "puskesmas_name": "Puskesmas Sungai Penuh"
                    }
                }
            }
        },
        401: {
            "description": "Unauthorized - Token tidak valid atau tidak ada",
            "content": {
                "application/json": {
                    "example": {"detail": "Could not validate credentials"}
                }
            }
        },
        403: {
            "description": "Forbidden - Bukan admin puskesmas",
            "content": {
                "application/json": {
                    "example": {"detail": "Not enough permissions. Required role(s): puskesmas"}
                }
            }
        }
    },
)
async def logout_puskesmas(
    current_user: User = Depends(require_role("puskesmas")),
    db: Session = Depends(get_db),
) -> dict:
    """
    Logout endpoint untuk admin puskesmas.
    
    Endpoint ini memvalidasi bahwa user adalah admin puskesmas yang sedang login.
    Client harus menghapus token dari storage setelah memanggil endpoint ini.
    
    Args:
        current_user: Current authenticated puskesmas admin user
        db: Database session
        
    Returns:
        dict: Success message confirming logout with puskesmas info
    """
    # Get puskesmas info
    puskesmas = crud_puskesmas.get_by_admin_user_id(db, admin_user_id=current_user.id)
    
    response_data = {
        "message": "Logout berhasil",
        "detail": "Token telah di-invalidate. Silakan hapus token dari client storage.",
        "user_id": current_user.id,
        "email": current_user.email,
    }
    
    if puskesmas:
        response_data["puskesmas_id"] = puskesmas.id
        response_data["puskesmas_name"] = puskesmas.name
    
    return response_data


@router.post(
    "/register/super-admin",
    response_model=dict,
    status_code=status.HTTP_201_CREATED,
    summary="Register Super Admin",
    description="""
Registrasi akun super admin baru.

**Catatan Penting:**
- Super admin memiliki akses untuk approve/reject registrasi puskesmas
- Super admin hanya dapat melihat data perawat dan ibu hamil (read-only)
- Super admin TIDAK dapat mengelola perawat atau assign ibu hamil
- Endpoint ini sebaiknya hanya digunakan untuk setup awal sistem
""",
)
async def register_super_admin(
    user_in: SuperAdminRegisterRequest,
    db: Session = Depends(get_db),
) -> dict:
    """
    Register a new super admin account.
    
    Args:
        user_in: Super admin registration data (email, phone, password, full_name)
        db: Database session
        
    Returns:
        dict: Created user data, access token, and token type
        
    Raises:
        HTTPException: 400 if email or phone already registered
    """
    # Check if email already exists
    existing_user_email = crud_user.get_by_email(db, email=user_in.email)
    if existing_user_email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered",
        )
    
    # Check if phone already exists
    existing_user_phone = crud_user.get_by_phone(db, phone=user_in.phone)
    if existing_user_phone:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Phone number already registered",
        )
    
    # Create super admin user
    user_data = UserCreate(
        email=user_in.email,
        phone=user_in.phone,
        password=user_in.password,
        full_name=user_in.full_name,
        role="super_admin",
    )
    db_user = crud_user.create_user(db, user_in=user_data)
    
    # Generate access token
    access_token_expires = timedelta(days=30)
    access_token = create_access_token(
        data={"sub": db_user.phone, "user_id": db_user.id, "role": db_user.role},
        expires_delta=access_token_expires,
    )
    
    return {
        "user": UserResponse.from_orm(db_user),
        "access_token": access_token,
        "token_type": "bearer",
    }


@router.post(
    "/login/super-admin",
    response_model=SuperAdminLoginResponse,
    status_code=status.HTTP_200_OK,
    summary="Login sebagai Super Admin",
    description="""
Login endpoint khusus untuk super admin menggunakan email dan password.

## Persyaratan Login

1. **User harus memiliki role `super_admin`**
2. **Akun harus aktif** (`is_active = true`)

## Alur Validasi

1. Validasi email dan password
2. Cek status aktif akun user
3. Verifikasi role user adalah 'super_admin'
4. Generate JWT access token

## Response Sukses

Mengembalikan JWT token beserta informasi user.
Token berlaku selama 30 hari.

## Akses Super Admin

- ✅ Dapat approve/reject registrasi puskesmas
- ✅ Dapat melihat data puskesmas, perawat, dan ibu hamil (read-only)
- ❌ TIDAK dapat mengelola perawat
- ❌ TIDAK dapat assign ibu hamil ke puskesmas atau perawat
""",
    responses={
        200: {
            "description": "Login berhasil",
            "content": {
                "application/json": {
                    "example": {
                        "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                        "token_type": "bearer",
                        "role": "super_admin",
                        "user": {
                            "id": 1,
                            "email": "superadmin@wellmom.go.id",
                            "full_name": "Super Admin WellMom"
                        }
                    }
                }
            }
        },
        401: {
            "description": "Unauthorized - Email/password salah atau akun tidak aktif",
            "content": {
                "application/json": {
                    "examples": {
                        "invalid_credentials": {
                            "summary": "Email atau password salah",
                            "value": {"detail": "Email atau password salah"}
                        },
                        "inactive_account": {
                            "summary": "Akun tidak aktif",
                            "value": {"detail": "Akun pengguna tidak aktif"}
                        }
                    }
                }
            }
        },
        403: {
            "description": "Forbidden - Role bukan super_admin",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "Akun ini bukan akun super admin"
                    }
                }
            }
        },
        422: {
            "description": "Validation Error - Format request tidak valid"
        }
    },
)
async def login_super_admin(
    login_data: SuperAdminLoginRequest,
    db: Session = Depends(get_db),
) -> SuperAdminLoginResponse:
    """
    Login endpoint untuk super admin.

    Hanya user dengan role 'super_admin' yang dapat login melalui endpoint ini.
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

    # Step 3: Verify user has super_admin role
    if user.role != "super_admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Akun ini bukan akun super admin",
        )

    # Step 4: Generate access token
    access_token_expires = timedelta(days=30)
    access_token = create_access_token(
        data={"sub": user.phone, "user_id": user.id, "role": user.role},
        expires_delta=access_token_expires,
    )

    # Step 5: Build response
    return SuperAdminLoginResponse(
        access_token=access_token,
        token_type="bearer",
        role=user.role,
        user=PuskesmasLoginUserInfo(
            id=user.id,
            email=user.email,
            full_name=user.full_name,
        ),
    )


@router.post(
    "/logout/super-admin",
    response_model=dict,
    status_code=status.HTTP_200_OK,
    summary="Logout Super Admin",
    description="""
Logout endpoint untuk super admin.

## Catatan Penting

Karena sistem menggunakan JWT stateless, logout dilakukan dengan:
1. Memanggil endpoint ini untuk invalidate session di server (opsional)
2. **Client harus menghapus token dari storage** (localStorage/sessionStorage/cookies)
3. Client tidak lagi mengirim token di Authorization header

## Response

Mengembalikan konfirmasi logout berhasil.
""",
    responses={
        200: {
            "description": "Logout berhasil",
            "content": {
                "application/json": {
                    "example": {
                        "message": "Logout berhasil",
                        "detail": "Token telah di-invalidate. Silakan hapus token dari client storage."
                    }
                }
            }
        },
        401: {
            "description": "Unauthorized - Token tidak valid atau tidak ada",
            "content": {
                "application/json": {
                    "example": {"detail": "Could not validate credentials"}
                }
            }
        },
        403: {
            "description": "Forbidden - Bukan super admin",
            "content": {
                "application/json": {
                    "example": {"detail": "Not enough permissions. Required role(s): super_admin"}
                }
            }
        }
    },
)
async def logout_super_admin(
    current_user: User = Depends(require_role("super_admin")),
) -> dict:
    """
    Logout endpoint untuk super admin.
    
    Endpoint ini memvalidasi bahwa user adalah super admin yang sedang login.
    Client harus menghapus token dari storage setelah memanggil endpoint ini.
    
    Args:
        current_user: Current authenticated super admin user
        
    Returns:
        dict: Success message confirming logout
    """
    return {
        "message": "Logout berhasil",
        "detail": "Token telah di-invalidate. Silakan hapus token dari client storage.",
        "user_id": current_user.id,
        "email": current_user.email,
    }


@router.post(
    "/logout/perawat",
    response_model=dict,
    status_code=status.HTTP_200_OK,
    summary="Logout Perawat",
    description="""
Logout endpoint untuk perawat.

## Catatan Penting

Karena sistem menggunakan JWT stateless, logout dilakukan dengan:
1. Memanggil endpoint ini untuk invalidate session di server (opsional)
2. **Client harus menghapus token dari storage** (localStorage/sessionStorage/cookies)
3. Client tidak lagi mengirim token di Authorization header

## Response

Mengembalikan konfirmasi logout berhasil beserta informasi perawat.
""",
    responses={
        200: {
            "description": "Logout berhasil",
            "content": {
                "application/json": {
                    "example": {
                        "message": "Logout berhasil",
                        "detail": "Token telah di-invalidate. Silakan hapus token dari client storage.",
                        "user_id": 20,
                        "email": "perawat@example.com",
                        "perawat_id": 5,
                        "nama_lengkap": "Nurse Name"
                    }
                }
            }
        },
        401: {
            "description": "Unauthorized - Token tidak valid atau tidak ada",
            "content": {
                "application/json": {
                    "example": {"detail": "Could not validate credentials"}
                }
            }
        },
        403: {
            "description": "Forbidden - Bukan perawat",
            "content": {
                "application/json": {
                    "example": {"detail": "Not enough permissions. Required role(s): perawat"}
                }
            }
        }
    },
)
async def logout_perawat(
    current_user: User = Depends(require_role("perawat")),
    db: Session = Depends(get_db),
) -> dict:
    """
    Logout endpoint untuk perawat.
    
    Endpoint ini memvalidasi bahwa user adalah perawat yang sedang login.
    Client harus menghapus token dari storage setelah memanggil endpoint ini.
    
    Args:
        current_user: Current authenticated perawat user
        db: Database session
        
    Returns:
        dict: Success message confirming logout with perawat info
    """
    # Get perawat info
    perawat = crud_perawat.get_by_field(db, "user_id", current_user.id)
    
    response_data = {
        "message": "Logout berhasil",
        "detail": "Token telah di-invalidate. Silakan hapus token dari client storage.",
        "user_id": current_user.id,
        "email": current_user.email,
    }
    
    if perawat:
        response_data["perawat_id"] = perawat.id
        response_data["nama_lengkap"] = perawat.nama_lengkap
    
    return response_data


@router.post(
    "/logout/ibu-hamil",
    response_model=dict,
    status_code=status.HTTP_200_OK,
    summary="Logout Ibu Hamil",
    description="""
Logout endpoint untuk ibu hamil.

## Catatan Penting

Karena sistem menggunakan JWT stateless, logout dilakukan dengan:
1. Memanggil endpoint ini untuk invalidate session di server (opsional)
2. **Client harus menghapus token dari storage** (localStorage/sessionStorage/cookies)
3. Client tidak lagi mengirim token di Authorization header

## Response

Mengembalikan konfirmasi logout berhasil beserta informasi ibu hamil.
""",
    responses={
        200: {
            "description": "Logout berhasil",
            "content": {
                "application/json": {
                    "example": {
                        "message": "Logout berhasil",
                        "detail": "Token telah di-invalidate. Silakan hapus token dari client storage.",
                        "user_id": 25,
                        "phone": "+6281234567890",
                        "ibu_hamil_id": 10,
                        "nama_lengkap": "Ibu Name"
                    }
                }
            }
        },
        401: {
            "description": "Unauthorized - Token tidak valid atau tidak ada",
            "content": {
                "application/json": {
                    "example": {"detail": "Could not validate credentials"}
                }
            }
        },
        403: {
            "description": "Forbidden - Bukan ibu hamil",
            "content": {
                "application/json": {
                    "example": {"detail": "Not enough permissions. Required role(s): ibu_hamil"}
                }
            }
        }
    },
)
async def logout_ibu_hamil(
    current_user: User = Depends(require_role("ibu_hamil")),
    db: Session = Depends(get_db),
) -> dict:
    """
    Logout endpoint untuk ibu hamil.
    
    Endpoint ini memvalidasi bahwa user adalah ibu hamil yang sedang login.
    Client harus menghapus token dari storage setelah memanggil endpoint ini.
    
    Args:
        current_user: Current authenticated ibu hamil user
        db: Database session
        
    Returns:
        dict: Success message confirming logout with ibu hamil info
    """
    # Get ibu hamil info
    ibu_hamil = crud_ibu_hamil.get_by_field(db, "user_id", current_user.id)
    
    response_data = {
        "message": "Logout berhasil",
        "detail": "Token telah di-invalidate. Silakan hapus token dari client storage.",
        "user_id": current_user.id,
        "phone": current_user.phone,
    }
    
    if ibu_hamil:
        response_data["ibu_hamil_id"] = ibu_hamil.id
        response_data["nama_lengkap"] = ibu_hamil.nama_lengkap
    
    return response_data


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
