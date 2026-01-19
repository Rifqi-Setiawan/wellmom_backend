"""Perawat activation and profile endpoints (FR-TK-001).

Flow:
- Puskesmas generates account dengan email dan NIP
- Password otomatis = NIP
- Nurse receives verification link (token) via email
- Verify email -> login dengan email + password
- Perawat dapat reset password sendiri

Notes:
- We store verification token in users.verification_token.
- Token expires after 72 hours (configurable in crud/user.py).
- Password awal menggunakan NIP, perawat wajib ganti setelah login pertama.
"""

from datetime import timedelta
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status, File, UploadFile
from pydantic import BaseModel, ConfigDict, EmailStr
from sqlalchemy.orm import Session

from app.api.deps import get_current_active_user, get_db, require_role
from app.config import settings
from app.core.security import create_access_token, verify_password
from app.crud import crud_user, crud_perawat, crud_puskesmas, crud_notification
from app.crud.user import TOKEN_EXPIRATION_HOURS
from app.models.user import User
from app.models.perawat import Perawat as PerawatModel
from app.schemas.perawat import (
    PerawatRegisterWithUser,
    PerawatResponse,
    PerawatGenerate,
    PerawatLoginRequest,
    PerawatLoginResponse,
    PerawatLoginUserInfo,
    PerawatLoginPerawatInfo,
    PerawatResetPasswordRequest,
)
from app.schemas.user import UserCreate
from app.schemas.notification import NotificationCreate
from app.services.email import EmailNotConfigured, send_email
from app.services.email_templates import (
    build_perawat_activation_email,
    build_perawat_activation_success_email,
    build_puskesmas_perawat_activated_notification,
    build_resend_activation_email,
)
from app.utils.file_handler import save_profile_photo

router = APIRouter(
    prefix="/perawat",
    tags=["Perawat (Nurses)"]
)


class VerificationRequest(BaseModel):
    user_id: int

    model_config = ConfigDict(json_schema_extra={
        "example": {"user_id": 123}
    })


class VerificationConfirm(BaseModel):
    token: str

    model_config = ConfigDict(json_schema_extra={
        "example": {"token": "VERIF_TOKEN_ABC..."}
    })


class SetPasswordPayload(BaseModel):
    token: str
    new_password: str

    model_config = ConfigDict(json_schema_extra={
        "example": {"token": "VERIF_TOKEN_ABC...", "new_password": "StrongPass!234"}
    })


class CompleteProfilePayload(BaseModel):
    token: str
    profile_photo_url: str

    model_config = ConfigDict(json_schema_extra={
        "example": {"token": "VERIF_TOKEN_ABC...", "profile_photo_url": "https://cdn.example.com/photos/perawat.jpg"}
    })


class AcceptTermsPayload(BaseModel):
    token: str

    model_config = ConfigDict(json_schema_extra={
        "example": {"token": "VERIF_TOKEN_ABC..."}
    })


def _get_perawat_by_user(db: Session, user_id: int) -> PerawatModel | None:
    return db.query(PerawatModel).filter(PerawatModel.user_id == user_id).first()


def _build_activation_link(token: str) -> str:
    """Build activation link from token."""
    return f"{settings.FRONTEND_BASE_URL.rstrip('/')}/perawat/activate?token={token}"


def _build_login_url() -> str:
    """Build login URL for perawat."""
    return f"{settings.FRONTEND_BASE_URL.rstrip('/')}/perawat/login"


def _build_dashboard_url() -> str:
    """Build dashboard URL for puskesmas admin."""
    return f"{settings.FRONTEND_BASE_URL.rstrip('/')}/puskesmas/dashboard/perawat"


