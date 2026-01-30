"""Perawat endpoints (FR-TK-001).

Flow:
- Puskesmas membuat akun perawat dengan data lengkap (nama, HP, NIP, email)
- Password otomatis = NIP
- Akun langsung aktif tanpa perlu aktivasi email
- Perawat dapat langsung login dengan email + NIP sebagai password
- Perawat dapat reset password sendiri setelah login

Notes:
- Password awal menggunakan NIP, perawat disarankan ganti setelah login pertama.
"""

from datetime import datetime, timedelta
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_db, require_role
from app.config import settings
from app.core.security import create_access_token, verify_password
from app.crud import crud_user, crud_perawat, crud_puskesmas, crud_ibu_hamil, crud_kerabat
from app.crud.notification import crud_notification
from app.schemas.notification import NotificationCreate
from app.models.user import User
from app.models.perawat import Perawat as PerawatModel
from app.schemas.perawat import (
    PerawatResponse,
    PerawatGenerate,
    PerawatGenerateResponse,
    PerawatUpdate,
    PerawatLoginRequest,
    PerawatLoginResponse,
    PerawatLoginUserInfo,
    PerawatLoginPerawatInfo,
    PerawatResetPasswordRequest,
    TransferAllPatientsRequest,
    TransferSinglePatientRequest,
    TransferPatientResponse,
    TransferPerawatInfo,
    MyNursesResponse,
    MyNurseItem,
    SetRiskLevelRequest,
    SetRiskLevelResponse,
    # Profile Settings Schemas
    PerawatProfileResponse,
    PerawatProfileUpdate,
    PerawatUserUpdate,
    PerawatPatientsResponse,
    PerawatPatientItem,
    PerawatPuskesmasInfo,
)
from app.schemas.user import UserCreate

router = APIRouter(
    prefix="/perawat",
    tags=["Perawat (Nurses)"]
)


def _get_perawat_by_user(db: Session, user_id: int) -> PerawatModel | None:
    return db.query(PerawatModel).filter(PerawatModel.user_id == user_id).first()


def _build_login_url() -> str:
    """Build login URL for perawat."""
    return f"{settings.FRONTEND_BASE_URL.rstrip('/')}/perawat/login"


@router.post(
    "/generate",
    response_model=PerawatGenerateResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Puskesmas membuat akun perawat baru",
    description="""
Membuat akun perawat baru oleh Puskesmas. Akun langsung aktif tanpa proses aktivasi email.

## Autentikasi
- Membutuhkan token dengan role `puskesmas`

## Request Body
| Field | Tipe | Validasi | Keterangan |
|-------|------|----------|------------|
| `nama_lengkap` | string | Min 3, Max 255 karakter | Nama lengkap perawat |
| `nomor_hp` | string | 10-15 digit, boleh diawali + | Format: `081234567890` atau `+6281234567890` |
| `nip` | string | Min 5, Max 50 karakter | NIP perawat (juga sebagai password awal) |
| `email` | string | Format email valid | Email aktif untuk login |

## Validasi Nomor HP
- Spasi dan dash otomatis dihapus
- Harus berisi angka saja (boleh diawali +)
- Panjang 10-15 digit setelah dibersihkan
- Contoh valid: `081234567890`, `+6281234567890`, `0812 3456 7890`

## Flow
1. Puskesmas memasukkan data lengkap perawat
2. Sistem memvalidasi uniqueness (email, NIP, nomor HP)
3. Sistem membuat akun user dan perawat (langsung aktif)
4. Password otomatis menggunakan NIP
5. Perawat dapat langsung login dengan email + NIP sebagai password

## Error Responses
| Status | Keterangan |
|--------|------------|
| 400 | Email/NIP/Nomor HP sudah terdaftar |
| 401 | Token tidak valid atau expired |
| 403 | User bukan role puskesmas |
| 404 | Profil puskesmas tidak ditemukan |
| 422 | Data tidak sesuai validasi (lihat detail error) |

## Contoh Error 422
```json
{
  "detail": "Validation Error",
  "errors": [
    {
      "field": "body -> nomor_hp",
      "message": "Nomor HP harus 10-15 digit",
      "type": "value_error"
    }
  ],
  "hint": "Periksa format data yang dikirim."
}
```
    """,
    responses={
        201: {
            "description": "Akun perawat berhasil dibuat",
            "model": PerawatGenerateResponse
        },
        400: {
            "description": "Email/NIP/Nomor HP sudah terdaftar",
            "content": {
                "application/json": {
                    "example": {"detail": "Email sudah terdaftar"}
                }
            }
        },
        404: {
            "description": "Profil puskesmas tidak ditemukan",
            "content": {
                "application/json": {
                    "example": {"detail": "Puskesmas profile not found for this user"}
                }
            }
        },
        422: {
            "description": "Validation error - data tidak sesuai format",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "Validation Error",
                        "errors": [
                            {
                                "field": "body -> nomor_hp",
                                "message": "Nomor HP harus 10-15 digit",
                                "type": "value_error",
                                "input": "0812"
                            }
                        ],
                        "hint": "Periksa format data yang dikirim."
                    }
                }
            }
        }
    }
)
def generate_perawat_account(
    payload: PerawatGenerate,
    current_user: User = Depends(require_role("puskesmas")),
    db: Session = Depends(get_db),
) -> PerawatGenerateResponse:
    """Puskesmas creates a nurse account. Account is immediately active. Password = NIP."""
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

    # Check phone uniqueness
    if crud_user.get_by_phone(db, phone=payload.nomor_hp):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Nomor HP sudah terdaftar")

    # Create user with password = NIP (account immediately active)
    user = crud_user.create_user(
        db,
        user_in=UserCreate(
            phone=payload.nomor_hp,
            password=payload.nip,  # Password = NIP
            full_name=payload.nama_lengkap,
            role="perawat",
            email=payload.email,
        ),
    )
    user.is_active = True  # Immediately active
    user.is_verified = True  # No email verification needed
    db.add(user)
    db.commit()
    db.refresh(user)

    # Create perawat profile linked to user and puskesmas
    perawat = PerawatModel(
        user_id=user.id,
        puskesmas_id=puskesmas.id,
        nama_lengkap=payload.nama_lengkap,
        email=payload.email,
        nomor_hp=payload.nomor_hp,
        nip=payload.nip,
        is_active=True,  # Immediately active
    )
    db.add(perawat)
    db.commit()
    db.refresh(perawat)

    return PerawatGenerateResponse(
        user_id=user.id,
        perawat_id=perawat.id,
        nama_lengkap=payload.nama_lengkap,
        email=payload.email,
        nomor_hp=payload.nomor_hp,
        nip=payload.nip,
        puskesmas_id=puskesmas.id,
        puskesmas_name=puskesmas.name,
        is_active=True,
        login_url=_build_login_url(),
        message="Akun perawat berhasil dibuat dan langsung aktif. Password awal adalah NIP. Perawat dapat langsung login.",
    )


