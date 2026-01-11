"""Kerabat (Family Member) endpoints."""

from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_active_user, get_db
from app.core.security import create_access_token
from app.crud import crud_kerabat, crud_user
from app.models.ibu_hamil import IbuHamil
from app.models.kerabat import KerabatIbuHamil
from app.models.user import User
from app.schemas.kerabat import (
    InviteCodeGenerateResponse,
    InviteCodeLoginRequest,
    InviteCodeLoginResponse,
    KerabatCompleteProfileRequest,
    KerabatResponse,
    KerabatUpdate,
)

router = APIRouter(
    prefix="/kerabat",
    tags=["Kerabat (Family Member)"],
)


@router.post(
    "/generate-invite",
    response_model=InviteCodeGenerateResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Generate invitation code untuk kerabat",
    description="""
Generate invitation code untuk mengundang kerabat.

**Akses:**
- Hanya dapat diakses oleh ibu hamil yang sedang login (role: ibu_hamil)
- Hanya dapat generate invite untuk dirinya sendiri

**Fitur:**
- Invitation code berlaku selama 24 jam
- Setiap generate akan membuat invitation code baru
- Kerabat yang menggunakan invitation code akan otomatis memiliki akses:
  - `can_view_records = True`
  - `can_receive_notifications = True`
""",
    responses={
        201: {
            "description": "Invitation code berhasil di-generate",
            "content": {
                "application/json": {
                    "example": {
                        "invite_code": "ABC123XY",
                        "expires_at": "2025-01-02T10:00:00Z",
                        "ibu_hamil_id": 1
                    }
                }
            }
        },
        403: {
            "description": "Bukan akun ibu hamil",
            "content": {
                "application/json": {
                    "example": {"detail": "Hanya ibu hamil yang dapat mengakses endpoint ini"}
                }
            }
        },
        404: {
            "description": "Profil ibu hamil tidak ditemukan",
            "content": {
                "application/json": {
                    "example": {"detail": "Profil Ibu Hamil tidak ditemukan"}
                }
            }
        }
    }
)
async def generate_invite_code(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> InviteCodeGenerateResponse:
    """
    Generate invitation code untuk mengundang kerabat.
    
    Args:
        current_user: User yang sedang login (harus role ibu_hamil)
        db: Database session
        
    Returns:
        InviteCodeGenerateResponse: Invitation code dan expiration time
        
    Raises:
        HTTPException 403: Jika bukan role ibu_hamil
        HTTPException 404: Jika profil ibu hamil tidak ditemukan
    """
    # Hanya ibu hamil yang dapat mengakses
    if current_user.role != "ibu_hamil":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Hanya ibu hamil yang dapat mengakses endpoint ini",
        )
    
    # Find IbuHamil linked to current user
    ibu = db.scalars(select(IbuHamil).where(IbuHamil.user_id == current_user.id)).first()
    if not ibu:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Profil Ibu Hamil tidak ditemukan",
        )
    
    # Generate invitation code
    kerabat = crud_kerabat.generate_invite_code_for_ibu_hamil(db, ibu_hamil_id=ibu.id)
    
    return InviteCodeGenerateResponse(
        invite_code=kerabat.invite_code,
        expires_at=kerabat.invite_code_expires_at,
        ibu_hamil_id=ibu.id,
    )


