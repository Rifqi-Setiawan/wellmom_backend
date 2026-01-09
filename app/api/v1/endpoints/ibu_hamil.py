"""Ibu Hamil (Pregnant Women) endpoints."""

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status, File, UploadFile
from pydantic import BaseModel, ConfigDict
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_active_user, get_db, require_role
from app.core.security import create_access_token
from app.core.exceptions import (
    InvalidCredentialsException,
    EmailNotFoundException,
    AccountInactiveException,
    NotIbuHamilException,
    IbuHamilProfileNotFoundException,
)
from app.crud import (
    crud_ibu_hamil,
    crud_kerabat,
    crud_notification,
    crud_perawat,
    crud_puskesmas,
    crud_user,
)
from app.models.ibu_hamil import IbuHamil
from app.models.user import User
from app.schemas.ibu_hamil import (
    IbuHamilCreate,
    IbuHamilLoginRequest,
    IbuHamilLoginResponse,
    IbuHamilResponse,
    IbuHamilUpdate,
)
from app.schemas.notification import NotificationCreate
from app.schemas.puskesmas import PuskesmasResponse
from app.schemas.user import UserCreate, UserResponse
from app.utils.file_handler import save_profile_photo

router = APIRouter(
    prefix="/ibu-hamil",
    tags=["Ibu Hamil (Pregnant Women)"],
)


class IbuHamilRegisterRequest(BaseModel):
    """Payload to register pregnant woman and user (if new)."""

    user: UserCreate
    ibu_hamil: IbuHamilCreate
    
    model_config = ConfigDict(json_schema_extra={
        "example": {
            "user": {
                "email": "siti.aminah@example.com",
                "phone": "+6281234567890",
                "password": "SecurePassword123!",
                "full_name": "Siti Aminah",
                "role": "ibu_hamil"
            },
            "ibu_hamil": {
                "nama_lengkap": "Siti Aminah",
                "nik": "3175091201850001",
                "date_of_birth": "1985-12-12",
                "address": "Jl. Mawar No. 10, RT 02 RW 05, Kelurahan Sungai Penuh",
                "location": [101.3912, -2.0645],
                "provinsi": "Jambi",
                "kota_kabupaten": "Kerinci",
                "kelurahan": "Sungai Penuh",
                "kecamatan": "Pesisir Bukit",
                "emergency_contact_name": "Budi (Suami)",
                "emergency_contact_phone": "+6281298765432",
                "emergency_contact_relation": "Suami",
                "last_menstrual_period": "2024-12-01",
                "estimated_due_date": "2025-09-08",
                "usia_kehamilan": 8,
                "kehamilan_ke": 2,
                "jumlah_anak": 1,
                "jarak_kehamilan_terakhir": "2 tahun",
                "miscarriage_number": 0,
                "previous_pregnancy_complications": "Tidak ada",
                "pernah_caesar": False,
                "pernah_perdarahan_saat_hamil": False,
                "riwayat_kesehatan_ibu": {
                    "darah_tinggi": False,
                    "diabetes": False,
                    "anemia": False,
                    "penyakit_jantung": False,
                    "asma": False,
                    "penyakit_ginjal": False,
                    "tbc_malaria": False
                },
                "age": 39,
                "blood_type": "O+",
                "risk_level": "normal",
                "healthcare_preference": "puskesmas",
                "whatsapp_consent": True,
                "data_sharing_consent": False
            }
        }
    })


class AssignToPuskesmasRequest(BaseModel):
    """Request body untuk assign ibu hamil ke puskesmas."""
    puskesmas_id: int

    model_config = ConfigDict(json_schema_extra={
        "example": {
            "puskesmas_id": 2
        }
    })


class AssignToPerawatRequest(BaseModel):
    """Request body untuk assign ibu hamil ke perawat."""
    perawat_id: int

    model_config = ConfigDict(json_schema_extra={
        "example": {
            "perawat_id": 3
        }
    })


class AutoAssignResponse(BaseModel):
    ibu_hamil: IbuHamilResponse
    puskesmas: PuskesmasResponse
    distance_km: float

    model_config = ConfigDict(json_schema_extra={
        "example": {
            "ibu_hamil": {
                "id": 1,
                "puskesmas_id": 2,
                "perawat_id": 3,
                "nik": "3175091201850001",
                "location": [101.39, -2.06],
                "address": "Jl. Mawar No. 10",
                "emergency_contact_name": "Budi",
                "emergency_contact_phone": "+6281234567890",
                "is_active": True,
            },
            "puskesmas": {
                "id": 2,
                "name": "Puskesmas Sungai Penuh",
                "code": "PKM-ABC-123",
                "registration_status": "approved",
                "is_active": True,
            },
            "distance_km": 1.2,
        }
    })


# Helper functions ---------------------------------------------------------

def _get_ibu_or_404(db: Session, ibu_id: int) -> IbuHamil:
    ibu = crud_ibu_hamil.get(db, id=ibu_id)
    if not ibu:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Ibu Hamil not found",
        )
    return ibu