@router.post(
    "/login",
    response_model=PerawatLoginResponse,
    status_code=status.HTTP_200_OK,
    summary="Login sebagai Perawat",
    description="""
Login endpoint untuk perawat menggunakan email dan password.

## Persyaratan Login
1. **User harus memiliki role `perawat`**
2. **Akun harus aktif** (`is_active = true`)

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
            detail="Akun tidak aktif. Hubungi admin puskesmas.",
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


# ============================================
# PROFILE SETTINGS ENDPOINTS (Self-service)
# ============================================

@router.get(
    "/me",
    response_model=PerawatProfileResponse,
    status_code=status.HTTP_200_OK,
    summary="Lihat profile perawat sendiri",
    description="""
Endpoint untuk perawat melihat profile mereka sendiri.

## Autentikasi
- Membutuhkan token dengan role `perawat`

## Response meliputi:
- **Data pribadi**: nama, email, nomor HP, NIP
- **Foto profile**: URL foto jika ada
- **Info puskesmas**: nama dan alamat puskesmas tempat bekerja
- **Statistik**: jumlah pasien yang sedang ditangani
- **Timestamps**: waktu pembuatan dan update terakhir
    """,
    responses={
        200: {
            "description": "Profile perawat berhasil diambil",
            "model": PerawatProfileResponse
        },
        401: {
            "description": "Token tidak valid atau expired"
        },
        404: {
            "description": "Data perawat tidak ditemukan"
        }
    }
)
def get_my_profile(
    current_user: User = Depends(require_role("perawat")),
    db: Session = Depends(get_db),
) -> PerawatProfileResponse:
    """Get current perawat's own profile."""
    perawat = _get_perawat_by_user(db, user_id=current_user.id)
    if not perawat:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Data perawat tidak ditemukan untuk akun ini"
        )

    # Build puskesmas info
    puskesmas_info = None
    if perawat.puskesmas:
        puskesmas_info = PerawatPuskesmasInfo(
            id=perawat.puskesmas.id,
            name=perawat.puskesmas.name,
            address=perawat.puskesmas.address if hasattr(perawat.puskesmas, 'address') else None,
            phone=perawat.puskesmas.phone if hasattr(perawat.puskesmas, 'phone') else None,
        )

    return PerawatProfileResponse(
        id=perawat.id,
        user_id=perawat.user_id,
        nama_lengkap=perawat.nama_lengkap,
        email=perawat.email,
        nomor_hp=perawat.nomor_hp,
        nip=perawat.nip,
        profile_photo_url=perawat.profile_photo_url,
        is_active=perawat.is_active,
        current_patients=perawat.current_patients or 0,
        puskesmas=puskesmas_info,
        created_at=perawat.created_at,
        updated_at=perawat.updated_at,
    )