@router.post(
    "/generate",
    status_code=status.HTTP_201_CREATED,
    summary="Puskesmas generate akun perawat (email + NIP)",
    description="""
Generate akun perawat baru oleh Puskesmas.

## Request Body
- **email**: Email perawat (untuk login dan menerima aktivasi)
- **nip**: NIP perawat (juga digunakan sebagai password awal)

## Flow
1. Puskesmas memasukkan email dan NIP perawat
2. Sistem membuat akun user dan perawat
3. Password otomatis menggunakan NIP
4. Email aktivasi dikirim ke perawat
5. Perawat dapat login dengan email + password (NIP)
6. Perawat disarankan untuk mengubah password setelah login pertama

## Response
Mengembalikan informasi akun yang dibuat dan link aktivasi.
    """,
)
def generate_perawat_account(
    payload: PerawatGenerate,
    current_user: User = Depends(require_role("puskesmas")),
    db: Session = Depends(get_db),
) -> dict:
    """Puskesmas creates a nurse account with email and NIP. Password = NIP."""
    puskesmas = crud_puskesmas.get_by_admin_user_id(db, admin_user_id=current_user.id)
    if not puskesmas:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Puskesmas profile not found for this user")

    # Uniqueness checks
    if crud_user.get_by_email(db, email=payload.email):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email sudah terdaftar")
    if crud_perawat.get_by_email(db, email=payload.email):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email sudah terdaftar sebagai perawat")
    if crud_perawat.get_by_nip(db, nip=payload.nip):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="NIP sudah terdaftar")

    # Extract name from email (before @) as placeholder
    email_name = payload.email.split("@")[0].replace(".", " ").replace("_", " ").title()
    full_name = email_name if email_name else f"Perawat {payload.nip}"
    
    # Generate placeholder phone (will be updated by perawat later)
    placeholder_phone = f"+62000{payload.nip[-8:]}" if len(payload.nip) >= 8 else f"+62000{payload.nip}"

    # Create user with password = NIP
    user = crud_user.create_user(
        db,
        user_in=UserCreate(
            phone=placeholder_phone,
            password=payload.nip,  # Password = NIP
            full_name=full_name,
            role="perawat",
            email=payload.email,
        ),
    )
    user.is_active = False  # Inactive until activation
    user.is_verified = False
    db.add(user)
    db.commit()
    db.refresh(user)

    # Create perawat profile linked to user and puskesmas
    perawat = PerawatModel(
        user_id=user.id,
        puskesmas_id=puskesmas.id,
        nama_lengkap=full_name,
        email=payload.email,
        nomor_hp=placeholder_phone,
        nip=payload.nip,
        is_active=False,  # Inactive until activation
    )
    db.add(perawat)
    db.commit()
    db.refresh(perawat)

    # Create verification token with expiration
    token = crud_user.create_verification_token(db, user_id=user.id)
    if not token:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to create verification token")

    activation_link = _build_activation_link(token)

    # Build professional email
    subject, html_body, text_body = build_perawat_activation_email(
        nurse_name=full_name,
        puskesmas_name=puskesmas.name,
        activation_link=activation_link,
        email=payload.email,
        nip=payload.nip,
        expires_in_hours=TOKEN_EXPIRATION_HOURS,
    )

    email_sent = False
    email_error = None
    try:
        send_email(to_email=payload.email, subject=subject, html_content=html_body, text_content=text_body)
        email_sent = True
    except EmailNotConfigured as e:
        email_error = str(e)
    except Exception as e:
        email_error = str(e)

    return {
        "user_id": user.id,
        "perawat_id": perawat.id,
        "email": payload.email,
        "nip": payload.nip,
        "full_name": full_name,
        "puskesmas_id": puskesmas.id,
        "puskesmas_name": puskesmas.name,
        "activation_link": activation_link,
        "email_sent": email_sent,
        "email_error": email_error if not email_sent else None,
        "token_expires_in_hours": TOKEN_EXPIRATION_HOURS,
        "message": "Akun perawat berhasil dibuat. Password awal adalah NIP. Perawat dapat login setelah aktivasi.",
    }


