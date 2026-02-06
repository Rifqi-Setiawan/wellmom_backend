"""Kerabat (Family Member) endpoints."""

import logging
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status

logger = logging.getLogger(__name__)
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_active_user, get_db
from app.core.security import create_access_token
from app.crud import crud_kerabat, crud_user
from app.crud.health_record import crud_health_record
from app.crud.notification import crud_notification
from app.models.ibu_hamil import IbuHamil
from app.models.kerabat import KerabatIbuHamil
from app.models.perawat import Perawat
from app.models.puskesmas import Puskesmas
from app.models.user import User
from app.schemas.kerabat import (
    EmergencyContact,
    IbuHamilSummary,
    InviteCodeGenerateResponse,
    InviteCodeLoginRequest,
    InviteCodeLoginResponse,
    KerabatCompleteProfileRequest,
    KerabatCompleteProfileResponse,
    KerabatDashboardResponse,
    KerabatHealthRecordListResponse,
    KerabatNotificationListResponse,
    KerabatProfileResponse,
    KerabatResponse,
    KerabatUpdate,
    LatestHealthRecordSummary,
    MarkNotificationReadRequest,
    MarkNotificationReadResponse,
)
from app.schemas.health_record import HealthRecordResponse
from app.schemas.notification import NotificationResponse

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
        # Generate temporary phone number using only digits (for phone validation)
        # Format: +62 + "9999" (kerabat prefix) + random 8 digits = 12 digits total
        import random
        random_digits = f"{random.randint(10000000, 99999999)}"
        temp_phone = f"+629999{random_digits}"

        # Ensure phone is unique (retry if needed)
        max_attempts = 5
        for attempt in range(max_attempts):
            existing_user = crud_user.get_by_phone(db, phone=temp_phone)
            if not existing_user:
                break
            if attempt < max_attempts - 1:
                random_digits = f"{random.randint(10000000, 99999999)}"
                temp_phone = f"+629999{random_digits}"
        
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

    # Debug logging
    logger.info(f"[KERABAT_LOGIN] User created/found: id={user.id}, phone={user.phone}, role={user.role}")
    logger.info(f"[KERABAT_LOGIN] Token generated with sub={user.phone}")
    logger.info(f"[KERABAT_LOGIN] Kerabat: id={kerabat.id}, kerabat_user_id={kerabat.kerabat_user_id}")

    # Verify user can be found by phone (sanity check)
    verify_user = crud_user.get_by_phone(db, phone=user.phone)
    if verify_user:
        logger.info(f"[KERABAT_LOGIN] Verification: User found by phone lookup, id={verify_user.id}")
    else:
        logger.error(f"[KERABAT_LOGIN] Verification FAILED: User NOT found by phone={user.phone}")

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
    response_model=KerabatCompleteProfileResponse,
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

**PENTING:** Jika phone diisi/diupdate, response akan menyertakan `access_token` baru.
Frontend HARUS menyimpan dan menggunakan token baru ini untuk request selanjutnya.
""",
    responses={
        200: {
            "description": "Profile berhasil di-complete",
            "content": {
                "application/json": {
                    "example": {
                        "kerabat": {
                            "id": 1,
                            "kerabat_user_id": 25,
                            "ibu_hamil_id": 1,
                            "relation_type": "Suami",
                            "can_view_records": True,
                            "can_receive_notifications": True
                        },
                        "access_token": "eyJhbGciOiJIUzI1NiIs...",
                        "token_type": "bearer",
                        "message": "Profile berhasil diupdate. Gunakan access_token baru."
                    }
                }
            }
        },
        400: {
            "description": "Data tidak valid",
            "content": {
                "application/json": {
                    "example": {"detail": "Nomor telepon sudah terdaftar di sistem"}
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
) -> KerabatCompleteProfileResponse:
    """
    Complete profile kerabat setelah login dengan invitation code.

    Args:
        profile_data: Data profile kerabat (full_name, relation_type, phone)
        current_user: User yang sedang login (harus role kerabat)
        db: Database session

    Returns:
        KerabatCompleteProfileResponse: Data kerabat + token baru jika phone diupdate

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

    # Track if phone was updated (need to generate new token)
    phone_updated = False
    old_phone = current_user.phone

    # Update user full_name
    if profile_data.full_name:
        current_user.full_name = profile_data.full_name
        db.add(current_user)

    # Update user phone if provided
    if profile_data.phone and profile_data.phone != current_user.phone:
        # Check if phone already exists
        existing_user = crud_user.get_by_phone(db, phone=profile_data.phone)
        if existing_user and existing_user.id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Nomor telepon sudah terdaftar di sistem",
            )
        current_user.phone = profile_data.phone
        phone_updated = True
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

    # Generate new token if phone was updated
    new_token = None
    message = "Profile berhasil diupdate"
    if phone_updated:
        new_token = create_access_token({"sub": str(current_user.phone)})
        message = "Profile berhasil diupdate. Gunakan access_token baru untuk request selanjutnya."
        logger.info(f"[KERABAT_COMPLETE_PROFILE] Phone updated from {old_phone} to {current_user.phone}, new token generated")

    return KerabatCompleteProfileResponse(
        kerabat=KerabatResponse.model_validate(kerabat),
        access_token=new_token,
        token_type="bearer",
        message=message,
    )


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