@router.patch(
    "/me/profile",
    response_model=PerawatProfileResponse,
    status_code=status.HTTP_200_OK,
    summary="Update profile perawat sendiri",
    description="""
Endpoint untuk perawat mengupdate data profile mereka sendiri.

## Autentikasi
- Membutuhkan token dengan role `perawat`

## Field yang dapat diupdate:
| Field | Tipe | Validasi | Keterangan |
|-------|------|----------|------------|
| `nama_lengkap` | string | Min 3, Max 255 karakter | Nama lengkap perawat |
| `nomor_hp` | string | 10-15 digit, boleh diawali + | Nomor HP perawat |
| `profile_photo_url` | string | Max 500 karakter | URL foto profil (setelah upload) |

## Catatan
- Email dan NIP tidak dapat diubah melalui endpoint ini (gunakan `/me/user` untuk email)
- Untuk mengupload foto, gunakan endpoint `/upload/perawat/profile-photo` terlebih dahulu
- Perubahan nomor HP akan disinkronkan ke data user
    """,
    responses={
        200: {
            "description": "Profile berhasil diupdate",
            "model": PerawatProfileResponse
        },
        400: {
            "description": "Nomor HP sudah terdaftar"
        },
        401: {
            "description": "Token tidak valid atau expired"
        },
        404: {
            "description": "Data perawat tidak ditemukan"
        }
    }
)
def update_my_profile(
    payload: PerawatProfileUpdate,
    current_user: User = Depends(require_role("perawat")),
    db: Session = Depends(get_db),
) -> PerawatProfileResponse:
    """Update current perawat's own profile."""
    perawat = _get_perawat_by_user(db, user_id=current_user.id)
    if not perawat:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Data perawat tidak ditemukan untuk akun ini"
        )

    update_data = payload.model_dump(exclude_unset=True)

    # Validate phone uniqueness if being updated
    if "nomor_hp" in update_data and update_data["nomor_hp"] != perawat.nomor_hp:
        existing_user = crud_user.get_by_phone(db, phone=update_data["nomor_hp"])
        if existing_user and existing_user.id != perawat.user_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Nomor HP sudah terdaftar"
            )

    # Update perawat fields
    for field, value in update_data.items():
        setattr(perawat, field, value)

    # Also update linked user if relevant fields changed
    if perawat.user_id:
        user = crud_user.get(db, perawat.user_id)
        if user:
            if "nama_lengkap" in update_data:
                user.full_name = update_data["nama_lengkap"]
            if "nomor_hp" in update_data:
                user.phone = update_data["nomor_hp"]
            if "profile_photo_url" in update_data:
                user.profile_photo_url = update_data["profile_photo_url"]
            db.add(user)

    db.add(perawat)

    try:
        db.commit()
        db.refresh(perawat)
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Gagal mengupdate profile: {str(e)}"
        )

    # Build response
    puskesmas_info = None
    if perawat.puskesmas:
        puskesmas_info = PerawatPuskesmasInfo(
            id=perawat.puskesmas.id,
            name=perawat.puskesmas.name,
            address=perawat.puskesmas.address if hasattr(perawat.puskesmas, 'address') else None,
            phone=perawat.puskesmas.phone if hasattr(perawat.puskesmas, 'phone') else None,
        )

    return PerawatProfileResponse(
        id=perawat.id,
        user_id=perawat.user_id,
        nama_lengkap=perawat.nama_lengkap,
        email=perawat.email,
        nomor_hp=perawat.nomor_hp,
        nip=perawat.nip,
        profile_photo_url=perawat.profile_photo_url,
        is_active=perawat.is_active,
        current_patients=perawat.current_patients or 0,
        puskesmas=puskesmas_info,
        created_at=perawat.created_at,
        updated_at=perawat.updated_at,
    )


@router.patch(
    "/me/user",
    status_code=status.HTTP_200_OK,
    summary="Update credentials perawat (email/password)",
    description="""
Endpoint untuk perawat mengupdate credentials (email dan/atau password).

## Autentikasi
- Membutuhkan token dengan role `perawat`
- **Wajib** menyertakan `current_password` untuk verifikasi

## Field yang dapat diupdate:
| Field | Tipe | Validasi | Keterangan |
|-------|------|----------|------------|
| `email` | string | Format email valid | Email baru |
| `new_password` | string | Min 6 karakter | Password baru |
| `current_password` | string | **Wajib** | Password saat ini untuk verifikasi |

## Keamanan
- Password saat ini harus benar untuk melakukan perubahan
- Email baru harus unik (belum terdaftar)
- Perubahan email akan disinkronkan ke data perawat

## Catatan
- Setelah mengubah password, gunakan password baru untuk login berikutnya
- Token saat ini tetap valid sampai expired
    """,
    responses={
        200: {
            "description": "Credentials berhasil diupdate",
            "content": {
                "application/json": {
                    "example": {
                        "message": "Credentials berhasil diupdate",
                        "updated_fields": ["email", "password"]
                    }
                }
            }
        },
        400: {
            "description": "Password salah atau email sudah terdaftar"
        },
        401: {
            "description": "Token tidak valid atau expired"
        },
        404: {
            "description": "Data perawat tidak ditemukan"
        }
    }
)
def update_my_user_credentials(
    payload: PerawatUserUpdate,
    current_user: User = Depends(require_role("perawat")),
    db: Session = Depends(get_db),
) -> dict:
    """Update current perawat's user credentials (email/password)."""
    # Verify current password
    if not verify_password(payload.current_password, current_user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password saat ini salah"
        )

    perawat = _get_perawat_by_user(db, user_id=current_user.id)
    if not perawat:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Data perawat tidak ditemukan untuk akun ini"
        )

    updated_fields = []

    # Update email if provided
    if payload.email and payload.email != current_user.email:
        # Check email uniqueness
        existing_user = crud_user.get_by_email(db, email=payload.email)
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email sudah terdaftar"
            )
        existing_perawat = crud_perawat.get_by_email(db, email=payload.email)
        if existing_perawat and existing_perawat.id != perawat.id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email sudah terdaftar sebagai perawat lain"
            )

        # Update email on user and perawat
        current_user.email = payload.email
        perawat.email = payload.email
        updated_fields.append("email")

    # Update password if provided
    if payload.new_password:
        updated = crud_user.update_password(db, user_id=current_user.id, new_password=payload.new_password)
        if not updated:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Gagal mengubah password"
            )
        updated_fields.append("password")

    if not updated_fields:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Tidak ada perubahan yang dilakukan. Sertakan email baru atau password baru."
        )

    # Save changes
    db.add(current_user)
    db.add(perawat)

    try:
        db.commit()
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Gagal mengupdate credentials: {str(e)}"
        )

    return {
        "message": "Credentials berhasil diupdate",
        "updated_fields": updated_fields
    }