@router.post(
    "/login",
    response_model=PerawatLoginResponse,
    status_code=status.HTTP_200_OK,
    summary="Login sebagai Perawat",
    description="""
Login endpoint untuk perawat menggunakan email dan password.

## Persyaratan Login
1. **User harus memiliki role `perawat`**
2. **Akun harus sudah diverifikasi** (`is_verified = true`)
3. **Akun harus aktif** (`is_active = true`)

## Password Awal
Password awal adalah NIP yang digenerate oleh Puskesmas.
Perawat disarankan untuk mengubah password setelah login pertama.

## Response Sukses
Mengembalikan JWT token beserta informasi user dan perawat.
Token berlaku selama 30 hari.
    """,
)
def login_perawat(
    login_data: PerawatLoginRequest,
    db: Session = Depends(get_db),
) -> PerawatLoginResponse:
    """Login endpoint untuk perawat dengan email dan password."""
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
            detail="Akun belum diaktivasi. Silakan cek email untuk link aktivasi.",
        )

    # Step 3: Verify user has perawat role
    if user.role != "perawat":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Akun ini bukan akun perawat",
        )

    # Step 4: Get perawat record linked to this user
    perawat = _get_perawat_by_user(db, user_id=user.id)

    if not perawat:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Data perawat tidak ditemukan untuk akun ini",
        )

    # Step 5: Check perawat is_active status
    if not perawat.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Akun perawat tidak aktif. Hubungi puskesmas untuk informasi lebih lanjut.",
        )

    # Step 6: Get puskesmas name
    puskesmas_name = perawat.puskesmas.name if perawat.puskesmas else None

    # Step 7: Generate access token
    access_token_expires = timedelta(days=30)
    access_token = create_access_token(
        data={"sub": user.phone, "user_id": user.id, "role": user.role},
        expires_delta=access_token_expires,
    )

    # Step 8: Build response
    return PerawatLoginResponse(
        access_token=access_token,
        token_type="bearer",
        role=user.role,
        user=PerawatLoginUserInfo(
            id=user.id,
            email=user.email,
            full_name=user.full_name,
        ),
        perawat=PerawatLoginPerawatInfo(
            id=perawat.id,
            nip=perawat.nip,
            puskesmas_id=perawat.puskesmas_id,
            puskesmas_name=puskesmas_name,
            is_active=perawat.is_active,
        ),
    )


@router.post(
    "/reset-password",
    status_code=status.HTTP_200_OK,
    summary="Reset password perawat",
    description="""
Reset password untuk perawat yang sudah login.

## Persyaratan
- Harus sudah login sebagai perawat
- Harus memasukkan password lama yang benar
- Password baru minimal 6 karakter

## Flow
1. Perawat login dengan password lama (NIP)
2. Akses endpoint ini dengan password lama dan password baru
3. Password berhasil diubah
    """,
)
def reset_password_perawat(
    payload: PerawatResetPasswordRequest,
    current_user: User = Depends(require_role("perawat")),
    db: Session = Depends(get_db),
) -> dict:
    """Reset password untuk perawat yang sudah login."""
    # Verify current password
    if not verify_password(payload.current_password, current_user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password saat ini salah",
        )
    
    # Update password
    updated = crud_user.update_password(db, user_id=current_user.id, new_password=payload.new_password)
    if not updated:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Gagal mengubah password",
        )
    
    return {
        "message": "Password berhasil diubah",
        "user_id": current_user.id,
    }


class ResendActivationRequest(BaseModel):
    """Schema untuk resend activation email."""
    email: EmailStr

    model_config = ConfigDict(json_schema_extra={
        "example": {"email": "perawat@puskesmas.go.id"}
    })


@router.post(
    "/activation/resend",
    status_code=status.HTTP_200_OK,
    summary="Resend activation email",
    description="""
Kirim ulang email aktivasi untuk perawat yang belum mengaktifkan akunnya.

## Kapan digunakan:
- Email aktivasi sebelumnya tidak diterima
- Token aktivasi sudah kedaluwarsa (expired)
- Perawat lupa mengaktifkan akunnya

## Persyaratan:
- Email harus terdaftar sebagai perawat
- Akun belum diaktivasi (is_active = false)

## Catatan:
- Token lama akan dinonaktifkan
- Token baru berlaku selama 72 jam
    """,
)
def resend_activation_email(
    payload: ResendActivationRequest,
    db: Session = Depends(get_db),
) -> dict:
    """Resend activation email to perawat who hasn't activated their account."""
    # Find user by email
    user = crud_user.get_by_email(db, email=payload.email)
    if not user or user.role != "perawat":
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Email tidak ditemukan atau bukan akun perawat"
        )

    # Check if already activated
    if user.is_active and user.is_verified:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Akun sudah diaktivasi. Silakan login."
        )

    # Get perawat data
    perawat = _get_perawat_by_user(db, user_id=user.id)
    if not perawat:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Data perawat tidak ditemukan"
        )

    puskesmas_name = perawat.puskesmas.name if perawat.puskesmas else "Puskesmas"

    # Generate new token (this invalidates the old one)
    token = crud_user.create_verification_token(db, user_id=user.id)
    if not token:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Gagal membuat token aktivasi"
        )

    activation_link = _build_activation_link(token)

    # Build resend email
    subject, html_body, text_body = build_resend_activation_email(
        nurse_name=user.full_name,
        puskesmas_name=puskesmas_name,
        activation_link=activation_link,
        email=payload.email,
        expires_in_hours=TOKEN_EXPIRATION_HOURS,
    )

    try:
        send_email(to_email=payload.email, subject=subject, html_content=html_body, text_content=text_body)
    except EmailNotConfigured as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Email tidak dapat dikirim: {exc}"
        ) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Gagal mengirim email: {exc}"
        ) from exc

    return {
        "message": "Email aktivasi berhasil dikirim ulang",
        "email": payload.email,
        "token_expires_in_hours": TOKEN_EXPIRATION_HOURS,
    }