# ============================================================================
# KERABAT DASHBOARD & FEATURE ENDPOINTS
# ============================================================================


def _get_kerabat_and_ibu_hamil(current_user: User, db: Session):
    """Helper untuk mendapatkan data kerabat dan ibu hamil."""
    if current_user.role != "kerabat":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Hanya kerabat yang dapat mengakses endpoint ini",
        )

    kerabat = db.scalars(
        select(KerabatIbuHamil).where(KerabatIbuHamil.kerabat_user_id == current_user.id)
    ).first()

    if not kerabat:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Kerabat tidak ditemukan. Pastikan Anda sudah login dengan invitation code.",
        )

    ibu_hamil = db.get(IbuHamil, kerabat.ibu_hamil_id)
    if not ibu_hamil:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Data ibu hamil tidak ditemukan",
        )

    return kerabat, ibu_hamil


@router.get(
    "/me",
    response_model=KerabatProfileResponse,
    summary="Get profile kerabat yang sedang login",
)
async def get_my_profile(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> KerabatProfileResponse:
    """Get profile kerabat yang sedang login."""
    kerabat, ibu_hamil = _get_kerabat_and_ibu_hamil(current_user, db)

    return KerabatProfileResponse(
        id=kerabat.id,
        user_id=current_user.id,
        full_name=current_user.full_name,
        phone=current_user.phone if not current_user.phone.startswith("+629999") else None,
        relation_type=kerabat.relation_type,
        ibu_hamil_id=ibu_hamil.id,
        ibu_hamil_name=ibu_hamil.nama_lengkap,
        can_view_records=kerabat.can_view_records,
        can_receive_notifications=kerabat.can_receive_notifications,
        created_at=kerabat.created_at,
    )


@router.get(
    "/dashboard",
    response_model=KerabatDashboardResponse,
    summary="Dashboard kerabat dengan ringkasan info ibu hamil",
)
async def get_dashboard(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> KerabatDashboardResponse:
    """Dashboard kerabat: info ibu hamil, health record terbaru, kontak darurat."""
    kerabat, ibu_hamil = _get_kerabat_and_ibu_hamil(current_user, db)

    if not kerabat.can_view_records:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Anda tidak memiliki izin untuk melihat data ibu hamil",
        )

    # Get latest health record
    latest_record = crud_health_record.get_latest(db, ibu_hamil_id=ibu_hamil.id)
    latest_health_summary = None
    if latest_record:
        latest_health_summary = LatestHealthRecordSummary(
            id=latest_record.id,
            checkup_date=latest_record.checkup_date,
            blood_pressure_systolic=latest_record.blood_pressure_systolic,
            blood_pressure_diastolic=latest_record.blood_pressure_diastolic,
            heart_rate=latest_record.heart_rate,
            body_temperature=latest_record.body_temperature,
            weight=latest_record.weight,
            complaints=latest_record.complaints,
            checked_by=latest_record.checked_by,
            notes=latest_record.notes,
        )

    # Get emergency contact
    emergency_contact = EmergencyContact()
    if ibu_hamil.perawat_id:
        perawat = db.get(Perawat, ibu_hamil.perawat_id)
        if perawat and perawat.user_id:
            perawat_user = db.get(User, perawat.user_id)
            if perawat_user:
                emergency_contact.perawat_name = perawat_user.full_name
                emergency_contact.perawat_phone = perawat_user.phone

    if ibu_hamil.puskesmas_id:
        puskesmas = db.get(Puskesmas, ibu_hamil.puskesmas_id)
        if puskesmas:
            emergency_contact.puskesmas_name = puskesmas.name
            emergency_contact.puskesmas_phone = puskesmas.phone
            emergency_contact.puskesmas_address = puskesmas.address

    # Get unread notifications count
    notifications = crud_notification.get_by_user(db, user_id=current_user.id, is_read=False)

    # Risk alert
    risk_alert = None
    if ibu_hamil.risk_level == "tinggi":
        risk_alert = "PERHATIAN: Ibu hamil memiliki status risiko TINGGI. Segera hubungi perawat jika ada keluhan."
    elif ibu_hamil.risk_level == "sedang":
        risk_alert = "INFO: Ibu hamil memiliki status risiko SEDANG. Pastikan pemeriksaan rutin dilakukan."

    ibu_hamil_summary = IbuHamilSummary(
        id=ibu_hamil.id,
        nama_lengkap=ibu_hamil.nama_lengkap,
        usia_kehamilan_minggu=ibu_hamil.usia_kehamilan,  # usia_kehamilan from model
        usia_kehamilan_hari=None,  # Not stored separately in model
        tanggal_hpht=ibu_hamil.last_menstrual_period,  # HPHT = last_menstrual_period
        tanggal_taksiran_persalinan=ibu_hamil.estimated_due_date,  # HPL = estimated_due_date
        risk_level=ibu_hamil.risk_level,
        risk_level_set_at=ibu_hamil.risk_level_set_at,
        golongan_darah=ibu_hamil.blood_type,  # golongan_darah = blood_type
    )

    return KerabatDashboardResponse(
        kerabat_id=kerabat.id,
        kerabat_name=current_user.full_name,
        relation_type=kerabat.relation_type,
        ibu_hamil=ibu_hamil_summary,
        latest_health_record=latest_health_summary,
        emergency_contact=emergency_contact,
        unread_notifications_count=len(notifications),
        risk_alert=risk_alert,
    )


@router.get(
    "/health-records",
    response_model=KerabatHealthRecordListResponse,
    summary="Daftar riwayat health record ibu hamil",
)
async def get_health_records(
    page: int = Query(1, ge=1),
    per_page: int = Query(10, ge=1, le=50),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> KerabatHealthRecordListResponse:
    """Get health records history untuk ibu hamil."""
    kerabat, ibu_hamil = _get_kerabat_and_ibu_hamil(current_user, db)

    if not kerabat.can_view_records:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Anda tidak memiliki izin untuk melihat health record",
        )

    all_records = crud_health_record.get_by_ibu_hamil(db, ibu_hamil_id=ibu_hamil.id)
    total = len(all_records)

    start_idx = (page - 1) * per_page
    paginated_records = all_records[start_idx:start_idx + per_page]
    records_response = [HealthRecordResponse.model_validate(r) for r in paginated_records]

    return KerabatHealthRecordListResponse(
        ibu_hamil_id=ibu_hamil.id,
        ibu_hamil_name=ibu_hamil.nama_lengkap,
        records=records_response,
        total=total,
        page=page,
        per_page=per_page,
    )


@router.get(
    "/health-records/{record_id}",
    response_model=HealthRecordResponse,
    summary="Detail satu health record",
)
async def get_health_record_detail(
    record_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> HealthRecordResponse:
    """Get detail satu health record."""
    kerabat, ibu_hamil = _get_kerabat_and_ibu_hamil(current_user, db)

    if not kerabat.can_view_records:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Anda tidak memiliki izin untuk melihat health record",
        )

    record = crud_health_record.get(db, record_id)
    if not record or record.ibu_hamil_id != ibu_hamil.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Health record tidak ditemukan",
        )

    return HealthRecordResponse.model_validate(record)