@router.get(
    "/me/patients",
    response_model=PerawatPatientsResponse,
    status_code=status.HTTP_200_OK,
    summary="Lihat daftar pasien yang ditangani",
    description="""
Endpoint untuk perawat melihat daftar semua ibu hamil yang terdaftar pada mereka.

## Autentikasi
- Membutuhkan token dengan role `perawat`

## Response meliputi:
- **Statistik ringkasan**: total pasien, jumlah per tingkat risiko
- **Daftar pasien**: nama, kontak, usia kehamilan, tingkat risiko, dll
- **Foto profile**: URL foto jika ada

## Filter pasien
Semua pasien yang ditampilkan adalah pasien aktif (`is_active = true`).

## Sorting
Pasien diurutkan berdasarkan:
1. Tingkat risiko (tinggi → sedang → rendah → belum ditentukan)
2. HPL terdekat (yang akan melahirkan lebih dulu)
    """,
    responses={
        200: {
            "description": "Daftar pasien berhasil diambil",
            "model": PerawatPatientsResponse
        },
        401: {
            "description": "Token tidak valid atau expired"
        },
        404: {
            "description": "Data perawat tidak ditemukan"
        }
    }
)
def get_my_patients(
    current_user: User = Depends(require_role("perawat")),
    db: Session = Depends(get_db),
) -> PerawatPatientsResponse:
    """Get list of patients assigned to current perawat."""
    perawat = _get_perawat_by_user(db, user_id=current_user.id)
    if not perawat:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Data perawat tidak ditemukan untuk akun ini"
        )

    # Get all patients assigned to this perawat
    patients = crud_ibu_hamil.get_by_perawat(db, perawat_id=perawat.id)

    # Count by risk level
    risk_counts = {
        "rendah": 0,
        "sedang": 0,
        "tinggi": 0,
        "belum_ditentukan": 0
    }

    patient_items = []
    for patient in patients:
        # Count risk levels
        if patient.risk_level:
            risk_level = patient.risk_level.lower()
            if risk_level in risk_counts:
                risk_counts[risk_level] += 1
            else:
                risk_counts["belum_ditentukan"] += 1
        else:
            risk_counts["belum_ditentukan"] += 1

        # Build patient item
        patient_items.append(PerawatPatientItem(
            id=patient.id,
            nama_lengkap=patient.nama_lengkap,
            nik=patient.nik if hasattr(patient, 'nik') else None,
            nomor_hp=patient.nomor_hp if hasattr(patient, 'nomor_hp') else None,
            tanggal_lahir=patient.tanggal_lahir.isoformat() if hasattr(patient, 'tanggal_lahir') and patient.tanggal_lahir else None,
            usia_kehamilan_minggu=patient.usia_kehamilan_minggu if hasattr(patient, 'usia_kehamilan_minggu') else None,
            usia_kehamilan_hari=patient.usia_kehamilan_hari if hasattr(patient, 'usia_kehamilan_hari') else None,
            hpht=patient.hpht.isoformat() if hasattr(patient, 'hpht') and patient.hpht else None,
            hpl=patient.hpl.isoformat() if hasattr(patient, 'hpl') and patient.hpl else None,
            risk_level=patient.risk_level,
            profile_photo_url=patient.profile_photo_url if hasattr(patient, 'profile_photo_url') else None,
            is_active=patient.is_active if hasattr(patient, 'is_active') else True,
            created_at=patient.created_at.isoformat() if hasattr(patient, 'created_at') and patient.created_at else None,
        ))

    # Sort by risk level (tinggi first) and then by HPL
    risk_order = {"tinggi": 0, "sedang": 1, "rendah": 2, None: 3}
    patient_items.sort(key=lambda p: (risk_order.get(p.risk_level.lower() if p.risk_level else None, 3), p.hpl or "9999-12-31"))

    return PerawatPatientsResponse(
        perawat_id=perawat.id,
        perawat_nama=perawat.nama_lengkap,
        total_patients=len(patient_items),
        patients_by_risk=risk_counts,
        patients=patient_items
    )


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
    response_model=MyNursesResponse,
    status_code=status.HTTP_200_OK,
    summary="List perawat milik puskesmas (untuk admin puskesmas)",
    description="""
Endpoint untuk puskesmas admin melihat daftar semua perawat yang terdaftar di puskesmas mereka.

## Autentikasi
Membutuhkan token dengan role `puskesmas`.

## Response meliputi:
- **puskesmas_id**: ID puskesmas
- **puskesmas_name**: Nama puskesmas
- **total_perawat**: Jumlah total perawat terdaftar
- **perawat_aktif**: Jumlah perawat yang aktif
- **perawat_list**: Daftar detail perawat (id, nama, email, NIP, status, jumlah pasien, dll)
    """,
)
def list_my_nurses(
    current_user: User = Depends(require_role("puskesmas")),
    db: Session = Depends(get_db),
) -> MyNursesResponse:
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
        result.append(MyNurseItem(
            id=perawat.id,
            user_id=perawat.user_id,
            nama_lengkap=perawat.nama_lengkap,
            email=perawat.email,
            nomor_hp=perawat.nomor_hp,
            nip=perawat.nip,
            profile_photo_url=perawat.profile_photo_url,
            is_active=perawat.is_active,
            current_patients=perawat.current_patients or 0,
            created_at=perawat.created_at.isoformat() if perawat.created_at else None,
            updated_at=perawat.updated_at.isoformat() if perawat.updated_at else None,
        ))

    return MyNursesResponse(
        puskesmas_id=puskesmas.id,
        puskesmas_name=puskesmas.name,
        total_perawat=len(result),
        perawat_aktif=sum(1 for p in result if p.is_active),
        perawat_list=result,
    )