@router.post(
    "/login-with-invite",
    response_model=InviteCodeLoginResponse,
    status_code=status.HTTP_200_OK,
    summary="Login kerabat dengan invitation code",
    description="""
Login kerabat menggunakan invitation code.

**Flow:**
1. Kerabat memasukkan invitation code
2. Sistem verifikasi invitation code (valid, tidak expired, belum digunakan)
3. Jika valid, buat user account dengan role 'kerabat' (jika belum ada)
4. Link kerabat dengan ibu hamil
5. Generate access token
6. Return response dengan flag `requires_profile_completion = True`

**Langkah Selanjutnya:**
- Kerabat perlu memanggil endpoint `/kerabat/complete-profile` untuk mengisi nama dan relasi
""",
    responses={
        200: {
            "description": "Login berhasil",
            "content": {
                "application/json": {
                    "example": {
                        "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                        "token_type": "bearer",
                        "kerabat_id": 1,
                        "ibu_hamil_id": 1,
                        "ibu_hamil_name": "Siti Aminah",
                        "requires_profile_completion": True
                    }
                }
            }
        },
        400: {
            "description": "Invitation code tidak valid",
            "content": {
                "application/json": {
                    "examples": {
                        "invalid_code": {
                            "summary": "Invitation code tidak ditemukan",
                            "value": {"detail": "Invitation code tidak valid atau tidak ditemukan"}
                        },
                        "expired": {
                            "summary": "Invitation code sudah expired",
                            "value": {"detail": "Invitation code sudah expired. Silakan minta invitation code baru dari ibu hamil."}
                        },
                        "already_used": {
                            "summary": "Invitation code sudah digunakan",
                            "value": {"detail": "Invitation code sudah digunakan. Silakan minta invitation code baru dari ibu hamil."}
                        }
                    }
                }
            }
        }
    }
)
async def login_with_invite_code(
    payload: InviteCodeLoginRequest,
    db: Session = Depends(get_db),
) -> InviteCodeLoginResponse:
    """
    Login kerabat menggunakan invitation code.
    
    Args:
        payload: Invitation code
        db: Database session
        
    Returns:
        InviteCodeLoginResponse: Access token dan informasi kerabat
        
    Raises:
        HTTPException 400: Invitation code tidak valid, expired, atau sudah digunakan
    """
    # Verify invitation code
    kerabat = crud_kerabat.verify_invite_code(db, invite_code=payload.invite_code)
    if not kerabat:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invitation code tidak valid, sudah expired, atau sudah digunakan. Silakan minta invitation code baru dari ibu hamil.",
        )
    
    # Get ibu hamil info
    ibu_hamil = db.get(IbuHamil, kerabat.ibu_hamil_id)
    if not ibu_hamil:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Ibu hamil tidak ditemukan",
        )
    
    # Check if user already exists (if kerabat_user_id is set)
    if kerabat.kerabat_user_id:
        # User already exists, just generate token
        user = db.get(User, kerabat.kerabat_user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User tidak ditemukan",
            )
    else:
        # Create new user account with role 'kerabat'
        # Generate temporary phone number based on invite code (unique)
        # Format: +62 + invite_code (8 chars) + random 4 digits
        import random
        random_suffix = f"{random.randint(1000, 9999)}"
        temp_phone = f"+62{kerabat.invite_code}{random_suffix}"
        
        # Ensure phone is unique (retry if needed)
        max_attempts = 5
        for attempt in range(max_attempts):
            existing_user = crud_user.get_by_phone(db, phone=temp_phone)
            if not existing_user:
                break
            if attempt < max_attempts - 1:
                random_suffix = f"{random.randint(1000, 9999)}"
                temp_phone = f"+62{kerabat.invite_code}{random_suffix}"
        
        # Create new user
        from app.schemas.user import UserCreate
        user_data = UserCreate(
            phone=temp_phone,
            password=kerabat.invite_code,  # Temporary password = invite code
            full_name="Kerabat",  # Temporary name, will be updated later
            role="kerabat",
            email=None,
        )
        try:
            user = crud_user.create_user(db, user_in=user_data)
        except Exception as e:
            db.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Gagal membuat akun user: {str(e)}",
            )
        
        # Check if this user is already linked to this ibu hamil
        existing_link = crud_kerabat.check_duplicate_kerabat(
            db, kerabat_user_id=user.id, ibu_hamil_id=kerabat.ibu_hamil_id
        )
        if existing_link:
            # Use existing link
            kerabat = existing_link
        else:
            # Link kerabat with user
            kerabat.kerabat_user_id = user.id
            db.add(kerabat)
            try:
                db.commit()
                db.refresh(kerabat)
            except Exception as e:
                db.rollback()
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Gagal menghubungkan kerabat dengan user: {str(e)}",
                )
    
    # Generate access token
    access_token = create_access_token({"sub": str(user.phone)})
    
    # Check if profile needs completion
    requires_completion = kerabat.relation_type is None or user.full_name == "Kerabat"
    
    return InviteCodeLoginResponse(
        access_token=access_token,
        token_type="bearer",
        kerabat_id=kerabat.id,
        ibu_hamil_id=ibu_hamil.id,
        ibu_hamil_name=ibu_hamil.nama_lengkap,
        requires_profile_completion=requires_completion,
    )