class CheckTokenRequest(BaseModel):
    """Schema untuk check token validity."""
    token: str

    model_config = ConfigDict(json_schema_extra={
        "example": {"token": "VERIF_TOKEN_ABC..."}
    })


@router.post(
    "/activation/check-token",
    status_code=status.HTTP_200_OK,
    summary="Check activation token validity",
    description="""
Cek apakah token aktivasi masih valid sebelum menampilkan form aktivasi.

## Kegunaan:
- Frontend dapat memverifikasi token sebelum menampilkan form
- Menampilkan pesan yang tepat jika token expired atau invalid

## Response:
- **valid**: true jika token masih valid
- **expired**: true jika token sudah kedaluwarsa
- **user_info**: informasi dasar user jika token valid
- **expires_at**: waktu token kedaluwarsa (jika valid)
    """,
)
def check_token_validity(
    payload: CheckTokenRequest,
    db: Session = Depends(get_db),
) -> dict:
    """Check if activation token is still valid."""
    # Check if token exists
    user = crud_user.get_by_verification_token(db, token=payload.token)

    if not user:
        # Token doesn't exist or already expired
        return {
            "valid": False,
            "expired": True,
            "message": "Token tidak valid atau sudah kedaluwarsa",
            "user_info": None,
            "expires_at": None,
        }

    # Check if already activated
    if user.is_active and user.is_verified:
        return {
            "valid": False,
            "expired": False,
            "message": "Akun sudah diaktivasi. Silakan login.",
            "already_activated": True,
            "user_info": {
                "user_id": user.id,
                "email": user.email,
                "full_name": user.full_name,
            },
            "expires_at": None,
        }

    # Get perawat data
    perawat = _get_perawat_by_user(db, user_id=user.id)
    puskesmas_name = perawat.puskesmas.name if perawat and perawat.puskesmas else None

    return {
        "valid": True,
        "expired": False,
        "message": "Token valid",
        "user_info": {
            "user_id": user.id,
            "email": user.email,
            "full_name": user.full_name,
            "is_verified": user.is_verified,
            "puskesmas_name": puskesmas_name,
            "nip": perawat.nip if perawat else None,
        },
        "expires_at": user.verification_token_expires_at.isoformat() if user.verification_token_expires_at else None,
    }