@router.patch(
    "/{perawat_id}",
    response_model=PerawatResponse,
    status_code=status.HTTP_200_OK,
    summary="Update data perawat",
    description="""
Update data perawat oleh admin puskesmas.

## Field yang dapat diupdate:
- **nama_lengkap**: Nama lengkap perawat
- **nomor_hp**: Nomor HP perawat
- **email**: Email perawat
- **nip**: NIP perawat
- **is_active**: Status aktif perawat
- **profile_photo_url**: URL foto profil

## Validasi:
- Hanya admin puskesmas yang dapat update
- Perawat harus milik puskesmas yang sama
- Email dan NIP harus unik (jika diubah)
    """,
)
def update_perawat(
    perawat_id: int,
    payload: PerawatUpdate,
    current_user: User = Depends(require_role("puskesmas")),
    db: Session = Depends(get_db),
) -> PerawatModel:
    """Update perawat data by puskesmas admin."""
    # Get puskesmas for current admin
    puskesmas = crud_puskesmas.get_by_admin_user_id(db, admin_user_id=current_user.id)
    if not puskesmas:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Puskesmas tidak ditemukan untuk user ini"
        )

    # Get perawat
    perawat = crud_perawat.get(db, perawat_id)
    if not perawat:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Perawat tidak ditemukan"
        )

    # Verify perawat belongs to this puskesmas
    if perawat.puskesmas_id != puskesmas.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Perawat bukan dari puskesmas Anda"
        )

    # Get update data (only fields that are set)
    update_data = payload.model_dump(exclude_unset=True)

    # Validate email uniqueness if being updated
    if "email" in update_data and update_data["email"] != perawat.email:
        existing_user = crud_user.get_by_email(db, email=update_data["email"])
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email sudah terdaftar"
            )
        existing_perawat = crud_perawat.get_by_email(db, email=update_data["email"])
        if existing_perawat and existing_perawat.id != perawat_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email sudah terdaftar sebagai perawat lain"
            )

    # Validate NIP uniqueness if being updated
    if "nip" in update_data and update_data["nip"] != perawat.nip:
        existing_perawat = crud_perawat.get_by_nip(db, nip=update_data["nip"])
        if existing_perawat and existing_perawat.id != perawat_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="NIP sudah terdaftar"
            )

    # Validate phone uniqueness if being updated
    if "nomor_hp" in update_data and update_data["nomor_hp"] != perawat.nomor_hp:
        existing_user = crud_user.get_by_phone(db, phone=update_data["nomor_hp"])
        if existing_user and existing_user.id != perawat.user_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Nomor HP sudah terdaftar"
            )

    # Update perawat fields
    for field, value in update_data.items():
        setattr(perawat, field, value)

    # Also update linked user if relevant fields changed
    if perawat.user_id:
        user = crud_user.get(db, perawat.user_id)
        if user:
            if "email" in update_data:
                user.email = update_data["email"]
            if "nama_lengkap" in update_data:
                user.full_name = update_data["nama_lengkap"]
            if "nomor_hp" in update_data:
                user.phone = update_data["nomor_hp"]
            if "profile_photo_url" in update_data:
                user.profile_photo_url = update_data["profile_photo_url"]
            if "is_active" in update_data:
                user.is_active = update_data["is_active"]
            db.add(user)

    db.add(perawat)

    try:
        db.commit()
        db.refresh(perawat)
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Gagal mengupdate perawat: {str(e)}"
        )

    return perawat