@router.get(
    "/notifications",
    response_model=KerabatNotificationListResponse,
    summary="Daftar notifikasi kerabat",
)
async def get_notifications(
    unread_only: bool = Query(False),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> KerabatNotificationListResponse:
    """Get daftar notifikasi kerabat."""
    if current_user.role != "kerabat":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Hanya kerabat yang dapat mengakses endpoint ini",
        )

    # Convert unread_only to is_read parameter
    is_read_filter = False if unread_only else None
    notifications = crud_notification.get_by_user(db, user_id=current_user.id, is_read=is_read_filter)
    unread = crud_notification.get_by_user(db, user_id=current_user.id, is_read=False)

    return KerabatNotificationListResponse(
        notifications=[NotificationResponse.model_validate(n) for n in notifications],
        total=len(notifications),
        unread_count=len(unread),
    )


@router.patch(
    "/notifications/mark-read",
    response_model=MarkNotificationReadResponse,
    summary="Tandai notifikasi sudah dibaca",
)
async def mark_notifications_read(
    payload: MarkNotificationReadRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> MarkNotificationReadResponse:
    """Mark notifications as read."""
    if current_user.role != "kerabat":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Hanya kerabat yang dapat mengakses endpoint ini",
        )

    if not payload.notification_ids:
        count = crud_notification.mark_all_read(db, user_id=current_user.id)
    else:
        count = 0
        for notif_id in payload.notification_ids:
            notif = crud_notification.get(db, notif_id)
            if notif and notif.user_id == current_user.id:
                crud_notification.mark_as_read(db, notification_id=notif_id)
                count += 1

    return MarkNotificationReadResponse(
        marked_count=count,
        message=f"{count} notifikasi berhasil ditandai sudah dibaca",
    )