@router.post(
    "/complete-profile",
    response_model=KerabatResponse,
    status_code=status.HTTP_200_OK,
    summary="Complete profile kerabat setelah login",
    description="""
Complete profile kerabat setelah login dengan invitation code.

**Akses:**
- Hanya dapat diakses oleh kerabat yang sedang login (role: kerabat)
- Hanya dapat complete profile untuk dirinya sendiri

**Field yang diisi:**
- full_name: Nama lengkap kerabat
- relation_type: Relasi kepada ibu hamil (contoh: Suami, Ibu, Ayah, dll)
- phone: Nomor telepon (optional, bisa diisi nanti)
""",
    responses={
        200: {
            "description": "Profile berhasil di-complete",
            "content": {
                "application/json": {
                    "example": {
                        "id": 1,
                        "kerabat_user_id": 25,
                        "ibu_hamil_id": 1,
                        "relation_type": "Suami",
                        "can_view_records": True,
                        "can_receive_notifications": True,
                        "created_at": "2025-01-01T10:00:00Z"
                    }
                }
            }
        },
        400: {
            "description": "Data tidak valid",
            "content": {
                "application/json": {
                    "example": {"detail": "Anda belum login dengan invitation code atau sudah complete profile"}
                }
            }
        },
        403: {
            "description": "Bukan akun kerabat",
            "content": {
                "application/json": {
                    "example": {"detail": "Hanya kerabat yang dapat mengakses endpoint ini"}
                }
            }
        },
        404: {
            "description": "Kerabat tidak ditemukan",
            "content": {
                "application/json": {
                    "example": {"detail": "Kerabat tidak ditemukan"}
                }
            }
        }
    }
)
async def complete_profile(
    profile_data: KerabatCompleteProfileRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> KerabatResponse:
    """
    Complete profile kerabat setelah login dengan invitation code.
    
    Args:
        profile_data: Data profile kerabat (full_name, relation_type, phone)
        current_user: User yang sedang login (harus role kerabat)
        db: Database session
        
    Returns:
        KerabatResponse: Data kerabat yang sudah di-update
        
    Raises:
        HTTPException 400: Data tidak valid atau sudah complete
        HTTPException 403: Jika bukan role kerabat
        HTTPException 404: Jika kerabat tidak ditemukan
    """
    # Hanya kerabat yang dapat mengakses
    if current_user.role != "kerabat":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Hanya kerabat yang dapat mengakses endpoint ini",
        )
    
    # Find kerabat relationship
    kerabat = db.scalars(
        select(KerabatIbuHamil).where(KerabatIbuHamil.kerabat_user_id == current_user.id)
    ).first()
    
    if not kerabat:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Kerabat tidak ditemukan. Pastikan Anda sudah login dengan invitation code.",
        )
    
    # Check if already completed (boleh update jika masih "Kerabat" atau relation_type masih null)
    if kerabat.relation_type and current_user.full_name != "Kerabat" and current_user.full_name:
        # Boleh update jika ada perubahan
        pass
    
    # Update user full_name
    if profile_data.full_name:
        current_user.full_name = profile_data.full_name
        db.add(current_user)
    
    # Update user phone if provided
    if profile_data.phone:
        # Check if phone already exists
        existing_user = crud_user.get_by_phone(db, phone=profile_data.phone)
        if existing_user and existing_user.id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Nomor telepon sudah terdaftar di sistem",
            )
        current_user.phone = profile_data.phone
        db.add(current_user)
    
    # Update kerabat relation_type
    kerabat.relation_type = profile_data.relation_type
    db.add(kerabat)
    
    try:
        db.commit()
        db.refresh(kerabat)
        db.refresh(current_user)
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Gagal mengupdate profile: {str(e)}",
        )
    
    return KerabatResponse.model_validate(kerabat)


@router.get(
    "/my-kerabat",
    response_model=List[KerabatResponse],
    status_code=status.HTTP_200_OK,
    summary="Daftar kerabat untuk ibu hamil",
    description="""
Mendapatkan daftar semua kerabat yang terhubung dengan ibu hamil yang sedang login.

**Akses:**
- Hanya dapat diakses oleh ibu hamil yang sedang login (role: ibu_hamil)
""",
)
async def get_my_kerabat(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> List[KerabatResponse]:
    """
    Mendapatkan daftar semua kerabat yang terhubung dengan ibu hamil.
    
    Args:
        current_user: User yang sedang login (harus role ibu_hamil)
        db: Database session
        
    Returns:
        List[KerabatResponse]: Daftar kerabat
    """
    # Hanya ibu hamil yang dapat mengakses
    if current_user.role != "ibu_hamil":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Hanya ibu hamil yang dapat mengakses endpoint ini",
        )
    
    # Find IbuHamil linked to current user
    ibu = db.scalars(select(IbuHamil).where(IbuHamil.user_id == current_user.id)).first()
    if not ibu:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Profil Ibu Hamil tidak ditemukan",
        )
    
    # Get all kerabat
    kerabat_list = crud_kerabat.get_by_ibu_hamil(db, ibu_hamil_id=ibu.id)
    
    return [KerabatResponse.model_validate(k) for k in kerabat_list]


__all__ = ["router"]