@router.delete(
    "/{perawat_id}",
    status_code=status.HTTP_200_OK,
    summary="Hapus akun perawat",
    description="""
Hapus akun perawat oleh admin puskesmas.

## Validasi:
- Hanya admin puskesmas yang dapat menghapus
- Perawat harus milik puskesmas yang sama
- Perawat yang masih memiliki pasien tidak dapat dihapus (harus transfer dulu)

## Efek:
- Data perawat akan dihapus dari database
- Data user yang terkait juga akan dihapus
    """,
)
def delete_perawat(
    perawat_id: int,
    current_user: User = Depends(require_role("puskesmas")),
    db: Session = Depends(get_db),
) -> dict:
    """Delete perawat by puskesmas admin."""
    # Get puskesmas for current admin
    puskesmas = crud_puskesmas.get_by_admin_user_id(db, admin_user_id=current_user.id)
    if not puskesmas:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Puskesmas tidak ditemukan untuk user ini"
        )

    # Get perawat
    perawat = crud_perawat.get(db, perawat_id)
    if not perawat:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Perawat tidak ditemukan"
        )

    # Verify perawat belongs to this puskesmas
    if perawat.puskesmas_id != puskesmas.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Perawat bukan dari puskesmas Anda"
        )

    # Check if perawat has patients
    patients = crud_ibu_hamil.get_by_perawat(db, perawat_id=perawat_id)
    if patients:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Tidak dapat menghapus perawat yang masih memiliki {len(patients)} pasien. Silakan transfer pasien terlebih dahulu."
        )

    # Store info for response
    perawat_info = {
        "id": perawat.id,
        "nama_lengkap": perawat.nama_lengkap,
        "email": perawat.email,
        "nip": perawat.nip,
    }
    user_id = perawat.user_id

    # Delete perawat
    db.delete(perawat)

    # Delete linked user if exists
    if user_id:
        user = crud_user.get(db, user_id)
        if user:
            db.delete(user)

    try:
        db.commit()
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Gagal menghapus perawat: {str(e)}"
        )

    return {
        "message": f"Perawat {perawat_info['nama_lengkap']} berhasil dihapus",
        "deleted_perawat": perawat_info,
    }


@router.post(
    "/{source_perawat_id}/transfer-all-patients",
    response_model=TransferPatientResponse,
    status_code=status.HTTP_200_OK,
    summary="Transfer semua pasien ke perawat lain (bulk transfer)",
    description="""
Transfer semua pasien (ibu hamil) dari satu perawat ke perawat lain.

## Kegunaan
- Menangani kasus perawat resign atau tidak aktif
- Memindahkan seluruh beban kerja ke perawat pengganti

## Validasi
- Kedua perawat harus dari puskesmas yang sama
- Perawat sumber harus memiliki minimal 1 pasien
- Perawat tujuan harus aktif
- Hanya admin puskesmas yang dapat melakukan transfer

## Efek
- Semua `ibu_hamil.perawat_id` yang sebelumnya merujuk ke perawat sumber akan diubah ke perawat tujuan
- `current_patients` perawat sumber akan menjadi 0
- `current_patients` perawat tujuan akan bertambah sesuai jumlah pasien yang dipindahkan
    """,
)
def transfer_all_patients(
    source_perawat_id: int,
    payload: TransferAllPatientsRequest,
    current_user: User = Depends(require_role("puskesmas")),
    db: Session = Depends(get_db),
) -> TransferPatientResponse:
    """Transfer all patients from one perawat to another."""
    # Get puskesmas for current admin
    puskesmas = crud_puskesmas.get_by_admin_user_id(db, admin_user_id=current_user.id)
    if not puskesmas:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Puskesmas tidak ditemukan untuk user ini"
        )

    # Get source perawat
    source_perawat = crud_perawat.get(db, source_perawat_id)
    if not source_perawat:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Perawat sumber tidak ditemukan"
        )

    # Verify source perawat belongs to this puskesmas
    if source_perawat.puskesmas_id != puskesmas.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Perawat sumber bukan dari puskesmas Anda"
        )

    # Get target perawat
    target_perawat = crud_perawat.get(db, payload.target_perawat_id)
    if not target_perawat:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Perawat tujuan tidak ditemukan"
        )

    # Verify target perawat belongs to same puskesmas
    if target_perawat.puskesmas_id != puskesmas.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Perawat tujuan bukan dari puskesmas Anda"
        )

    # Cannot transfer to same perawat
    if source_perawat_id == payload.target_perawat_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Tidak dapat memindahkan pasien ke perawat yang sama"
        )

    # Check target perawat is active
    if not target_perawat.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Perawat tujuan tidak aktif"
        )

    # Get all patients from source perawat
    patients = crud_ibu_hamil.get_by_perawat(db, perawat_id=source_perawat_id)
    if not patients:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Perawat sumber tidak memiliki pasien untuk dipindahkan"
        )

    transferred_ids = []
    transferred_count = 0

    # Transfer all patients
    for patient in patients:
        patient.perawat_id = payload.target_perawat_id
        db.add(patient)
        transferred_ids.append(patient.id)
        transferred_count += 1

    # Update workload counters
    source_perawat.current_patients = 0
    target_perawat.current_patients = (target_perawat.current_patients or 0) + transferred_count

    db.add(source_perawat)
    db.add(target_perawat)

    try:
        db.commit()
        db.refresh(source_perawat)
        db.refresh(target_perawat)
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Gagal memindahkan pasien: {str(e)}"
        )

    return TransferPatientResponse(
        success=True,
        message=f"Berhasil memindahkan {transferred_count} pasien dari {source_perawat.nama_lengkap} ke {target_perawat.nama_lengkap}",
        transferred_count=transferred_count,
        source_perawat=TransferPerawatInfo(
            id=source_perawat.id,
            nama_lengkap=source_perawat.nama_lengkap,
            current_patients=source_perawat.current_patients or 0
        ),
        target_perawat=TransferPerawatInfo(
            id=target_perawat.id,
            nama_lengkap=target_perawat.nama_lengkap,
            current_patients=target_perawat.current_patients or 0
        ),
        transferred_patients=transferred_ids
    )