def _is_puskesmas_admin(current_user: User, ibu: IbuHamil, db: Session) -> bool:
    if not ibu.puskesmas_id:
        return False
    pusk = crud_puskesmas.get(db, id=ibu.puskesmas_id)
    return bool(pusk and pusk.admin_user_id == current_user.id)


def _is_perawat_assigned(current_user: User, ibu: IbuHamil) -> bool:
    return current_user.role == "perawat" and ibu.perawat_id is not None and current_user.id == ibu.perawat_id


def _is_kerabat_linked(current_user: User, ibu: IbuHamil, db: Session) -> bool:
    if current_user.role != "kerabat":
        return False
    relations = crud_kerabat.get_by_kerabat_user(db, kerabat_user_id=current_user.id)
    return any(rel.ibu_hamil_id == ibu.id for rel in relations)


def _authorize_view(ibu: IbuHamil, current_user: User, db: Session) -> None:
    """Authorize access to an IbuHamil record."""
    # Super admin dapat melihat semua data (read-only)
    if current_user.role == "super_admin":
        return
    if ibu.user_id == current_user.id:
        return
    if _is_puskesmas_admin(current_user, ibu, db):
        return
    if _is_perawat_assigned(current_user, ibu):
        return
    if _is_kerabat_linked(current_user, ibu, db):
        return
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Not authorized to access this record",
    )


def _authorize_update(ibu: IbuHamil, current_user: User, db: Session) -> None:
    """Authorize update to an IbuHamil record."""
    # Super admin tidak dapat update (read-only)
    if current_user.role == "super_admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Super admin tidak dapat mengupdate data ibu hamil (read-only access).",
        )
        return
    if ibu.user_id == current_user.id:
        return
    if _is_puskesmas_admin(current_user, ibu, db):
        return
    if _is_perawat_assigned(current_user, ibu):
        return
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Not authorized to update this record",
    )


def _auto_assign_nearest(
    db: Session,
    ibu: IbuHamil,
    radius_km: float = 20.0,
):
    """Auto-assign to nearest approved Puskesmas with capacity and an available Perawat."""
    nearest_list = crud_ibu_hamil.find_nearest_puskesmas(db, ibu_id=ibu.id, radius_km=radius_km)
    for puskesmas, distance in nearest_list:
        if puskesmas.registration_status != "approved" or not puskesmas.is_active:
            continue

        assigned_ibu = crud_ibu_hamil.assign_to_puskesmas(
            db,
            ibu_id=ibu.id,
            puskesmas_id=puskesmas.id,
            distance_km=float(distance),
        )

        # Pick first available perawat in that puskesmas
        perawats = crud_perawat.get_available(db, puskesmas_id=puskesmas.id)
        if perawats:
            perawat = perawats[0]
            crud_ibu_hamil.assign_to_perawat(db, ibu_id=ibu.id, perawat_id=perawat.id)
            crud_perawat.update_workload(db, perawat_id=perawat.id, increment=1)

        # Create notification for ibu user
        notification_in = NotificationCreate(
            user_id=ibu.user_id,
            title="Penugasan Puskesmas",
            message=f"Anda telah ditugaskan ke {puskesmas.name}.",
            notification_type="assignment",
            priority="normal",
            sent_via="in_app",
        )
        crud_notification.create(db, obj_in=notification_in)

        return assigned_ibu, puskesmas, float(distance)

    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="Tidak ada Puskesmas terdekat dengan kapasitas tersedia dalam radius",
    )


# Endpoints ---------------------------------------------------------------