@router.get(
    "/risk-status",
    summary="Status risiko kehamilan ibu hamil",
)
async def get_risk_status(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Get risk status ibu hamil dengan rekomendasi."""
    kerabat, ibu_hamil = _get_kerabat_and_ibu_hamil(current_user, db)

    risk_info = {
        "ibu_hamil_id": ibu_hamil.id,
        "ibu_hamil_name": ibu_hamil.nama_lengkap,
        "risk_level": ibu_hamil.risk_level,
        "risk_level_set_at": ibu_hamil.risk_level_set_at,
        "message": "",
        "recommendations": [],
    }

    if ibu_hamil.risk_level == "tinggi":
        risk_info["message"] = "Status risiko kehamilan TINGGI. Diperlukan perhatian khusus."
        risk_info["recommendations"] = [
            "Segera hubungi perawat jika ada keluhan",
            "Lakukan pemeriksaan rutin sesuai jadwal",
            "Hindari aktivitas fisik yang berat",
            "Persiapkan transportasi ke fasilitas kesehatan",
        ]
    elif ibu_hamil.risk_level == "sedang":
        risk_info["message"] = "Status risiko kehamilan SEDANG. Perlu pemantauan rutin."
        risk_info["recommendations"] = [
            "Lakukan pemeriksaan rutin sesuai jadwal",
            "Jaga pola makan dan istirahat",
            "Pantau tekanan darah secara berkala",
        ]
    elif ibu_hamil.risk_level == "rendah":
        risk_info["message"] = "Status risiko kehamilan RENDAH. Tetap jaga kesehatan."
        risk_info["recommendations"] = [
            "Lakukan pemeriksaan rutin",
            "Jaga pola makan sehat",
            "Olahraga ringan secara teratur",
        ]
    else:
        risk_info["message"] = "Status risiko belum ditentukan oleh perawat."
        risk_info["recommendations"] = ["Jadwalkan pemeriksaan dengan perawat"]

    return risk_info


@router.post(
    "/logout",
    summary="Logout kerabat",
)
async def logout(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Logout kerabat (hapus token di client)."""
    if current_user.role != "kerabat":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Hanya kerabat yang dapat mengakses endpoint ini",
        )

    kerabat = db.scalars(
        select(KerabatIbuHamil).where(KerabatIbuHamil.kerabat_user_id == current_user.id)
    ).first()

    return {
        "message": "Logout berhasil",
        "user_id": current_user.id,
        "kerabat_id": kerabat.id if kerabat else None,
        "instruction": "Hapus access token di aplikasi untuk menyelesaikan logout",
    }


__all__ = ["router"]