@router.post(
    "/{source_perawat_id}/transfer-patient",
    response_model=TransferPatientResponse,
    status_code=status.HTTP_200_OK,
    summary="Transfer satu pasien ke perawat lain",
    description="""
Transfer satu pasien (ibu hamil) dari satu perawat ke perawat lain.

## Kegunaan
- Menyeimbangkan beban kerja antar perawat
- Memindahkan pasien sesuai kebutuhan spesifik

## Validasi
- Kedua perawat harus dari puskesmas yang sama
- Pasien harus sedang ditangani oleh perawat sumber
- Perawat tujuan harus aktif
- Hanya admin puskesmas yang dapat melakukan transfer

## Efek
- `ibu_hamil.perawat_id` akan diubah ke perawat tujuan
- `current_patients` perawat sumber akan berkurang 1
- `current_patients` perawat tujuan akan bertambah 1
    """,
)
def transfer_single_patient(
    source_perawat_id: int,
    payload: TransferSinglePatientRequest,
    current_user: User = Depends(require_role("puskesmas")),
    db: Session = Depends(get_db),
) -> TransferPatientResponse:
    """Transfer a single patient from one perawat to another."""
    # Get puskesmas for current admin
    puskesmas = crud_puskesmas.get_by_admin_user_id(db, admin_user_id=current_user.id)
    if not puskesmas:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Puskesmas tidak ditemukan untuk user ini"
        )

    # Get source perawat
    source_perawat = crud_perawat.get(db, source_perawat_id)
    if not source_perawat:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Perawat sumber tidak ditemukan"
        )

    # Verify source perawat belongs to this puskesmas
    if source_perawat.puskesmas_id != puskesmas.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Perawat sumber bukan dari puskesmas Anda"
        )

    # Get target perawat
    target_perawat = crud_perawat.get(db, payload.target_perawat_id)
    if not target_perawat:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Perawat tujuan tidak ditemukan"
        )

    # Verify target perawat belongs to same puskesmas
    if target_perawat.puskesmas_id != puskesmas.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Perawat tujuan bukan dari puskesmas Anda"
        )

    # Cannot transfer to same perawat
    if source_perawat_id == payload.target_perawat_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Tidak dapat memindahkan pasien ke perawat yang sama"
        )

    # Check target perawat is active
    if not target_perawat.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Perawat tujuan tidak aktif"
        )

    # Get the patient
    patient = crud_ibu_hamil.get(db, payload.ibu_hamil_id)
    if not patient:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Pasien tidak ditemukan"
        )

    # Verify patient is currently assigned to source perawat
    if patient.perawat_id != source_perawat_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Pasien tidak sedang ditangani oleh perawat sumber"
        )

    # Verify patient belongs to same puskesmas
    if patient.puskesmas_id != puskesmas.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Pasien bukan dari puskesmas Anda"
        )

    # Transfer patient
    patient.perawat_id = payload.target_perawat_id
    db.add(patient)

    # Update workload counters
    source_perawat.current_patients = max(0, (source_perawat.current_patients or 0) - 1)
    target_perawat.current_patients = (target_perawat.current_patients or 0) + 1

    db.add(source_perawat)
    db.add(target_perawat)

    try:
        db.commit()
        db.refresh(source_perawat)
        db.refresh(target_perawat)
        db.refresh(patient)
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Gagal memindahkan pasien: {str(e)}"
        )

    return TransferPatientResponse(
        success=True,
        message=f"Berhasil memindahkan 1 pasien dari {source_perawat.nama_lengkap} ke {target_perawat.nama_lengkap}",
        transferred_count=1,
        source_perawat=TransferPerawatInfo(
            id=source_perawat.id,
            nama_lengkap=source_perawat.nama_lengkap,
            current_patients=source_perawat.current_patients or 0
        ),
        target_perawat=TransferPerawatInfo(
            id=target_perawat.id,
            nama_lengkap=target_perawat.nama_lengkap,
            current_patients=target_perawat.current_patients or 0
        ),
        transferred_patients=[patient.id]
    )