@router.post(
    "/register",
    response_model=dict,
    status_code=status.HTTP_201_CREATED,
    summary="Registrasi ibu hamil",
    description="Publik atau user terautentikasi dapat mendaftarkan ibu hamil. Membuat user (role ibu_hamil) bila belum ada, lalu membuat profil ibu hamil dan auto-assign Puskesmas terdekat jika lokasi tersedia.",
    responses={
        201: {
            "description": "Registrasi berhasil, user dan profil ibu hamil telah dibuat",
            "content": {
                "application/json": {
                    "example": {
                        "ibu_hamil": {"id": 1, "nama_lengkap": "Siti Aminah", "nik": "3175091201850001"},
                        "user": {"id": 1, "phone": "+6281234567890", "full_name": "Siti Aminah"},
                        "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                        "token_type": "bearer",
                        "assignment": {
                            "puskesmas": {"id": 1, "name": "Puskesmas Sungai Penuh"},
                            "distance_km": 1.2
                        }
                    }
                }
            }
        },
        400: {
            "description": "Data tidak valid atau sudah terdaftar",
            "content": {
                "application/json": {
                    "examples": {
                        "nik_exists": {
                            "summary": "NIK sudah terdaftar",
                            "value": {"detail": "NIK sudah terdaftar di sistem. Setiap NIK hanya dapat digunakan sekali."}
                        },
                        "phone_different_role": {
                            "summary": "Nomor telepon terdaftar dengan role berbeda",
                            "value": {"detail": "Nomor telepon sudah terdaftar dengan role perawat. Silakan gunakan nomor lain atau login dengan akun yang ada."}
                        },
                        "phone_already_ibu_hamil": {
                            "summary": "Nomor telepon sudah terdaftar sebagai ibu hamil",
                            "value": {"detail": "Nomor telepon ini sudah terdaftar sebagai ibu hamil. Silakan login menggunakan akun yang ada."}
                        },
                        "email_different_role": {
                            "summary": "Email terdaftar dengan role berbeda",
                            "value": {"detail": "Email sudah terdaftar dengan role perawat. Silakan gunakan email lain."}
                        },
                        "email_already_ibu_hamil": {
                            "summary": "Email sudah terdaftar sebagai ibu hamil",
                            "value": {"detail": "Email ini sudah terdaftar sebagai ibu hamil. Silakan login menggunakan akun yang ada."}
                        },
                        "invalid_location": {
                            "summary": "Koordinat lokasi tidak valid",
                            "value": {"detail": "Koordinat lokasi tidak valid. Longitude harus antara -180 hingga 180, dan Latitude antara -90 hingga 90."}
                        }
                    }
                }
            }
        },
        422: {
            "description": "Validation error pada data input",
            "content": {
                "application/json": {
                    "example": {
                        "detail": [
                            {
                                "loc": ["body", "ibu_hamil", "nik"],
                                "msg": "NIK must be exactly 16 digits",
                                "type": "value_error"
                            }
                        ]
                    }
                }
            }
        },
        500: {
            "description": "Kesalahan server internal",
            "content": {
                "application/json": {
                    "example": {"detail": "Terjadi kesalahan saat memproses registrasi. Silakan coba lagi."}
                }
            }
        }
    }
)
async def register_ibu_hamil(
    payload: IbuHamilRegisterRequest,
    db: Session = Depends(get_db),
) -> dict:
    """
    Registrasi ibu hamil baru dengan validasi lengkap.
    
    Proses registrasi:
    1. Validasi data input (NIK, phone, email, location)
    2. Cek apakah phone sudah terdaftar (jika sudah sebagai ibu hamil, tolak)
    3. Cek apakah email sudah terdaftar (jika sudah sebagai ibu hamil, tolak)
    4. Cek apakah NIK sudah terdaftar
    5. Buat user account (jika belum ada)
    6. Buat profil ibu hamil
    7. Auto-assign ke Puskesmas terdekat (jika lokasi tersedia)
    8. Generate access token
    
    Returns:
        dict: User info, ibu hamil profile, access token, dan assignment info
    
    Raises:
        HTTPException 400: NIK/phone/email sudah terdaftar atau data tidak valid
        HTTPException 422: Validation error pada input
        HTTPException 500: Database atau server error
    """
    try:
        # Ensure role is ibu_hamil
        user_in = payload.user.model_copy(update={"role": "ibu_hamil"})

        # Validate: Check if phone already exists with different role
        existing_user = crud_user.get_by_phone(db, phone=user_in.phone)
        if existing_user:
            if existing_user.role != "ibu_hamil":
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Nomor telepon sudah terdaftar dengan role {existing_user.role}. Silakan gunakan nomor lain atau login dengan akun yang ada."
                )
            # Check if this user already has an ibu_hamil profile
            existing_ibu_for_user = db.query(IbuHamil).filter(IbuHamil.user_id == existing_user.id).first()
            if existing_ibu_for_user:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Nomor telepon ini sudah terdaftar sebagai ibu hamil. Silakan login menggunakan akun yang ada."
                )
            user_obj = existing_user
        else:
            # Validate: Check if email already exists (if provided)
            if user_in.email:
                existing_user_by_email = crud_user.get_by_email(db, email=user_in.email)
                if existing_user_by_email:
                    if existing_user_by_email.role != "ibu_hamil":
                        raise HTTPException(
                            status_code=status.HTTP_400_BAD_REQUEST,
                            detail=f"Email sudah terdaftar dengan role {existing_user_by_email.role}. Silakan gunakan email lain."
                        )
                    # Check if this user already has an ibu_hamil profile
                    existing_ibu_for_email_user = db.query(IbuHamil).filter(IbuHamil.user_id == existing_user_by_email.id).first()
                    if existing_ibu_for_email_user:
                        raise HTTPException(
                            status_code=status.HTTP_400_BAD_REQUEST,
                            detail="Email ini sudah terdaftar sebagai ibu hamil. Silakan login menggunakan akun yang ada."
                        )
            
            # Create new user
            try:
                user_obj = crud_user.create_user(db, user_in=user_in)
            except Exception as e:
                db.rollback()
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Gagal membuat akun user: {str(e)}"
                )

        # Validate: Check if NIK already registered
        existing_ibu = db.query(IbuHamil).filter(IbuHamil.nik == payload.ibu_hamil.nik).first()
        if existing_ibu:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="NIK sudah terdaftar di sistem. Setiap NIK hanya dapat digunakan sekali."
            )

        # Validate location format
        if payload.ibu_hamil.location:
            lon, lat = payload.ibu_hamil.location
            if not (-180.0 <= lon <= 180.0 and -90.0 <= lat <= 90.0):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Koordinat lokasi tidak valid. Longitude harus antara -180 hingga 180, dan Latitude antara -90 hingga 90."
                )

        # Create ibu hamil profile
        try:
            ibu_obj = crud_ibu_hamil.create_with_location(
                db,
                obj_in=payload.ibu_hamil,
                user_id=user_obj.id,
            )
        except ValueError as e:
            db.rollback()
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Data tidak valid: {str(e)}"
            )
        except Exception as e:
            db.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Gagal membuat profil ibu hamil: {str(e)}"
            )

        # Auto-assign to nearest Puskesmas if location is provided
        assigned_info = None
        if payload.ibu_hamil.location:
            try:
                assigned_info = _auto_assign_nearest(db, ibu_obj)
            except HTTPException as e:
                # Log the assignment failure but continue (keep unassigned)
                # User can be assigned manually later
                assigned_info = None
            except Exception as e:
                # Log unexpected error but don't fail the registration
                assigned_info = None

        # Generate access token
        try:
            token = create_access_token({"sub": str(user_obj.phone)})
        except Exception as e:
            # Log the actual error for debugging
            import logging
            logging.error(f"Failed to create access token: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Gagal membuat access token: {str(e)}"
            )

        # Build response
        try:
            response = {
                "ibu_hamil": IbuHamilResponse.from_orm(ibu_obj),
                "user": UserResponse.from_orm(user_obj),
                "access_token": token,
                "token_type": "bearer",
            }
            if assigned_info:
                _, puskesmas, distance = assigned_info
                response["assignment"] = {
                    "puskesmas": PuskesmasResponse.from_orm(puskesmas),
                    "distance_km": distance,
                }
            else:
                response["assignment"] = None
                response["message"] = "Registrasi berhasil. Penugasan Puskesmas akan dilakukan secara manual oleh admin."
            
            return response
            
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Gagal membentuk response: {str(e)}"
            )

    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        # Catch any unexpected errors
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Terjadi kesalahan tidak terduga saat memproses registrasi: {str(e)}"
        )