@router.post(
    "/activation/request",
    status_code=status.HTTP_200_OK,
    summary="Request email verification (internal)",
    description="Internal endpoint untuk puskesmas admin mengirim ulang email aktivasi.",
)
def request_verification(
    payload: VerificationRequest,
    current_user: User = Depends(require_role("puskesmas")),
    db: Session = Depends(get_db),
) -> dict:
    """Puskesmas admin can request to resend verification email for their nurses."""
    user = crud_user.get(db, payload.user_id)
    if not user or user.role != "perawat":
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Perawat user not found")
    if not user.email:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Perawat email is required")

    # Verify the perawat belongs to this puskesmas
    perawat = _get_perawat_by_user(db, user_id=user.id)
    if not perawat:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Perawat profile not found")

    puskesmas = crud_puskesmas.get_by_admin_user_id(db, admin_user_id=current_user.id)
    if not puskesmas or perawat.puskesmas_id != puskesmas.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Perawat bukan dari puskesmas Anda")

    # Check if already activated
    if user.is_active and user.is_verified:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Perawat sudah diaktivasi")

    # Generate new token
    token = crud_user.create_verification_token(db, user_id=user.id)
    if not token:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to create token")

    activation_link = _build_activation_link(token)
    puskesmas_name = puskesmas.name

    subject, html_body, text_body = build_resend_activation_email(
        nurse_name=user.full_name,
        puskesmas_name=puskesmas_name,
        activation_link=activation_link,
        email=user.email,
        expires_in_hours=TOKEN_EXPIRATION_HOURS,
    )

    try:
        send_email(to_email=user.email, subject=subject, html_content=html_body, text_content=text_body)
    except EmailNotConfigured as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc)) from exc

    return {
        "message": "Email aktivasi berhasil dikirim",
        "user_id": user.id,
        "email": user.email,
        "activation_link": activation_link,
        "token_expires_in_hours": TOKEN_EXPIRATION_HOURS,
    }


@router.post(
    "/activation/verify",
    status_code=status.HTTP_200_OK,
    summary="Verify email via token (Step 1)",
    description="""
Verifikasi email perawat menggunakan token dari email aktivasi.

**Ini adalah langkah pertama dari proses aktivasi:**
1. **verify** - Verifikasi email (endpoint ini)
2. set-password - Set password baru (opsional)
3. complete-profile - Lengkapi profil
4. accept-terms - Terima syarat & ketentuan, aktivasi akun

Token tetap valid sampai langkah terakhir selesai atau expired.
    """,
)
def verify_email(payload: VerificationConfirm, db: Session = Depends(get_db)) -> dict:
    """Verify perawat email. Token is NOT cleared to allow multi-step flow."""
    # Check if token is expired first
    if crud_user.is_token_expired(db, token=payload.token):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Token sudah kedaluwarsa. Silakan minta email aktivasi baru."
        )

    # Verify without clearing token (for multi-step flow)
    user = crud_user.verify_by_token(db, token=payload.token, clear_token=False)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Token tidak valid atau sudah kedaluwarsa"
        )

    return {
        "message": "Email berhasil diverifikasi",
        "user_id": user.id,
        "is_verified": user.is_verified,
        "next_step": "set-password atau complete-profile",
    }


@router.post(
    "/activation/set-password",
    status_code=status.HTTP_200_OK,
    summary="Set password (Step 2 - Optional)",
    description="""
Set password baru untuk perawat. Langkah ini opsional karena password awal sudah diset ke NIP.

**Persyaratan:**
- Token harus valid dan belum expired
- Password baru minimal 6 karakter

**Catatan:**
- Password awal adalah NIP perawat
- Perawat disarankan untuk mengubah password untuk keamanan
    """,
)
def set_password(payload: SetPasswordPayload, db: Session = Depends(get_db)) -> dict:
    """Set new password for perawat during activation flow."""
    # Check if token is expired
    if crud_user.is_token_expired(db, token=payload.token):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Token sudah kedaluwarsa. Silakan minta email aktivasi baru."
        )

    # Get user by token (without clearing)
    user = crud_user.get_by_verification_token(db, token=payload.token)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Token tidak valid"
        )

    # Validate password length
    if len(payload.new_password) < 6:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password minimal 6 karakter"
        )

    updated = crud_user.update_password(db, user_id=user.id, new_password=payload.new_password)
    if not updated:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Gagal mengubah password"
        )

    return {
        "message": "Password berhasil diubah",
        "user_id": updated.id,
        "next_step": "complete-profile",
    }