@router.patch(
    "/me/patients/{ibu_hamil_id}/risk-level",
    response_model=SetRiskLevelResponse,
    status_code=status.HTTP_200_OK,
    summary="Tentukan tingkat risiko kehamilan ibu hamil",
    description="""
Endpoint untuk perawat menentukan tingkat risiko kehamilan seorang ibu hamil yang terdaftar pada perawat tersebut.

## Autentikasi
- Membutuhkan token dengan role `perawat`

## Persyaratan
- Ibu hamil harus terdaftar pada perawat yang sedang login (perawat_id pada ibu hamil harus sama dengan perawat yang login)
- Ibu hamil harus aktif

## Tingkat Risiko
| Level | Keterangan |
|-------|------------|
| `rendah` | Kehamilan dengan risiko rendah |
| `sedang` | Kehamilan dengan risiko sedang |
| `tinggi` | Kehamilan dengan risiko tinggi |

## Efek
- Field `risk_level` pada ibu hamil akan diupdate
- Field `risk_level_set_by` akan diisi dengan ID perawat
- Field `risk_level_set_at` akan diisi dengan waktu saat ini

## Error Responses
| Status | Keterangan |
|--------|------------|
| 400 | Tingkat risiko tidak valid |
| 401 | Token tidak valid atau expired |
| 403 | Ibu hamil tidak terdaftar pada perawat ini |
| 404 | Perawat atau ibu hamil tidak ditemukan |
    """,
    responses={
        200: {
            "description": "Tingkat risiko berhasil ditentukan",
            "model": SetRiskLevelResponse
        },
        400: {
            "description": "Tingkat risiko tidak valid",
            "content": {
                "application/json": {
                    "example": {"detail": "Tingkat risiko harus salah satu dari: rendah, sedang, tinggi"}
                }
            }
        },
        403: {
            "description": "Ibu hamil tidak terdaftar pada perawat ini",
            "content": {
                "application/json": {
                    "example": {"detail": "Anda tidak memiliki akses untuk mengubah data ibu hamil ini. Ibu hamil tidak terdaftar pada Anda."}
                }
            }
        },
        404: {
            "description": "Data tidak ditemukan",
            "content": {
                "application/json": {
                    "example": {"detail": "Ibu hamil tidak ditemukan"}
                }
            }
        }
    }
)
def set_patient_risk_level(
    ibu_hamil_id: int,
    payload: SetRiskLevelRequest,
    current_user: User = Depends(require_role("perawat")),
    db: Session = Depends(get_db),
) -> SetRiskLevelResponse:
    """Perawat menentukan tingkat risiko kehamilan ibu hamil yang terdaftar padanya."""
    # Get perawat profile for current user
    perawat = _get_perawat_by_user(db, user_id=current_user.id)
    if not perawat:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Data perawat tidak ditemukan untuk akun ini"
        )

    # Check perawat is active
    if not perawat.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Akun perawat tidak aktif"
        )

    # Get ibu hamil
    ibu_hamil = crud_ibu_hamil.get(db, ibu_hamil_id)
    if not ibu_hamil:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Ibu hamil tidak ditemukan"
        )

    # Check ibu hamil is active
    if not ibu_hamil.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Ibu hamil tidak aktif"
        )

    # Verify ibu hamil is assigned to this perawat
    if ibu_hamil.perawat_id != perawat.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Anda tidak memiliki akses untuk mengubah data ibu hamil ini. Ibu hamil tidak terdaftar pada Anda."
        )

    # Update risk level
    current_time = datetime.utcnow()
    ibu_hamil.risk_level = payload.risk_level
    ibu_hamil.risk_level_set_by = perawat.id
    ibu_hamil.risk_level_set_at = current_time

    db.add(ibu_hamil)

    try:
        db.commit()
        db.refresh(ibu_hamil)
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Gagal mengupdate tingkat risiko: {str(e)}"
        )

    # Send notification to kerabat if risk level is tinggi or sedang
    if payload.risk_level in ["tinggi", "sedang"]:
        kerabat_list = crud_kerabat.get_by_ibu_hamil(db, ibu_hamil_id=ibu_hamil.id)
        for kerabat in kerabat_list:
            if kerabat.can_receive_notifications and kerabat.kerabat_user_id:
                priority = "urgent" if payload.risk_level == "tinggi" else "high"
                title = f"Status Risiko Kehamilan: {payload.risk_level.upper()}"
                if payload.risk_level == "tinggi":
                    message = (
                        f"PERHATIAN: {ibu_hamil.nama_lengkap} memiliki status risiko kehamilan TINGGI. "
                        f"Segera hubungi perawat jika ada keluhan. Pantau kondisi secara rutin."
                    )
                else:
                    message = (
                        f"INFO: {ibu_hamil.nama_lengkap} memiliki status risiko kehamilan SEDANG. "
                        f"Pastikan pemeriksaan rutin dilakukan sesuai jadwal."
                    )

                try:
                    notification_data = NotificationCreate(
                        user_id=kerabat.kerabat_user_id,
                        title=title,
                        message=message,
                        notification_type="health_alert",
                        priority=priority,
                        sent_via="in_app",
                        related_entity_type="ibu_hamil",
                        related_entity_id=ibu_hamil.id,
                    )
                    crud_notification.create(db, obj_in=notification_data)
                except Exception:
                    pass  # Don't fail main operation if notification fails

    return SetRiskLevelResponse(
        success=True,
        message="Tingkat risiko kehamilan berhasil ditentukan",
        ibu_hamil_id=ibu_hamil.id,
        ibu_hamil_nama=ibu_hamil.nama_lengkap,
        risk_level=ibu_hamil.risk_level,
        risk_level_set_by=perawat.id,
        risk_level_set_by_nama=perawat.nama_lengkap,
        risk_level_set_at=current_time
    )