@router.post(
    "/login",
    response_model=IbuHamilLoginResponse,
    status_code=status.HTTP_200_OK,
    summary="Login ibu hamil",
    description="""
Login untuk ibu hamil menggunakan email dan password.

**Proses Login:**
1. Validasi format email dan password
2. Cek apakah email terdaftar di sistem
3. Verifikasi password
4. Pastikan akun aktif dan memiliki role ibu_hamil
5. Pastikan profil ibu hamil sudah lengkap
6. Generate access token

**Catatan:**
- Email harus terdaftar sebagai akun ibu hamil
- Akun harus dalam status aktif
- Profil ibu hamil harus sudah lengkap (sudah registrasi)
""",
    responses={
        200: {
            "description": "Login berhasil",
            "content": {
                "application/json": {
                    "example": {
                        "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                        "token_type": "bearer",
                        "user_id": 1,
                        "ibu_hamil_id": 1,
                        "nama_lengkap": "Siti Aminah",
                        "email": "siti.aminah@example.com"
                    }
                }
            }
        },
        401: {
            "description": "Email atau password salah",
            "content": {
                "application/json": {
                    "example": {"detail": "Email atau password salah"}
                }
            }
        },
        403: {
            "description": "Akun tidak aktif atau bukan akun ibu hamil",
            "content": {
                "application/json": {
                    "examples": {
                        "inactive": {
                            "summary": "Akun tidak aktif",
                            "value": {"detail": "Akun tidak aktif. Silakan hubungi administrator."}
                        },
                        "not_ibu_hamil": {
                            "summary": "Bukan akun ibu hamil",
                            "value": {"detail": "Akun ini bukan akun ibu hamil. Silakan gunakan login yang sesuai."}
                        }
                    }
                }
            }
        },
        404: {
            "description": "Email tidak terdaftar atau profil ibu hamil tidak ditemukan",
            "content": {
                "application/json": {
                    "examples": {
                        "email_not_found": {
                            "summary": "Email tidak terdaftar",
                            "value": {"detail": "Email tidak terdaftar di sistem"}
                        },
                        "profile_not_found": {
                            "summary": "Profil ibu hamil tidak ditemukan",
                            "value": {"detail": "Profil ibu hamil tidak ditemukan. Silakan lengkapi registrasi terlebih dahulu."}
                        }
                    }
                }
            }
        },
        422: {
            "description": "Validation error pada data input",
            "content": {
                "application/json": {
                    "example": {
                        "detail": [
                            {
                                "loc": ["body", "email"],
                                "msg": "value is not a valid email address",
                                "type": "value_error.email"
                            }
                        ]
                    }
                }
            }
        }
    }
)
async def login_ibu_hamil(
    payload: IbuHamilLoginRequest,
    db: Session = Depends(get_db),
) -> IbuHamilLoginResponse:
    """
    Login ibu hamil dengan email dan password.

    Args:
        payload: Data login (email, password)
        db: Database session

    Returns:
        IbuHamilLoginResponse: Access token dan informasi user

    Raises:
        EmailNotFoundException: Email tidak terdaftar
        InvalidCredentialsException: Password salah
        AccountInactiveException: Akun tidak aktif
        NotIbuHamilException: Akun bukan ibu hamil
        IbuHamilProfileNotFoundException: Profil ibu hamil tidak ditemukan
    """
    # 1. Cek apakah email terdaftar
    user = crud_user.get_by_email(db, email=payload.email)
    if not user:
        raise EmailNotFoundException()

    # 2. Verifikasi password
    authenticated_user = crud_user.authenticate_by_email(
        db, email=payload.email, password=payload.password
    )
    if not authenticated_user:
        raise InvalidCredentialsException()

    # 3. Cek apakah akun aktif
    if not authenticated_user.is_active:
        raise AccountInactiveException()

    # 4. Cek apakah role adalah ibu_hamil
    if authenticated_user.role != "ibu_hamil":
        raise NotIbuHamilException()

    # 5. Cari profil ibu hamil
    ibu_hamil = db.scalars(
        select(IbuHamil).where(IbuHamil.user_id == authenticated_user.id)
    ).first()
    if not ibu_hamil:
        raise IbuHamilProfileNotFoundException()

    # 6. Generate access token
    access_token = create_access_token({"sub": authenticated_user.phone})

    return IbuHamilLoginResponse(
        access_token=access_token,
        token_type="bearer",
        user_id=authenticated_user.id,
        ibu_hamil_id=ibu_hamil.id,
        nama_lengkap=ibu_hamil.nama_lengkap,
        email=authenticated_user.email,
    )