@router.post(
    "/activation/complete-profile",
    response_model=PerawatResponse,
    status_code=status.HTTP_200_OK,
    summary="Complete profile (Step 3)",
    description="""
Lengkapi profil perawat dengan foto profil.

**Persyaratan:**
- Token harus valid dan belum expired
- URL foto profil harus valid

**Catatan:**
- Foto profil akan disimpan di User dan Perawat
- Setelah ini, lanjut ke accept-terms untuk aktivasi final
    """,
)
def complete_profile(payload: CompleteProfilePayload, db: Session = Depends(get_db)) -> PerawatModel:
    """Complete perawat profile with photo during activation flow."""
    # Check if token is expired
    if crud_user.is_token_expired(db, token=payload.token):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Token sudah kedaluwarsa. Silakan minta email aktivasi baru."
        )

    # Get user by token (without clearing)
    user = crud_user.get_by_verification_token(db, token=payload.token)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Token tidak valid"
        )

    # Update user profile photo
    user.profile_photo_url = payload.profile_photo_url
    db.add(user)
    db.commit()
    db.refresh(user)

    # Also update perawat profile photo
    perawat = _get_perawat_by_user(db, user_id=user.id)
    if not perawat:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Data perawat tidak ditemukan"
        )

    perawat.profile_photo_url = payload.profile_photo_url
    db.add(perawat)
    db.commit()
    db.refresh(perawat)

    return perawat


@router.post(
    "/activation/accept-terms",
    status_code=status.HTTP_200_OK,
    summary="Accept T&C and activate (Step 4 - Final)",
    description="""
Terima syarat & ketentuan dan aktivasi akun perawat.

**Ini adalah langkah terakhir dari proses aktivasi.**

Setelah endpoint ini dipanggil:
1. Akun perawat akan diaktifkan
2. Perawat dapat login dengan email dan password
3. Token aktivasi akan dihapus (tidak bisa digunakan lagi)
4. Notifikasi dikirim ke admin puskesmas
5. Email konfirmasi dikirim ke perawat

**Persyaratan:**
- Token harus valid dan belum expired
- Email harus sudah diverifikasi (dari step 1)
    """,
)
def accept_terms(payload: AcceptTermsPayload, db: Session = Depends(get_db)) -> dict:
    """Final step: Accept terms, activate account, and send notifications."""
    # Check if token is expired
    if crud_user.is_token_expired(db, token=payload.token):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Token sudah kedaluwarsa. Silakan minta email aktivasi baru."
        )

    # Get user by token
    user = crud_user.get_by_verification_token(db, token=payload.token)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Token tidak valid"
        )

    # Get perawat data
    perawat = _get_perawat_by_user(db, user_id=user.id)
    if not perawat:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Data perawat tidak ditemukan"
        )

    # Get puskesmas data for notifications
    puskesmas = perawat.puskesmas
    puskesmas_name = puskesmas.name if puskesmas else "Puskesmas"
    puskesmas_admin_user_id = puskesmas.admin_user_id if puskesmas else None

    # Activate user account
    user.is_verified = True
    user.is_active = True
    db.add(user)
    db.commit()
    db.refresh(user)

    # Clear verification token (final step)
    crud_user.clear_verification_token(db, user_id=user.id)

    # Activate perawat
    perawat.is_active = True
    db.add(perawat)
    db.commit()
    db.refresh(perawat)

    # Send notifications
    email_to_perawat_sent = False
    email_to_puskesmas_sent = False

    # 1. Send confirmation email to perawat
    if user.email:
        try:
            subject, html_body, text_body = build_perawat_activation_success_email(
                nurse_name=user.full_name,
                puskesmas_name=puskesmas_name,
                login_url=_build_login_url(),
            )
            send_email(to_email=user.email, subject=subject, html_content=html_body, text_content=text_body)
            email_to_perawat_sent = True
        except Exception:
            pass  # Don't fail activation if email fails

    # 2. Create in-app notification for puskesmas admin
    if puskesmas_admin_user_id:
        try:
            notification_in = NotificationCreate(
                user_id=puskesmas_admin_user_id,
                title="Perawat Baru Aktif",
                message=f"Perawat {user.full_name} ({perawat.nip}) telah mengaktifkan akunnya dan siap bertugas.",
                notification_type="system",
                priority="normal",
                sent_via="in_app",
            )
            crud_notification.create(db, obj_in=notification_in)
        except Exception:
            pass  # Don't fail activation if notification fails

    # 3. Send email notification to puskesmas admin
    if puskesmas and puskesmas.admin_user_id:
        try:
            # Get puskesmas admin user for email
            admin_user = crud_user.get(db, puskesmas.admin_user_id)
            if admin_user and admin_user.email:
                subject, html_body, text_body = build_puskesmas_perawat_activated_notification(
                    admin_name=admin_user.full_name,
                    nurse_name=user.full_name,
                    nurse_email=user.email or perawat.email,
                    nurse_nip=perawat.nip,
                    puskesmas_name=puskesmas_name,
                    dashboard_url=_build_dashboard_url(),
                )
                send_email(to_email=admin_user.email, subject=subject, html_content=html_body, text_content=text_body)
                email_to_puskesmas_sent = True
        except Exception:
            pass  # Don't fail activation if email fails

    return {
        "message": "Akun berhasil diaktivasi! Anda dapat login sekarang.",
        "user_id": user.id,
        "perawat_id": perawat.id,
        "email": user.email,
        "puskesmas_name": puskesmas_name,
        "notifications": {
            "email_to_perawat_sent": email_to_perawat_sent,
            "email_to_puskesmas_sent": email_to_puskesmas_sent,
            "in_app_notification_created": puskesmas_admin_user_id is not None,
        },
        "login_url": _build_login_url(),
    }