@router.get(
    "/me",
    response_model=IbuHamilResponse,
    status_code=status.HTTP_200_OK,
    summary="Profil ibu hamil saat ini",
    description="Mengambil profil ibu hamil milik user yang login (role ibu_hamil atau kerabat terkait).",
)
async def get_my_profile(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> IbuHamil:
    # Find IbuHamil linked to current user
    ibu = db.scalars(select(IbuHamil).where(IbuHamil.user_id == current_user.id)).first()
    if not ibu:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Profil Ibu Hamil tidak ditemukan",
        )

    # Kerabat can view if linked
    if current_user.role == "kerabat" and not _is_kerabat_linked(current_user, ibu, db):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to access this record",
        )

    return ibu


@router.get(
    "/{ibu_id}",
    response_model=IbuHamilResponse,
    status_code=status.HTTP_200_OK,
    summary="Detail ibu hamil",
    description="Dapat diakses oleh admin, perawat yang ditugaskan, admin puskesmas terkait, kerabat terkait, atau pemilik akun.",
)
async def get_ibu_hamil(
    ibu_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> IbuHamil:
    ibu = _get_ibu_or_404(db, ibu_id)
    _authorize_view(ibu, current_user, db)
    return ibu


@router.patch(
    "/{ibu_id}",
    response_model=IbuHamilResponse,
    status_code=status.HTTP_200_OK,
    summary="Update ibu hamil",
    description="Admin, pemilik akun, perawat terassign, atau admin puskesmas dapat memperbarui data. Jika lokasi diubah, akan mencoba auto-assign ulang.",
)
async def update_ibu_hamil(
    ibu_id: int,
    ibu_update: IbuHamilUpdate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> IbuHamil:
    ibu = _get_ibu_or_404(db, ibu_id)
    _authorize_update(ibu, current_user, db)

    updated = crud_ibu_hamil.update(db, db_obj=ibu, obj_in=ibu_update)

    # If location changed and no explicit puskesmas_id provided, try auto-assign
    if ibu_update.location and not ibu_update.puskesmas_id:
        try:
            _auto_assign_nearest(db, updated)
        except HTTPException:
            pass

    return updated


@router.get(
    "/unassigned",
    response_model=List[IbuHamilResponse],
    status_code=status.HTTP_200_OK,
    summary="Ibu hamil belum ter-assign",
    description="Admin, super admin (read-only), atau admin puskesmas yang dapat melihat daftar ibu hamil tanpa puskesmas.",
)
async def list_unassigned(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> List[IbuHamil]:
    # Super admin dapat melihat data (read-only)
    if current_user.role not in {"super_admin", "puskesmas"}:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized",
        )
    return crud_ibu_hamil.get_unassigned(db)


@router.post(
    "/{ibu_id}/assign-puskesmas",
    response_model=IbuHamilResponse,
    status_code=status.HTTP_200_OK,
    summary="Assign ibu hamil ke puskesmas",
    description="""
Menugaskan ibu hamil ke puskesmas tertentu secara manual.

**Siapa yang dapat mengakses:**
- Admin sistem
- Admin puskesmas (hanya untuk puskesmas yang dikelolanya)

**Catatan:**
- Puskesmas harus dalam status 'approved' dan aktif
- Endpoint ini HANYA untuk assign ke puskesmas, bukan ke perawat
- Untuk assign ke perawat, gunakan endpoint `/ibu-hamil/{ibu_id}/assign-perawat`
- Setelah assign ke puskesmas, ibu hamil belum memiliki perawat yang menangani

**Alur yang direkomendasikan:**
1. Assign ibu hamil ke puskesmas menggunakan endpoint ini
2. Kemudian assign ke perawat menggunakan endpoint `/ibu-hamil/{ibu_id}/assign-perawat`
""",
    responses={
        200: {
            "description": "Berhasil assign ibu hamil ke puskesmas",
            "content": {
                "application/json": {
                    "example": {
                        "id": 1,
                        "puskesmas_id": 2,
                        "perawat_id": None,
                        "nik": "3175091201850001",
                        "nama_lengkap": "Siti Aminah",
                        "is_active": True
                    }
                }
            }
        },
        403: {
            "description": "Tidak memiliki akses",
            "content": {
                "application/json": {
                    "examples": {
                        "not_authorized": {
                            "summary": "Bukan admin atau admin puskesmas",
                            "value": {"detail": "Not authorized"}
                        },
                        "wrong_puskesmas": {
                            "summary": "Admin puskesmas mencoba assign ke puskesmas lain",
                            "value": {"detail": "Not authorized to assign for this puskesmas"}
                        }
                    }
                }
            }
        },
        404: {
            "description": "Data tidak ditemukan",
            "content": {
                "application/json": {
                    "examples": {
                        "ibu_not_found": {
                            "summary": "Ibu hamil tidak ditemukan",
                            "value": {"detail": "Ibu Hamil not found"}
                        },
                        "puskesmas_not_found": {
                            "summary": "Puskesmas tidak ditemukan atau tidak aktif",
                            "value": {"detail": "Puskesmas tidak ditemukan atau belum aktif"}
                        }
                    }
                }
            }
        }
    }
)
async def assign_ibu_to_puskesmas(
    ibu_id: int,
    payload: AssignToPuskesmasRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> IbuHamil:
    """
    Assign ibu hamil ke puskesmas tertentu.

    Args:
        ibu_id: ID ibu hamil yang akan di-assign
        payload: Data berisi puskesmas_id tujuan
        current_user: User yang sedang login
        db: Database session

    Returns:
        IbuHamil: Data ibu hamil yang sudah di-update
    """
    # Super admin TIDAK dapat assign (hanya bisa approve/reject registrasi puskesmas)
    if current_user.role not in {"super_admin", "puskesmas"}:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized. Super admin hanya dapat approve/reject registrasi puskesmas.",
        )

    ibu = _get_ibu_or_404(db, ibu_id)

    pusk = crud_puskesmas.get(db, id=payload.puskesmas_id)
    if not pusk or pusk.registration_status != "approved" or not pusk.is_active:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Puskesmas tidak ditemukan atau belum aktif",
        )
    if current_user.role == "puskesmas" and pusk.admin_user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to assign for this puskesmas",
        )

    assigned = crud_ibu_hamil.assign_to_puskesmas(
        db,
        ibu_id=ibu.id,
        puskesmas_id=pusk.id,
        distance_km=0.0,
    )

    notification_in = NotificationCreate(
        user_id=ibu.user_id,
        title="Penugasan Puskesmas",
        message=f"Anda ditugaskan ke {pusk.name}.",
        notification_type="assignment",
        priority="normal",
        sent_via="in_app",
    )
    crud_notification.create(db, obj_in=notification_in)

    return assigned


@router.post(
    "/{ibu_id}/assign-perawat",
    response_model=IbuHamilResponse,
    status_code=status.HTTP_200_OK,
    summary="Assign ibu hamil ke perawat",
    description="""
Menugaskan ibu hamil ke perawat tertentu.

**Prasyarat:**
- Ibu hamil HARUS sudah ter-assign ke puskesmas terlebih dahulu
- Perawat HARUS terdaftar di puskesmas yang sama dengan ibu hamil
- Perawat harus memiliki kapasitas (current_patients < max_patients)

**Siapa yang dapat mengakses:**
- Admin sistem
- Admin puskesmas (hanya untuk ibu hamil di puskesmasnya)

**Catatan:**
- Gunakan endpoint `/ibu-hamil/{ibu_id}/assign-puskesmas` terlebih dahulu jika ibu hamil belum ter-assign ke puskesmas
- Endpoint ini akan menambah workload perawat secara otomatis

**Alur yang direkomendasikan:**
1. Pastikan ibu hamil sudah ter-assign ke puskesmas
2. Gunakan endpoint ini untuk assign ke perawat yang tersedia di puskesmas tersebut
""",
    responses={
        200: {
            "description": "Berhasil assign ibu hamil ke perawat",
            "content": {
                "application/json": {
                    "example": {
                        "id": 1,
                        "puskesmas_id": 2,
                        "perawat_id": 3,
                        "nik": "3175091201850001",
                        "nama_lengkap": "Siti Aminah",
                        "is_active": True
                    }
                }
            }
        },
        400: {
            "description": "Request tidak valid",
            "content": {
                "application/json": {
                    "examples": {
                        "no_puskesmas": {
                            "summary": "Ibu hamil belum ter-assign ke puskesmas",
                            "value": {"detail": "Ibu hamil belum ter-assign ke puskesmas. Silakan assign ke puskesmas terlebih dahulu."}
                        },
                        "perawat_full": {
                            "summary": "Perawat sudah mencapai kapasitas maksimal",
                            "value": {"detail": "Perawat sudah mencapai kapasitas maksimal pasien"}
                        }
                    }
                }
            }
        },
        403: {
            "description": "Tidak memiliki akses",
            "content": {
                "application/json": {
                    "examples": {
                        "not_authorized": {
                            "summary": "Bukan admin atau admin puskesmas",
                            "value": {"detail": "Not authorized"}
                        },
                        "wrong_puskesmas": {
                            "summary": "Admin puskesmas mencoba assign ibu hamil dari puskesmas lain",
                            "value": {"detail": "Not authorized to assign perawat for this ibu hamil"}
                        }
                    }
                }
            }
        },
        404: {
            "description": "Data tidak ditemukan",
            "content": {
                "application/json": {
                    "examples": {
                        "ibu_not_found": {
                            "summary": "Ibu hamil tidak ditemukan",
                            "value": {"detail": "Ibu Hamil not found"}
                        },
                        "perawat_not_found": {
                            "summary": "Perawat tidak ditemukan atau bukan dari puskesmas yang sama",
                            "value": {"detail": "Perawat tidak ditemukan atau tidak terdaftar di puskesmas ibu hamil ini"}
                        }
                    }
                }
            }
        }
    }
)
async def assign_ibu_to_perawat(
    ibu_id: int,
    payload: AssignToPerawatRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> IbuHamil:
    """
    Assign ibu hamil ke perawat yang terdaftar di puskesmas ibu hamil.

    Args:
        ibu_id: ID ibu hamil yang akan di-assign
        payload: Data berisi perawat_id tujuan
        current_user: User yang sedang login
        db: Database session

    Returns:
        IbuHamil: Data ibu hamil yang sudah di-update dengan perawat_id baru

    Raises:
        HTTPException 400: Ibu hamil belum ter-assign ke puskesmas atau perawat penuh
        HTTPException 403: Tidak memiliki akses
        HTTPException 404: Ibu hamil atau perawat tidak ditemukan
    """
    # Super admin TIDAK dapat assign (hanya bisa approve/reject registrasi puskesmas)
    if current_user.role not in {"super_admin", "puskesmas"}:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized. Super admin hanya dapat approve/reject registrasi puskesmas.",
        )

    ibu = _get_ibu_or_404(db, ibu_id)

    # Cek apakah ibu hamil sudah ter-assign ke puskesmas
    if not ibu.puskesmas_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Ibu hamil belum ter-assign ke puskesmas. Silakan assign ke puskesmas terlebih dahulu.",
        )

    # Jika admin puskesmas, pastikan ibu hamil berada di puskesmasnya
    if current_user.role == "puskesmas":
        pusk = crud_puskesmas.get(db, id=ibu.puskesmas_id)
        if not pusk or pusk.admin_user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to assign perawat for this ibu hamil",
            )

    # Cek perawat
    perawat = crud_perawat.get(db, id=payload.perawat_id)
    if not perawat or perawat.puskesmas_id != ibu.puskesmas_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Perawat tidak ditemukan atau tidak terdaftar di puskesmas ibu hamil ini",
        )

    # Cek kapasitas perawat
    if perawat.current_patients >= perawat.max_patients:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Perawat sudah mencapai kapasitas maksimal pasien",
        )

    # Assign ke perawat
    crud_ibu_hamil.assign_to_perawat(db, ibu_id=ibu.id, perawat_id=perawat.id)
    crud_perawat.update_workload(db, perawat_id=perawat.id, increment=1)

    # Refresh data ibu hamil
    db.refresh(ibu)

    # Kirim notifikasi
    notification_in = NotificationCreate(
        user_id=ibu.user_id,
        title="Penugasan Perawat",
        message=f"Anda akan ditangani oleh perawat {perawat.nama_lengkap}.",
        notification_type="assignment",
        priority="normal",
        sent_via="in_app",
    )
    crud_notification.create(db, obj_in=notification_in)

    return ibu