@router.get(
    "",
    response_model=List[PerawatResponse],
    status_code=status.HTTP_200_OK,
    summary="List all perawat",
)
def list_perawat(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
) -> List[PerawatModel]:
    """Public list of all active perawat."""
    return crud_perawat.get_multi(db, skip=skip, limit=limit)


@router.get(
    "/puskesmas/my-nurses",
    status_code=status.HTTP_200_OK,
    summary="List perawat milik puskesmas (untuk admin puskesmas)",
    description="""
Endpoint untuk puskesmas admin melihat daftar semua perawat yang terdaftar di puskesmas mereka.

## Response meliputi:
- Informasi dasar perawat (nama, email, NIP)
- Status aktivasi (sudah aktif atau belum)
- Tanggal pendaftaran

## Kegunaan:
- Memantau perawat mana yang sudah mengaktifkan akun
- Mengetahui perawat mana yang perlu dikirim ulang email aktivasi
    """,
)
def list_my_nurses(
    current_user: User = Depends(require_role("puskesmas")),
    db: Session = Depends(get_db),
) -> dict:
    """Get list of nurses registered under current puskesmas admin."""
    # Get puskesmas for current admin
    puskesmas = crud_puskesmas.get_by_admin_user_id(db, admin_user_id=current_user.id)
    if not puskesmas:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Puskesmas tidak ditemukan untuk user ini"
        )

    # Get all perawat for this puskesmas
    perawat_list = db.query(PerawatModel).filter(
        PerawatModel.puskesmas_id == puskesmas.id
    ).order_by(PerawatModel.created_at.desc()).all()

    result = []
    for perawat in perawat_list:
        # Get linked user for activation status
        user = db.query(User).filter(User.id == perawat.user_id).first() if perawat.user_id else None

        result.append({
            "id": perawat.id,
            "user_id": perawat.user_id,
            "nama_lengkap": perawat.nama_lengkap,
            "email": perawat.email,
            "nomor_hp": perawat.nomor_hp,
            "nip": perawat.nip,
            "profile_photo_url": perawat.profile_photo_url,
            "is_active": perawat.is_active,
            "created_at": perawat.created_at.isoformat() if perawat.created_at else None,
            "updated_at": perawat.updated_at.isoformat() if perawat.updated_at else None,
            # User activation status
            "activation_status": {
                "is_verified": user.is_verified if user else False,
                "is_user_active": user.is_active if user else False,
                "has_pending_token": user.verification_token is not None if user else False,
                "token_expires_at": user.verification_token_expires_at.isoformat() if user and user.verification_token_expires_at else None,
            } if user else None,
        })

    return {
        "puskesmas_id": puskesmas.id,
        "puskesmas_name": puskesmas.name,
        "total_perawat": len(result),
        "perawat_aktif": sum(1 for p in result if p["is_active"] and p.get("activation_status", {}).get("is_user_active")),
        "perawat_pending": sum(1 for p in result if not p["is_active"] or (p.get("activation_status") and not p["activation_status"].get("is_user_active"))),
        "perawat_list": result,
    }