@router.post(
    "/{ibu_id}/auto-assign",
    response_model=AutoAssignResponse,
    status_code=status.HTTP_200_OK,
    summary="Auto-assign ke puskesmas terdekat",
    description="Admin atau ibu bersangkutan dapat melakukan penugasan otomatis ke puskesmas terdekat yang aktif dan tersedia.",
)
async def auto_assign(
    ibu_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> AutoAssignResponse:
    ibu = _get_ibu_or_404(db, ibu_id)

    if current_user.role != "ibu_hamil" and current_user.id != ibu.user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized",
        )
    if current_user.role == "ibu_hamil" and ibu.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized",
        )

    assigned_ibu, puskesmas, distance = _auto_assign_nearest(db, ibu)

    return AutoAssignResponse(
        ibu_hamil=IbuHamilResponse.from_orm(assigned_ibu),
        puskesmas=PuskesmasResponse.from_orm(puskesmas),
        distance_km=distance,
    )


@router.get(
    "/by-puskesmas/{puskesmas_id}",
    response_model=List[IbuHamilResponse],
    status_code=status.HTTP_200_OK,
    summary="Daftar ibu hamil per puskesmas",
    description="Admin, admin puskesmas tersebut, atau perawat di puskesmas tersebut dapat melihat daftar ibu hamil.",
)
async def list_by_puskesmas(
    puskesmas_id: int,
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> List[IbuHamil]:
    pusk = crud_puskesmas.get(db, id=puskesmas_id)
    if not pusk:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Puskesmas tidak ditemukan",
        )

    # Super admin dapat melihat data (read-only)
    if current_user.role not in {"super_admin", "puskesmas", "perawat"}:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized",
        )
    if current_user.role == "puskesmas" and pusk.admin_user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized",
        )
    if current_user.role == "perawat":
        perawat = crud_perawat.get(db, id=current_user.id)
        if not perawat or perawat.puskesmas_id != puskesmas_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized",
            )

    results = (
        db.execute(
            select(IbuHamil)
            .where(IbuHamil.puskesmas_id == puskesmas_id)
            .offset(skip)
            .limit(limit)
        )
        .scalars()
        .all()
    )
    return results


@router.get(
    "/by-perawat/{perawat_id}",
    response_model=List[IbuHamilResponse],
    status_code=status.HTTP_200_OK,
    summary="Daftar ibu hamil per perawat",
    description="Admin, perawat terkait, atau admin puskesmas yang menaungi perawat dapat melihat daftar ini.",
)
async def list_by_perawat(
    perawat_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> List[IbuHamil]:
    perawat = crud_perawat.get(db, id=perawat_id)
    if not perawat:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Perawat tidak ditemukan",
        )

    # Super admin dapat melihat data (read-only)
    if current_user.role not in {"super_admin", "perawat", "puskesmas"}:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized",
        )
    if current_user.role == "perawat" and current_user.id != perawat.user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized",
        )
    if current_user.role == "puskesmas":
        pusk = crud_puskesmas.get(db, id=perawat.puskesmas_id)
        if not pusk or pusk.admin_user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized",
            )

    return crud_ibu_hamil.get_by_perawat(db, perawat_id=perawat_id)


@router.post(
    "/{ibu_hamil_id}/profile-photo",
    response_model=IbuHamilResponse,
    status_code=status.HTTP_200_OK,
    summary="Upload ibu hamil profile photo",
)
async def upload_profile_photo(
    ibu_hamil_id: int,
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> IbuHamil:
    """Upload profile photo for an ibu hamil.
    
    Only the ibu hamil themselves (via their user account) or admin can upload their photo.
    Supported formats: JPG, PNG, GIF (max 5MB).
    """
    ibu_hamil = crud_ibu_hamil.get(db, ibu_hamil_id)
    if not ibu_hamil:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Ibu Hamil not found",
        )
    
    # Authorization: only the ibu hamil (via their user) or admin can upload their photo
    if current_user.role == "ibu_hamil" and ibu_hamil.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot upload photo for another ibu hamil",
        )
    
    try:
        # Save file and get path
        photo_path = await save_profile_photo(file, "ibu_hamil", ibu_hamil_id)
        
        # Update ibu hamil record
        ibu_hamil_update_data = {"profile_photo_url": photo_path}
        ibu_hamil = crud_ibu_hamil.update(db, db_obj=ibu_hamil, obj_in=ibu_hamil_update_data)
        
        return ibu_hamil
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to upload photo: {str(e)}",
        )


@router.get(
    "/{ibu_hamil_id}/profile-photo",
    status_code=status.HTTP_200_OK,
    summary="Get ibu hamil profile photo URL",
)
def get_profile_photo_url(
    ibu_hamil_id: int,
    db: Session = Depends(get_db),
) -> dict:
    """Get profile photo URL for an ibu hamil."""
    ibu_hamil = crud_ibu_hamil.get(db, ibu_hamil_id)
    if not ibu_hamil:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Ibu Hamil not found",
        )
    
    if not ibu_hamil.profile_photo_url:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Profile photo not found",
        )
    
    return {
        "ibu_hamil_id": ibu_hamil_id,
        "profile_photo_url": ibu_hamil.profile_photo_url,
    }


@router.delete(
    "/{ibu_hamil_id}/profile-photo",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete ibu hamil profile photo",
)
def delete_profile_photo(
    ibu_hamil_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> None:
    """Delete profile photo for an ibu hamil."""
    ibu_hamil = crud_ibu_hamil.get(db, ibu_hamil_id)
    if not ibu_hamil:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Ibu Hamil not found",
        )
    
    # Authorization: only the ibu hamil (via their user) or admin can delete their photo
    if current_user.role == "ibu_hamil" and ibu_hamil.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot delete photo for another ibu hamil",
        )
    
    # Clear photo URL
    ibu_hamil_update = {"profile_photo_url": None}
    crud_ibu_hamil.update(db, db_obj=ibu_hamil, obj_in=ibu_hamil_update)


__all__ = ["router"]
