"""Ibu Hamil (Pregnant Women) endpoints."""

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status, File, UploadFile
from pydantic import BaseModel, ConfigDict
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.api.deps import get_current_active_user, get_db, require_role
from app.core.security import create_access_token
from app.core.exceptions import (
    InvalidCredentialsException,
    EmailNotFoundException,
    AccountInactiveException,
    NotIbuHamilException,
    IbuHamilProfileNotFoundException,
    HealthRecordNotFoundException,
)
from app.crud import (
    crud_health_record,
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
    IbuHamilUpdateIdentitas,
    IbuHamilUpdateKehamilan,
    IbuHamilProfileResponse,
    MyPerawatResponse,
    MyPerawatInfo,
    MyPuskesmasInfo,
    UserUpdateProfile,
)
from app.schemas.health_record import HealthRecordResponse, LatestPerawatNotesResponse
from app.schemas.notification import NotificationCreate
from app.schemas.puskesmas import PuskesmasResponse
from app.schemas.user import UserCreate, UserResponse
from app.utils.file_handler import save_profile_photo

router = APIRouter(
    prefix="/ibu-hamil",
    tags=["Ibu Hamil (Pregnant Women)"],
)


class IbuHamilRegisterRequest(BaseModel):
    """
    Payload untuk registrasi ibu hamil baru.

    Request body terdiri dari 2 bagian:
    - user: Data akun user (email, phone, password, full_name)
    - ibu_hamil: Data profil ibu hamil (identitas, kehamilan, alamat, kontak darurat, riwayat kesehatan)

    **Catatan Penting:**
    - Field `role` pada user akan otomatis di-set ke "ibu_hamil" meskipun diisi nilai lain
    - Field `risk_level` TIDAK boleh diisi saat registrasi (akan diabaikan). Risk level ditentukan oleh perawat setelah assessment
    - Field `profile_photo_url` akan diabaikan saat registrasi
    """

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


def _is_perawat_in_same_puskesmas(current_user: User, ibu: IbuHamil, db: Session) -> bool:
    """Check if perawat is in the same puskesmas as ibu hamil."""
    if current_user.role != "perawat":
        return False
    if not ibu.puskesmas_id:
        return False
    perawat = crud_perawat.get_by_user_id(db, user_id=current_user.id)
    if not perawat:
        return False
    return perawat.puskesmas_id == ibu.puskesmas_id


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
    if _is_perawat_in_same_puskesmas(current_user, ibu, db):
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
    if _is_perawat_in_same_puskesmas(current_user, ibu, db):
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
    summary="Registrasi ibu hamil baru",
    description="""
Endpoint untuk registrasi ibu hamil baru ke dalam sistem WellMom.

## Flow Registrasi
1. Validasi semua data input (NIK, phone, email, lokasi, dll)
2. Membuat akun user dengan role `ibu_hamil`
3. Membuat profil ibu hamil dengan data lengkap
4. Generate access token untuk login otomatis

## Field yang Wajib Diisi

### Data User (`user`)
| Field | Tipe | Keterangan |
|-------|------|------------|
| phone | string | Nomor telepon (8-15 digit, boleh dengan awalan +) |
| password | string | Password minimal 6 karakter |
| full_name | string | Nama lengkap |

### Data Ibu Hamil (`ibu_hamil`)
| Field | Tipe | Keterangan |
|-------|------|------------|
| nama_lengkap | string | Nama lengkap ibu hamil |
| nik | string | NIK 16 digit (unik, tidak boleh duplikat) |
| date_of_birth | date | Tanggal lahir (format: YYYY-MM-DD) |
| address | string | Alamat lengkap |
| location | array | Koordinat [longitude, latitude] |
| emergency_contact_name | string | Nama kontak darurat |
| emergency_contact_phone | string | Nomor telepon kontak darurat |

## Field Opsional

### Data User (`user`)
- `email`: Email (opsional tapi disarankan untuk login via email)

### Data Ibu Hamil (`ibu_hamil`)
- `provinsi`, `kota_kabupaten`, `kelurahan`, `kecamatan`: Alamat administratif
- `last_menstrual_period`: HPHT (Hari Pertama Haid Terakhir)
- `estimated_due_date`: HPL (Hari Perkiraan Lahir)
- `usia_kehamilan`: Usia kehamilan dalam minggu
- `kehamilan_ke`: Kehamilan ke berapa (default: 1)
- `jumlah_anak`: Jumlah anak yang sudah dilahirkan (default: 0)
- `miscarriage_number`: Riwayat keguguran (default: 0)
- `jarak_kehamilan_terakhir`: Jarak dengan kehamilan sebelumnya
- `previous_pregnancy_complications`: Komplikasi kehamilan sebelumnya
- `pernah_caesar`: Pernah persalinan caesar (default: false)
- `pernah_perdarahan_saat_hamil`: Pernah perdarahan saat hamil (default: false)
- `riwayat_kesehatan_ibu`: Object berisi riwayat kesehatan (darah_tinggi, diabetes, anemia, dll)
- `age`: Usia ibu hamil
- `blood_type`: Golongan darah (A+, A-, B+, B-, AB+, AB-, O+, O-)
- `emergency_contact_relation`: Hubungan dengan kontak darurat
- `healthcare_preference`: Preferensi layanan kesehatan
- `whatsapp_consent`: Persetujuan menerima notifikasi via WhatsApp (default: true)
- `data_sharing_consent`: Persetujuan berbagi data (default: false)

## Field yang TIDAK Boleh Diisi Saat Registrasi
- `risk_level`: Akan diabaikan. Risk level ditentukan oleh perawat setelah assessment
- `profile_photo_url`: Akan diabaikan. Upload foto profil menggunakan endpoint terpisah

## Langkah Selanjutnya (di Frontend)
1. Setelah registrasi berhasil, simpan `access_token` untuk autentikasi
2. Panggil endpoint `GET /puskesmas/nearest?latitude={lat}&longitude={lon}` untuk mendapatkan list puskesmas terdekat
3. Tampilkan list puskesmas ke user untuk dipilih
4. Panggil endpoint `POST /ibu-hamil/{ibu_id}/assign-puskesmas` dengan puskesmas_id yang dipilih
""",
    responses={
        201: {
            "description": "Registrasi berhasil. User dan profil ibu hamil telah dibuat. Access token dikembalikan untuk login otomatis.",
            "content": {
                "application/json": {
                    "example": {
                        "ibu_hamil": {
                            "id": 1,
                            "user_id": 15,
                            "puskesmas_id": None,
                            "perawat_id": None,
                            "nama_lengkap": "Siti Aminah",
                            "nik": "3175091201850001",
                            "date_of_birth": "1985-12-12",
                            "age": 39,
                            "blood_type": "O+",
                            "last_menstrual_period": "2024-12-01",
                            "estimated_due_date": "2025-09-08",
                            "usia_kehamilan": 8,
                            "kehamilan_ke": 2,
                            "jumlah_anak": 1,
                            "address": "Jl. Mawar No. 10, RT 02 RW 05, Kelurahan Sungai Penuh",
                            "provinsi": "Jambi",
                            "kota_kabupaten": "Kerinci",
                            "location": [101.3912, -2.0645],
                            "emergency_contact_name": "Budi (Suami)",
                            "emergency_contact_phone": "+6281298765432",
                            "risk_level": None,
                            "is_active": True,
                            "created_at": "2026-01-22T10:00:00Z",
                            "updated_at": "2026-01-22T10:00:00Z"
                        },
                        "user": {
                            "id": 15,
                            "email": "siti.aminah@example.com",
                            "phone": "+6281234567890",
                            "full_name": "Siti Aminah",
                            "role": "ibu_hamil",
                            "is_active": True,
                            "is_verified": False,
                            "created_at": "2026-01-22T10:00:00Z",
                            "updated_at": "2026-01-22T10:00:00Z"
                        },
                        "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIrNjI4MTIzNDU2Nzg5MCIsImV4cCI6MTcwNjAwMDAwMH0.xxx",
                        "token_type": "bearer",
                        "message": "Registrasi berhasil. Silakan pilih puskesmas terdekat untuk melanjutkan."
                    }
                }
            }
        },
        400: {
            "description": "Data tidak valid atau sudah terdaftar di sistem",
            "content": {
                "application/json": {
                    "examples": {
                        "nik_exists": {
                            "summary": "NIK sudah terdaftar",
                            "value": {"detail": "NIK sudah terdaftar di sistem. Setiap NIK hanya dapat digunakan sekali."}
                        },
                        "phone_different_role": {
                            "summary": "Nomor telepon terdaftar dengan akun lain",
                            "value": {"detail": "Nomor telepon sudah terdaftar dengan akun lain. Silakan gunakan nomor lain atau login dengan akun yang ada."}
                        },
                        "phone_already_ibu_hamil": {
                            "summary": "Nomor telepon sudah terdaftar sebagai ibu hamil",
                            "value": {"detail": "Nomor telepon ini sudah terdaftar sebagai ibu hamil. Silakan login menggunakan akun yang ada."}
                        },
                        "email_different_role": {
                            "summary": "Email terdaftar dengan akun lain",
                            "value": {"detail": "Email sudah terdaftar dengan akun lain. Silakan gunakan email lain."}
                        },
                        "email_already_ibu_hamil": {
                            "summary": "Email sudah terdaftar sebagai ibu hamil",
                            "value": {"detail": "Email ini sudah terdaftar sebagai ibu hamil. Silakan login menggunakan akun yang ada."}
                        },
                        "invalid_location": {
                            "summary": "Koordinat lokasi tidak valid",
                            "value": {"detail": "Koordinat lokasi tidak valid. Longitude harus antara -180 hingga 180, dan Latitude antara -90 hingga 90."}
                        },
                        "invalid_blood_type": {
                            "summary": "Golongan darah tidak valid",
                            "value": {"detail": "Blood type must be one of ['A+', 'A-', 'AB+', 'AB-', 'B+', 'B-', 'O+', 'O-']"}
                        },
                        "invalid_emergency_phone": {
                            "summary": "Nomor kontak darurat tidak valid",
                            "value": {"detail": "Emergency contact phone must be 8-15 digits, optional leading '+'"}
                        },
                        "invalid_phone": {
                            "summary": "Nomor telepon tidak valid",
                            "value": {"detail": "Phone must be 8-15 digits, optional leading '+'"}
                        }
                    }
                }
            }
        },
        422: {
            "description": "Validation error - Data input tidak sesuai format yang diharapkan",
            "content": {
                "application/json": {
                    "examples": {
                        "invalid_nik": {
                            "summary": "NIK tidak valid (bukan 16 digit)",
                            "value": {
                                "detail": [
                                    {
                                        "loc": ["body", "ibu_hamil", "nik"],
                                        "msg": "NIK must be exactly 16 digits",
                                        "type": "value_error"
                                    }
                                ]
                            }
                        },
                        "missing_field": {
                            "summary": "Field wajib tidak diisi",
                            "value": {
                                "detail": [
                                    {
                                        "loc": ["body", "ibu_hamil", "nama_lengkap"],
                                        "msg": "Field required",
                                        "type": "missing"
                                    }
                                ]
                            }
                        },
                        "invalid_date": {
                            "summary": "Format tanggal tidak valid",
                            "value": {
                                "detail": [
                                    {
                                        "loc": ["body", "ibu_hamil", "date_of_birth"],
                                        "msg": "Input should be a valid date",
                                        "type": "date_parsing"
                                    }
                                ]
                            }
                        },
                        "invalid_location_format": {
                            "summary": "Format lokasi tidak valid",
                            "value": {
                                "detail": [
                                    {
                                        "loc": ["body", "ibu_hamil", "location"],
                                        "msg": "Location must be a (longitude, latitude) tuple",
                                        "type": "value_error"
                                    }
                                ]
                            }
                        }
                    }
                }
            }
        },
        500: {
            "description": "Kesalahan server internal",
            "content": {
                "application/json": {
                    "examples": {
                        "create_user_failed": {
                            "summary": "Gagal membuat akun user",
                            "value": {"detail": "Gagal membuat akun user: [error message]"}
                        },
                        "create_profile_failed": {
                            "summary": "Gagal membuat profil ibu hamil",
                            "value": {"detail": "Gagal membuat profil ibu hamil: [error message]"}
                        },
                        "unexpected_error": {
                            "summary": "Error tidak terduga",
                            "value": {"detail": "Terjadi kesalahan tidak terduga saat memproses registrasi: [error message]"}
                        }
                    }
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
    7. Generate access token
    
    Setelah registrasi, ibu hamil perlu:
    - Memanggil GET /puskesmas/nearest untuk mendapatkan list puskesmas terdekat
    - Memilih puskesmas dan memanggil POST /puskesmas/{id}/ibu-hamil/{ibu_id}/assign
    
    Returns:
        dict: User info, ibu hamil profile, access token, dan message
    
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
                    detail="Nomor telepon sudah terdaftar dengan akun lain. Silakan gunakan nomor lain atau login dengan akun yang ada."
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
                            detail="Email sudah terdaftar dengan akun lain. Silakan gunakan email lain."
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

        # Generate access token
        try:
            token = create_access_token({"sub": str(user_obj.phone)})
        except Exception as e:
            import logging
            logging.error(f"Failed to create access token: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Gagal membuat access token: {str(e)}"
            )

        # Build response
        try:
            return {
                "ibu_hamil": IbuHamilResponse.model_validate(ibu_obj),
                "user": UserResponse.model_validate(user_obj),
                "access_token": token,
                "token_type": "bearer",
                "message": "Registrasi berhasil. Silakan pilih puskesmas terdekat untuk melanjutkan.",
            }
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
    description="""
Mengambil profil ibu hamil milik user yang sedang login.

**Akses:**
- Ibu hamil: Dapat melihat profil dirinya sendiri
- Kerabat: Dapat melihat profil ibu hamil yang terhubung dengannya

**Data yang dikembalikan:**
- **Identitas Pribadi:** nama_lengkap, NIK, date_of_birth, age, blood_type, profile_photo_url
- **Data Kehamilan:**
  - last_menstrual_period (HPHT - Hari Pertama Haid Terakhir)
  - estimated_due_date (HPL - Hari Perkiraan Lahir)
  - usia_kehamilan (dalam minggu)
  - kehamilan_ke, jumlah_anak, miscarriage_number
  - jarak_kehamilan_terakhir
  - previous_pregnancy_complications (komplikasi kehamilan sebelumnya)
  - pernah_caesar (riwayat operasi caesar)
  - pernah_perdarahan_saat_hamil (riwayat perdarahan saat hamil)
- **Alamat & Lokasi:** address, provinsi, kota_kabupaten, kelurahan, kecamatan, location
- **Kontak Darurat:** emergency_contact_name, emergency_contact_phone, emergency_contact_relation
- **Riwayat Kesehatan Ibu:**
  - darah_tinggi (hipertensi)
  - diabetes
  - anemia
  - penyakit_jantung
  - asma
  - penyakit_ginjal
  - tbc_malaria
- **Risk Assessment:** risk_level, risk_level_set_by, risk_level_set_by_name, risk_level_set_at
- **Assignment:** puskesmas_id, perawat_id, assignment_date, assignment_distance_km, assignment_method
- **Status:** is_active, created_at, updated_at
""",
    responses={
        200: {
            "description": "Profil ibu hamil berhasil diambil",
            "content": {
                "application/json": {
                    "example": {
                        "id": 1,
                        "user_id": 15,
                        "puskesmas_id": 2,
                        "perawat_id": 3,
                        "assigned_by_user_id": 10,
                        "nama_lengkap": "Siti Aminah",
                        "nik": "3175091201850001",
                        "date_of_birth": "1985-12-12",
                        "age": 39,
                        "blood_type": "O+",
                        "profile_photo_url": "/uploads/photos/profiles/ibu_hamil/ibu_hamil_1_20250118_123456.jpg",
                        "last_menstrual_period": "2024-12-01",
                        "estimated_due_date": "2025-09-08",
                        "usia_kehamilan": 8,
                        "kehamilan_ke": 2,
                        "jumlah_anak": 1,
                        "miscarriage_number": 0,
                        "jarak_kehamilan_terakhir": "2 tahun",
                        "previous_pregnancy_complications": "Tidak ada",
                        "pernah_caesar": False,
                        "pernah_perdarahan_saat_hamil": False,
                        "address": "Jl. Mawar No. 10, RT 02 RW 05",
                        "provinsi": "Jambi",
                        "kota_kabupaten": "Kerinci",
                        "kelurahan": "Sungai Penuh",
                        "kecamatan": "Pesisir Bukit",
                        "location": [101.3912, -2.0645],
                        "emergency_contact_name": "Budi (Suami)",
                        "emergency_contact_phone": "+6281234567890",
                        "emergency_contact_relation": "Suami",
                        "darah_tinggi": False,
                        "diabetes": False,
                        "anemia": True,
                        "penyakit_jantung": False,
                        "asma": False,
                        "penyakit_ginjal": False,
                        "tbc_malaria": False,
                        "risk_level": "sedang",
                        "risk_level_set_by": 3,
                        "risk_level_set_by_name": "Bidan Rina Wijaya",
                        "risk_level_set_at": "2026-01-20T10:30:00Z",
                        "assignment_date": "2026-01-15T08:00:00Z",
                        "assignment_distance_km": 2.5,
                        "assignment_method": "manual",
                        "healthcare_preference": "puskesmas",
                        "whatsapp_consent": True,
                        "data_sharing_consent": False,
                        "is_active": True,
                        "created_at": "2026-01-10T10:00:00Z",
                        "updated_at": "2026-01-20T10:30:00Z"
                    }
                }
            }
        },
        403: {
            "description": "Tidak memiliki akses",
            "content": {
                "application/json": {
                    "example": {"detail": "Not authorized to access this record"}
                }
            }
        },
        404: {
            "description": "Profil tidak ditemukan",
            "content": {
                "application/json": {
                    "example": {"detail": "Profil Ibu Hamil tidak ditemukan"}
                }
            }
        }
    }
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
    "/me/profile",
    response_model=IbuHamilProfileResponse,
    status_code=status.HTTP_200_OK,
    summary="Profil lengkap ibu hamil (untuk profile setting)",
    description="""
Mengambil profil lengkap ibu hamil yang sedang login, termasuk data user dan data ibu hamil.
Digunakan untuk halaman profile setting.

**Akses:**
- Hanya dapat diakses oleh ibu hamil yang sedang login (role: ibu_hamil)
- Data yang dikembalikan mencakup semua informasi user dan profil ibu hamil
""",
    responses={
        200: {
            "description": "Profil lengkap berhasil diambil",
            "content": {
                "application/json": {
                    "example": {
                        "user": {
                            "id": 15,
                            "email": "siti.aminah@example.com",
                            "phone": "+6281234567890",
                            "full_name": "Siti Aminah",
                            "role": "ibu_hamil",
                            "is_active": True,
                            "is_verified": False
                        },
                        "ibu_hamil": {
                            "id": 18,
                            "user_id": 15,
                            "nama_lengkap": "Siti Aminah",
                            "nik": "3175091201850001",
                            "date_of_birth": "1985-12-12",
                            "location": [101.3912, -2.0645],
                            "address": "Jl. Mawar No. 10",
                            "is_active": True
                        }
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
async def get_my_profile_full(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> IbuHamilProfileResponse:
    """
    Mengambil profil lengkap ibu hamil yang sedang login (user + ibu hamil).
    
    Args:
        current_user: User yang sedang login (harus role ibu_hamil)
        db: Database session
        
    Returns:
        IbuHamilProfileResponse: Gabungan data user dan ibu hamil
        
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
    
    return IbuHamilProfileResponse(
        user=UserResponse.model_validate(current_user),
        ibu_hamil=IbuHamilResponse.model_validate(ibu),
    )


@router.get(
    "/me/perawat",
    response_model=MyPerawatResponse,
    status_code=status.HTTP_200_OK,
    summary="Ambil data perawat pendamping",
    description="""
Mengambil data perawat pendamping yang ditugaskan untuk ibu hamil yang sedang login.

Endpoint ini digunakan di homepage ibu hamil untuk menampilkan informasi perawat pendampingnya.

## Akses
- **Role yang diizinkan:** `ibu_hamil`
- Hanya dapat mengakses data perawat yang ditugaskan untuk diri sendiri

## Response Fields

| Field | Tipe | Keterangan |
|-------|------|------------|
| has_perawat | boolean | `true` jika sudah mendapat perawat, `false` jika belum |
| perawat | object/null | Data perawat (null jika belum mendapat perawat) |
| puskesmas | object/null | Data puskesmas (null jika belum terdaftar di puskesmas) |
| message | string | Pesan informatif tentang status penugasan |

### Perawat Info (jika ada)
| Field | Tipe | Keterangan |
|-------|------|------------|
| id | integer | ID perawat |
| nama_lengkap | string | Nama lengkap perawat |
| email | string | Email perawat |
| nomor_hp | string | Nomor HP perawat untuk dihubungi |
| profile_photo_url | string/null | URL foto profil perawat |

### Puskesmas Info (jika ada)
| Field | Tipe | Keterangan |
|-------|------|------------|
| id | integer | ID puskesmas |
| name | string | Nama puskesmas |
| address | string/null | Alamat puskesmas |
| phone | string/null | Nomor telepon puskesmas |

## Kondisi Response

1. **Sudah mendapat perawat**: `has_perawat=true`, data perawat dan puskesmas tersedia
2. **Belum mendapat perawat tapi sudah terdaftar di puskesmas**: `has_perawat=false`, perawat=null, puskesmas tersedia
3. **Belum terdaftar di puskesmas manapun**: `has_perawat=false`, perawat=null, puskesmas=null

## Error Handling
- **401**: Token tidak valid atau expired
- **403**: User bukan ibu hamil
- **404**: Profil ibu hamil tidak ditemukan
""",
    responses={
        200: {
            "description": "Data perawat berhasil diambil",
            "content": {
                "application/json": {
                    "examples": {
                        "with_perawat": {
                            "summary": "Sudah mendapat perawat",
                            "value": {
                                "has_perawat": True,
                                "perawat": {
                                    "id": 1,
                                    "nama_lengkap": "Siti Nurhaliza",
                                    "email": "siti.nurhaliza@puskesmas.go.id",
                                    "nomor_hp": "+6281234567890",
                                    "profile_photo_url": "/uploads/photos/profiles/perawat/perawat_1.jpg"
                                },
                                "puskesmas": {
                                    "id": 1,
                                    "name": "Puskesmas Hamparan Pugu",
                                    "address": "Jl. Raya No. 1",
                                    "phone": "021-1234567"
                                },
                                "message": "Anda sudah mendapatkan perawat pendamping"
                            }
                        },
                        "no_perawat": {
                            "summary": "Belum mendapat perawat",
                            "value": {
                                "has_perawat": False,
                                "perawat": None,
                                "puskesmas": {
                                    "id": 1,
                                    "name": "Puskesmas Hamparan Pugu",
                                    "address": "Jl. Raya No. 1",
                                    "phone": "021-1234567"
                                },
                                "message": "Anda belum mendapatkan perawat pendamping. Silakan tunggu penugasan dari puskesmas."
                            }
                        },
                        "no_puskesmas": {
                            "summary": "Belum terdaftar di puskesmas",
                            "value": {
                                "has_perawat": False,
                                "perawat": None,
                                "puskesmas": None,
                                "message": "Anda belum terdaftar di puskesmas manapun. Silakan hubungi puskesmas terdekat."
                            }
                        }
                    }
                }
            }
        },
        403: {
            "description": "Bukan role ibu_hamil",
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
async def get_my_perawat(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> MyPerawatResponse:
    """
    Mengambil data perawat pendamping untuk ibu hamil yang sedang login.

    Returns:
        MyPerawatResponse: Data perawat dan puskesmas (jika ada)

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

    # Get puskesmas info if assigned
    puskesmas_info = None
    if ibu.puskesmas_id:
        puskesmas = crud_puskesmas.get(db, id=ibu.puskesmas_id)
        if puskesmas:
            puskesmas_info = MyPuskesmasInfo(
                id=puskesmas.id,
                name=puskesmas.name,
                address=puskesmas.address,
                phone=puskesmas.phone,
            )

    # Get perawat info if assigned
    perawat_info = None
    if ibu.perawat_id:
        perawat = crud_perawat.get(db, id=ibu.perawat_id)
        if perawat:
            perawat_info = MyPerawatInfo(
                id=perawat.id,
                nama_lengkap=perawat.nama_lengkap,
                email=perawat.email,
                nomor_hp=perawat.nomor_hp,
                profile_photo_url=perawat.profile_photo_url,
            )

    # Determine message based on status
    if perawat_info:
        message = "Anda sudah mendapatkan perawat pendamping"
    elif puskesmas_info:
        message = "Anda belum mendapatkan perawat pendamping. Silakan tunggu penugasan dari puskesmas."
    else:
        message = "Anda belum terdaftar di puskesmas manapun. Silakan hubungi puskesmas terdekat."

    return MyPerawatResponse(
        has_perawat=perawat_info is not None,
        perawat=perawat_info,
        puskesmas=puskesmas_info,
        message=message,
    )


@router.get(
    "/me/latest-health-record",
    response_model=HealthRecordResponse,
    status_code=status.HTTP_200_OK,
    summary="Ambil health record terbaru ibu hamil",
    description="""
Mengambil health record terbaru milik ibu hamil yang sedang login.

Endpoint ini digunakan untuk menampilkan ringkasan kondisi kesehatan terakhir ibu hamil di halaman dashboard atau home.

## Akses
- **Role yang diizinkan:** `ibu_hamil`
- Hanya dapat mengakses data milik sendiri

## Response Fields

### Data Pemeriksaan
| Field | Tipe | Keterangan |
|-------|------|------------|
| id | integer | ID unik health record |
| ibu_hamil_id | integer | ID ibu hamil |
| perawat_id | integer | ID perawat yang memeriksa (null jika mandiri) |
| checkup_date | date | Tanggal pemeriksaan (YYYY-MM-DD) |
| checked_by | string | Siapa yang memeriksa: `perawat` atau `mandiri` |

### Usia Kehamilan
| Field | Tipe | Keterangan |
|-------|------|------------|
| gestational_age_weeks | integer | Usia kehamilan dalam minggu |
| gestational_age_days | integer | Usia kehamilan dalam hari (sisa) |

### Tanda Vital (Wajib)
| Field | Tipe | Keterangan |
|-------|------|------------|
| blood_pressure_systolic | integer | Tekanan darah sistolik (mmHg) |
| blood_pressure_diastolic | integer | Tekanan darah diastolik (mmHg) |
| heart_rate | integer | Detak jantung (bpm) |
| body_temperature | float | Suhu tubuh (°C) |
| weight | float | Berat badan (kg) |
| complaints | string | Keluhan yang dirasakan |

### Data Lab/Puskesmas (Opsional)
| Field | Tipe | Keterangan |
|-------|------|------------|
| hemoglobin | float | Kadar hemoglobin (g/dL) |
| blood_glucose | float | Gula darah (mg/dL) |
| protein_urin | string | Protein urin (negatif, +1, +2, +3, +4) |
| upper_arm_circumference | float | Lingkar lengan atas/LILA (cm) |
| fundal_height | float | Tinggi fundus uteri (cm) |
| fetal_heart_rate | integer | Detak jantung janin (bpm) |
| notes | string | Catatan tambahan dari perawat |

### Timestamp
| Field | Tipe | Keterangan |
|-------|------|------------|
| created_at | datetime | Waktu record dibuat |
| updated_at | datetime | Waktu record terakhir diupdate |

## Error Handling
- **401**: Token tidak valid atau expired
- **403**: User bukan ibu hamil
- **404**: Profil ibu hamil tidak ditemukan atau belum ada health record sama sekali
""",
    responses={
        200: {
            "description": "Health record terbaru berhasil diambil",
            "content": {
                "application/json": {
                    "example": {
                        "id": 1,
                        "ibu_hamil_id": 1,
                        "perawat_id": 1,
                        "checkup_date": "2025-02-15",
                        "checked_by": "perawat",
                        "gestational_age_weeks": 28,
                        "gestational_age_days": 3,
                        "blood_pressure_systolic": 120,
                        "blood_pressure_diastolic": 80,
                        "heart_rate": 72,
                        "body_temperature": 36.8,
                        "weight": 65.5,
                        "complaints": "Tidak ada keluhan",
                        "hemoglobin": 12.5,
                        "blood_glucose": 95.0,
                        "protein_urin": "negatif",
                        "upper_arm_circumference": 25.0,
                        "fundal_height": 28.0,
                        "fetal_heart_rate": 140,
                        "notes": "Ibu dalam kondisi sehat",
                        "created_at": "2025-02-15T10:00:00Z",
                        "updated_at": "2025-02-15T10:00:00Z",
                    }
                }
            },
        },
        401: {
            "description": "Token tidak valid atau expired",
            "content": {
                "application/json": {
                    "example": {"detail": "Could not validate credentials"}
                }
            },
        },
        403: {
            "description": "Bukan role ibu_hamil",
            "content": {
                "application/json": {
                    "example": {"detail": "Hanya ibu hamil yang dapat mengakses endpoint ini"}
                }
            },
        },
        404: {
            "description": "Profil tidak ditemukan atau belum ada health record",
            "content": {
                "application/json": {
                    "examples": {
                        "profile_not_found": {
                            "summary": "Profil ibu hamil tidak ditemukan",
                            "value": {"detail": "Profil Ibu Hamil tidak ditemukan"}
                        },
                        "no_health_record": {
                            "summary": "Belum ada health record",
                            "value": {"detail": "Belum ada data health record. Silakan lakukan pemeriksaan kesehatan terlebih dahulu."}
                        }
                    }
                }
            },
        },
    },
)
async def get_my_latest_health_record(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> HealthRecordResponse:
    """
    Mengambil health record terbaru milik ibu hamil yang sedang login.

    Args:
        current_user: User yang sedang login (harus role ibu_hamil)
        db: Database session

    Returns:
        HealthRecordResponse: Data health record terbaru

    Raises:
        HTTPException 403: Jika bukan role ibu_hamil
        HTTPException 404: Jika profil ibu hamil tidak ditemukan
        HealthRecordNotFoundException: Jika belum ada health record sama sekali
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

    # Get latest health record
    latest_record = crud_health_record.get_latest(db, ibu_hamil_id=ibu.id)
    if not latest_record:
        raise HealthRecordNotFoundException()

    return HealthRecordResponse.model_validate(latest_record)


@router.get(
    "/me/latest-perawat-notes",
    response_model=LatestPerawatNotesResponse,
    status_code=status.HTTP_200_OK,
    summary="Ambil catatan perawat terakhir untuk ibu hamil",
    description="""
Mengambil catatan (notes) terakhir dari perawat untuk ibu hamil yang sedang login.

## Konteks
- Catatan dari perawat hanya didapatkan saat ibu hamil melakukan pemeriksaan di puskesmas
- Banyak health record yang tidak memiliki notes karena ibu hamil melakukan pemeriksaan mandiri di rumah
- Endpoint ini mencari health record terakhir yang:
  - Dilakukan oleh perawat (`checked_by = 'perawat'`)
  - Memiliki catatan (`notes` tidak kosong)

## Akses
- **Role yang diizinkan:** `ibu_hamil`
- Hanya dapat mengakses data milik sendiri

## Response Fields
| Field | Tipe | Keterangan |
|-------|------|------------|
| has_notes | boolean | Apakah ada catatan dari perawat |
| notes | string | Isi catatan dari perawat (null jika belum ada) |
| checkup_date | date | Tanggal pemeriksaan saat catatan dibuat (null jika belum ada) |
| perawat_id | integer | ID perawat yang memberikan catatan (null jika belum ada) |
| health_record_id | integer | ID health record yang memiliki catatan (null jika belum ada) |
| message | string | Pesan informatif untuk ditampilkan ke user |

## Kemungkinan Response
1. **Ada catatan dari perawat:**
   - `has_notes: true`
   - Semua field terisi dengan data dari health record terakhir yang memiliki notes

2. **Belum ada catatan dari perawat:**
   - `has_notes: false`
   - Field notes, checkup_date, perawat_id, health_record_id bernilai null
   - message berisi informasi untuk kunjungi puskesmas
""",
    responses={
        200: {
            "description": "Catatan perawat berhasil diambil",
            "content": {
                "application/json": {
                    "examples": {
                        "has_notes": {
                            "summary": "Ada catatan dari perawat",
                            "value": {
                                "has_notes": True,
                                "notes": "Ibu dalam kondisi sehat. Tekanan darah normal. Lanjutkan pola makan sehat dan istirahat cukup.",
                                "checkup_date": "2026-01-20",
                                "perawat_id": 3,
                                "health_record_id": 15,
                                "message": "Catatan perawat terakhir ditemukan"
                            }
                        },
                        "no_notes": {
                            "summary": "Belum ada catatan dari perawat",
                            "value": {
                                "has_notes": False,
                                "notes": None,
                                "checkup_date": None,
                                "perawat_id": None,
                                "health_record_id": None,
                                "message": "Belum ada catatan dari perawat. Silakan kunjungi puskesmas untuk pemeriksaan."
                            }
                        }
                    }
                }
            },
        },
        401: {
            "description": "Token tidak valid atau expired",
            "content": {
                "application/json": {
                    "example": {"detail": "Could not validate credentials"}
                }
            },
        },
        403: {
            "description": "Bukan role ibu_hamil",
            "content": {
                "application/json": {
                    "example": {"detail": "Hanya ibu hamil yang dapat mengakses endpoint ini"}
                }
            },
        },
        404: {
            "description": "Profil ibu hamil tidak ditemukan",
            "content": {
                "application/json": {
                    "example": {"detail": "Profil Ibu Hamil tidak ditemukan"}
                }
            },
        },
    },
)
async def get_my_latest_perawat_notes(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> LatestPerawatNotesResponse:
    """
    Mengambil catatan perawat terakhir untuk ibu hamil yang sedang login.

    Endpoint ini berguna untuk menampilkan catatan/rekomendasi terakhir dari perawat
    di halaman dashboard atau profil ibu hamil.

    Args:
        current_user: User yang sedang login (harus role ibu_hamil)
        db: Database session

    Returns:
        LatestPerawatNotesResponse: Data catatan perawat terakhir atau informasi bahwa belum ada catatan
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

    # Get latest health record with notes from perawat
    record_with_notes = crud_health_record.get_latest_perawat_notes(db, ibu_hamil_id=ibu.id)

    if record_with_notes:
        return LatestPerawatNotesResponse(
            has_notes=True,
            notes=record_with_notes.notes,
            checkup_date=record_with_notes.checkup_date,
            perawat_id=record_with_notes.perawat_id,
            health_record_id=record_with_notes.id,
            message="Catatan perawat terakhir ditemukan",
        )
    else:
        return LatestPerawatNotesResponse(
            has_notes=False,
            notes=None,
            checkup_date=None,
            perawat_id=None,
            health_record_id=None,
            message="Belum ada catatan dari perawat. Silakan kunjungi puskesmas untuk pemeriksaan.",
        )


@router.patch(
    "/me/profile/identitas",
    response_model=IbuHamilResponse,
    status_code=status.HTTP_200_OK,
    summary="Update identitas pribadi & alamat ibu hamil",
    description="""
Update identitas pribadi dan alamat ibu hamil yang sedang login.

**Akses:**
- Hanya dapat diakses oleh ibu hamil yang sedang login (role: ibu_hamil)
- Hanya dapat mengupdate profil dirinya sendiri

**Field yang dapat diupdate:**
- **Identitas Pribadi:**
  - nama_lengkap: Nama lengkap
  - date_of_birth: Tanggal lahir
  - nik: NIK (harus unik, tidak boleh duplikat)

- **Alamat & Lokasi:**
  - address: Alamat lengkap
  - provinsi: Provinsi
  - kota_kabupaten: Kota/Kabupaten
  - kelurahan: Kelurahan
  - kecamatan: Kecamatan
  - location: Koordinat lokasi [longitude, latitude]

**Catatan:**
- Endpoint ini khusus untuk halaman profile setting identitas pribadi
- Untuk update data kehamilan, gunakan endpoint `/me/profile/kehamilan`
""",
    responses={
        200: {
            "description": "Identitas pribadi & alamat berhasil diupdate",
            "content": {
                "application/json": {
                    "example": {
                        "id": 18,
                        "user_id": 15,
                        "nama_lengkap": "Siti Aminah Updated",
                        "nik": "3175091201850001",
                        "date_of_birth": "1985-12-12",
                        "address": "Jl. Mawar No. 10, RT 02 RW 05",
                        "provinsi": "Jambi",
                        "kota_kabupaten": "Kerinci",
                        "location": [101.3912, -2.0645],
                        "is_active": True
                    }
                }
            }
        },
        400: {
            "description": "Data tidak valid",
            "content": {
                "application/json": {
                    "examples": {
                        "nik_exists": {
                            "summary": "NIK sudah terdaftar",
                            "value": {"detail": "NIK sudah terdaftar di sistem. Setiap NIK hanya dapat digunakan sekali."}
                        },
                        "invalid_location": {
                            "summary": "Koordinat lokasi tidak valid",
                            "value": {"detail": "Koordinat lokasi tidak valid. Longitude harus antara -180 hingga 180, dan Latitude antara -90 hingga 90."}
                        }
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
async def update_my_profile_identitas(
    identitas_update: IbuHamilUpdateIdentitas,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> IbuHamil:
    """
    Update identitas pribadi & alamat ibu hamil yang sedang login.
    
    Args:
        identitas_update: Data update untuk identitas pribadi & alamat
        current_user: User yang sedang login (harus role ibu_hamil)
        db: Database session
        
    Returns:
        IbuHamil: Data ibu hamil yang sudah diupdate
        
    Raises:
        HTTPException 400: Data tidak valid (misalnya NIK sudah terdaftar)
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
    
    # Validasi: jika NIK diupdate, pastikan tidak duplikat
    if identitas_update.nik and identitas_update.nik != ibu.nik:
        existing_ibu = db.query(IbuHamil).filter(IbuHamil.nik == identitas_update.nik).first()
        if existing_ibu:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="NIK sudah terdaftar di sistem. Setiap NIK hanya dapat digunakan sekali.",
            )
    
    # Validasi location jika diupdate
    if identitas_update.location:
        lon, lat = identitas_update.location
        if not (-180.0 <= lon <= 180.0 and -90.0 <= lat <= 90.0):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Koordinat lokasi tidak valid. Longitude harus antara -180 hingga 180, dan Latitude antara -90 hingga 90.",
            )
    
    # Update profil identitas
    updated = crud_ibu_hamil.update(db, db_obj=ibu, obj_in=identitas_update)
    
    return updated


@router.patch(
    "/me/profile/kehamilan",
    response_model=IbuHamilResponse,
    status_code=status.HTTP_200_OK,
    summary="Update data kehamilan & riwayat kesehatan ibu hamil",
    description="""
Update data kehamilan dan riwayat kesehatan ibu hamil yang sedang login.

**Akses:**
- Hanya dapat diakses oleh ibu hamil yang sedang login (role: ibu_hamil)
- Hanya dapat mengupdate profil dirinya sendiri

**Field yang dapat diupdate:**
- **Data Kehamilan:**
  - usia_kehamilan: Usia kehamilan (minggu)
  - kehamilan_ke: Kehamilan ke berapa
  - jumlah_anak: Jumlah anak hidup
  - miscarriage_number: Riwayat keguguran
  - jarak_kehamilan_terakhir: Jarak kehamilan terakhir
  - last_menstrual_period: HPHT (Hari Pertama Haid Terakhir)
  - estimated_due_date: HPL (Hari Perkiraan Lahir)
  - previous_pregnancy_complications: Komplikasi kehamilan sebelumnya
  - pernah_caesar: Pernah persalinan caesar
  - pernah_perdarahan_saat_hamil: Pernah pendarahan saat hamil

- **Riwayat Kesehatan:**
  - riwayat_kesehatan_ibu: Object berisi:
    - darah_tinggi: Pernah darah tinggi?
    - diabetes: Pernah diabetes?
    - anemia: Pernah anemia?
    - penyakit_jantung: Pernah penyakit jantung?
    - asma: Pernah asma?
    - penyakit_ginjal: Pernah penyakit ginjal?
    - tbc_malaria: Pernah TBC/Malaria?

**Catatan:**
- Endpoint ini khusus untuk halaman profile setting data kehamilan
- Untuk update identitas pribadi & alamat, gunakan endpoint `/me/profile/identitas`
""",
    responses={
        200: {
            "description": "Data kehamilan & riwayat kesehatan berhasil diupdate",
            "content": {
                "application/json": {
                    "example": {
                        "id": 18,
                        "user_id": 15,
                        "nama_lengkap": "Siti Aminah",
                        "usia_kehamilan": 9,
                        "kehamilan_ke": 2,
                        "jumlah_anak": 1,
                        "is_active": True
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
async def update_my_profile_kehamilan(
    kehamilan_update: IbuHamilUpdateKehamilan,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> IbuHamil:
    """
    Update data kehamilan & riwayat kesehatan ibu hamil yang sedang login.
    
    Args:
        kehamilan_update: Data update untuk kehamilan & riwayat kesehatan
        current_user: User yang sedang login (harus role ibu_hamil)
        db: Database session
        
    Returns:
        IbuHamil: Data ibu hamil yang sudah diupdate
        
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
    
    # Update profil kehamilan
    updated = crud_ibu_hamil.update(db, db_obj=ibu, obj_in=kehamilan_update)
    
    return updated


@router.patch(
    "/me/user",
    response_model=UserResponse,
    status_code=status.HTTP_200_OK,
    summary="Update data user (untuk profile setting)",
    description="""
Update data user yang sedang login (email, phone, full_name, password).

**Akses:**
- Hanya dapat diakses oleh ibu hamil yang sedang login (role: ibu_hamil)
- Hanya dapat mengupdate data dirinya sendiri

**Field yang dapat diupdate:**
- email: Email baru (optional)
- phone: Nomor telepon baru (optional, harus unik)
- full_name: Nama lengkap baru (optional)
- password: Password baru (optional, minimal 6 karakter)

**Catatan:**
- Jika phone diupdate, pastikan phone baru belum terdaftar
- Jika email diupdate, pastikan email baru belum terdaftar
- Password akan di-hash sebelum disimpan
""",
    responses={
        200: {
            "description": "Data user berhasil diupdate",
            "content": {
                "application/json": {
                    "example": {
                        "id": 15,
                        "email": "siti.new@example.com",
                        "phone": "+628111222333",
                        "full_name": "Siti Aminah Updated",
                        "role": "ibu_hamil",
                        "is_active": True
                    }
                }
            }
        },
        400: {
            "description": "Data tidak valid atau sudah terdaftar",
            "content": {
                "application/json": {
                    "examples": {
                        "phone_exists": {
                            "summary": "Nomor telepon sudah terdaftar",
                            "value": {"detail": "Nomor telepon sudah terdaftar di sistem"}
                        },
                        "email_exists": {
                            "summary": "Email sudah terdaftar",
                            "value": {"detail": "Email sudah terdaftar di sistem"}
                        },
                        "password_short": {
                            "summary": "Password terlalu pendek",
                            "value": {"detail": "Password minimal 6 karakter"}
                        }
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
        }
    }
)
async def update_my_user(
    user_update: UserUpdateProfile,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> User:
    """
    Update data user yang sedang login.
    
    Args:
        user_update: Data update untuk user (email, phone, full_name, password)
        current_user: User yang sedang login (harus role ibu_hamil)
        db: Database session
        
    Returns:
        User: Data user yang sudah diupdate
        
    Raises:
        HTTPException 400: Data tidak valid atau sudah terdaftar
        HTTPException 403: Jika bukan role ibu_hamil
    """
    # Hanya ibu hamil yang dapat mengakses
    if current_user.role != "ibu_hamil":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Hanya ibu hamil yang dapat mengakses endpoint ini",
        )
    
    # Validasi: jika phone diupdate, pastikan tidak duplikat
    if user_update.phone and user_update.phone != current_user.phone:
        existing_user = crud_user.get_by_phone(db, phone=user_update.phone)
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Nomor telepon sudah terdaftar di sistem. Silakan gunakan nomor lain.",
            )
    
    # Validasi: jika email diupdate, pastikan tidak duplikat
    if user_update.email and user_update.email != current_user.email:
        existing_user = crud_user.get_by_email(db, email=user_update.email)
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email sudah terdaftar di sistem. Silakan gunakan email lain.",
            )
    
    # Prepare update data
    update_data = user_update.model_dump(exclude_unset=True, exclude={"password"})
    
    # Update password jika diisi
    if user_update.password:
        crud_user.update_password(db, user_id=current_user.id, new_password=user_update.password)
    
    # Update user data
    updated_user = crud_user.update(db, db_obj=current_user, obj_in=update_data)
    
    return updated_user


@router.get(
    "/{ibu_id}",
    response_model=IbuHamilResponse,
    status_code=status.HTTP_200_OK,
    summary="Detail ibu hamil berdasarkan ID",
    description="""
Mengambil detail profil ibu hamil berdasarkan ID.

**Siapa yang dapat mengakses:**
- **Super Admin**: Dapat melihat semua data ibu hamil (read-only)
- **Admin Puskesmas**: Dapat melihat data ibu hamil yang terdaftar di puskesmasnya
- **Perawat**: Dapat melihat data ibu hamil yang ditugaskan kepadanya
- **Kerabat**: Dapat melihat data ibu hamil yang terhubung dengannya
- **Ibu Hamil**: Dapat melihat data dirinya sendiri

**Data yang dikembalikan:**
- Identitas pribadi (nama lengkap, NIK, tanggal lahir, usia, golongan darah)
- Data kehamilan (usia kehamilan, HPHT, HPL, kehamilan ke, jumlah anak, dll)
- Alamat dan lokasi geografis
- Kontak darurat
- Riwayat kesehatan (darah tinggi, diabetes, anemia, dll)
- Risk level dan informasi perawat yang menentukan
- Status assignment ke puskesmas dan perawat
""",
    responses={
        200: {
            "description": "Detail ibu hamil berhasil diambil",
            "content": {
                "application/json": {
                    "example": {
                        "id": 1,
                        "user_id": 15,
                        "puskesmas_id": 2,
                        "perawat_id": 3,
                        "assigned_by_user_id": 10,
                        "nama_lengkap": "Siti Aminah",
                        "nik": "3175091201850001",
                        "date_of_birth": "1985-12-12",
                        "age": 39,
                        "blood_type": "O+",
                        "profile_photo_url": "/uploads/photos/profiles/ibu_hamil_1.jpg",
                        "last_menstrual_period": "2024-12-01",
                        "estimated_due_date": "2025-09-08",
                        "usia_kehamilan": 8,
                        "kehamilan_ke": 2,
                        "jumlah_anak": 1,
                        "miscarriage_number": 0,
                        "jarak_kehamilan_terakhir": "2 tahun",
                        "previous_pregnancy_complications": None,
                        "pernah_caesar": False,
                        "pernah_perdarahan_saat_hamil": False,
                        "address": "Jl. Mawar No. 10, RT 02 RW 05",
                        "provinsi": "Jambi",
                        "kota_kabupaten": "Kerinci",
                        "kelurahan": "Sungai Penuh",
                        "kecamatan": "Pesisir Bukit",
                        "location": [101.3912, -2.0645],
                        "emergency_contact_name": "Budi (Suami)",
                        "emergency_contact_phone": "+6281234567890",
                        "emergency_contact_relation": "Suami",
                        "darah_tinggi": False,
                        "diabetes": False,
                        "anemia": False,
                        "penyakit_jantung": False,
                        "asma": False,
                        "penyakit_ginjal": False,
                        "tbc_malaria": False,
                        "risk_level": "sedang",
                        "risk_level_set_by": 3,
                        "risk_level_set_by_name": "Bidan Rina",
                        "risk_level_set_at": "2026-01-15T10:00:00Z",
                        "assignment_date": "2026-01-10T08:00:00Z",
                        "assignment_distance_km": 2.5,
                        "assignment_method": "manual",
                        "healthcare_preference": "puskesmas",
                        "whatsapp_consent": True,
                        "data_sharing_consent": False,
                        "is_active": True,
                        "created_at": "2026-01-05T10:00:00Z",
                        "updated_at": "2026-01-15T10:00:00Z"
                    }
                }
            }
        },
        403: {
            "description": "Tidak memiliki akses untuk melihat data ini",
            "content": {
                "application/json": {
                    "example": {"detail": "Not authorized to access this record"}
                }
            }
        },
        404: {
            "description": "Ibu hamil tidak ditemukan",
            "content": {
                "application/json": {
                    "example": {"detail": "Ibu Hamil not found"}
                }
            }
        }
    }
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
    summary="Update data ibu hamil",
    description="""
Memperbarui data ibu hamil berdasarkan ID.

**Siapa yang dapat mengakses:**
- **Ibu Hamil**: Dapat mengupdate data dirinya sendiri
- **Admin Puskesmas**: Dapat mengupdate data ibu hamil yang terdaftar di puskesmasnya
- **Perawat**: Dapat mengupdate data ibu hamil yang ditugaskan kepadanya
- **Super Admin**: TIDAK dapat mengupdate (hanya read-only access)

**Field yang dapat diupdate:**
- Identitas: nama_lengkap, nik, date_of_birth, age, blood_type
- Kehamilan: usia_kehamilan, kehamilan_ke, jumlah_anak, miscarriage_number, dll
- Alamat: address, provinsi, kota_kabupaten, kelurahan, kecamatan, location
- Kontak darurat: emergency_contact_name, emergency_contact_phone, emergency_contact_relation
- Riwayat kesehatan: riwayat_kesehatan_ibu (nested object)
- Lainnya: risk_level (hanya oleh perawat), healthcare_preference, consent fields

**Catatan:**
- Tidak semua field wajib diisi, hanya field yang ingin diupdate
- Jika NIK diupdate, akan dicek untuk duplikasi
- Jika location diupdate, format harus [longitude, latitude]
""",
    responses={
        200: {
            "description": "Data ibu hamil berhasil diupdate",
            "content": {
                "application/json": {
                    "example": {
                        "id": 1,
                        "user_id": 15,
                        "puskesmas_id": 2,
                        "perawat_id": 3,
                        "nama_lengkap": "Siti Aminah Updated",
                        "nik": "3175091201850001",
                        "usia_kehamilan": 9,
                        "is_active": True,
                        "updated_at": "2026-01-22T10:00:00Z"
                    }
                }
            }
        },
        403: {
            "description": "Tidak memiliki akses untuk mengupdate data ini",
            "content": {
                "application/json": {
                    "examples": {
                        "not_authorized": {
                            "summary": "Bukan pemilik atau tidak memiliki akses",
                            "value": {"detail": "Not authorized to update this record"}
                        },
                        "super_admin": {
                            "summary": "Super admin tidak dapat update",
                            "value": {"detail": "Super admin tidak dapat mengupdate data ibu hamil (read-only access)."}
                        }
                    }
                }
            }
        },
        404: {
            "description": "Ibu hamil tidak ditemukan",
            "content": {
                "application/json": {
                    "example": {"detail": "Ibu Hamil not found"}
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
                                "loc": ["body", "nik"],
                                "msg": "NIK must be exactly 16 digits",
                                "type": "value_error"
                            }
                        ]
                    }
                }
            }
        }
    }
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

    return updated


@router.get(
    "/unassigned",
    response_model=List[IbuHamilResponse],
    status_code=status.HTTP_200_OK,
    summary="Daftar ibu hamil yang belum ter-assign ke puskesmas",
    description="""
Mendapatkan daftar ibu hamil yang belum ditugaskan ke puskesmas manapun.

**Siapa yang dapat mengakses:**
- **Super Admin**: Dapat melihat semua ibu hamil yang belum ter-assign (read-only)
- **Admin Puskesmas**: Dapat melihat daftar untuk proses assignment

**Kegunaan:**
- Untuk admin puskesmas melakukan assignment manual ibu hamil ke puskesmasnya
- Untuk monitoring ibu hamil yang belum terlayani

**Response:**
- Daftar ibu hamil dengan puskesmas_id = null
- Diurutkan berdasarkan waktu registrasi
""",
    responses={
        200: {
            "description": "Daftar ibu hamil belum ter-assign berhasil diambil",
            "content": {
                "application/json": {
                    "example": [
                        {
                            "id": 5,
                            "user_id": 25,
                            "puskesmas_id": None,
                            "perawat_id": None,
                            "nama_lengkap": "Dewi Sartika",
                            "nik": "3175091201900002",
                            "date_of_birth": "1990-05-15",
                            "location": [101.4, -2.1],
                            "address": "Jl. Kenanga No. 5",
                            "is_active": True,
                            "created_at": "2026-01-20T08:00:00Z"
                        }
                    ]
                }
            }
        },
        403: {
            "description": "Tidak memiliki akses",
            "content": {
                "application/json": {
                    "example": {"detail": "Not authorized"}
                }
            }
        }
    }
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
- Perawat harus aktif

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
                        "perawat_inactive": {
                            "summary": "Perawat tidak aktif",
                            "value": {"detail": "Perawat tidak aktif"}
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
        HTTPException 400: Ibu hamil belum ter-assign ke puskesmas atau perawat tidak aktif
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

    # Cek perawat aktif
    if not perawat.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Perawat tidak aktif",
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
    summary="Auto-assign ibu hamil ke puskesmas terdekat",
    description="""
Melakukan penugasan otomatis ibu hamil ke puskesmas terdekat berdasarkan lokasi geografis.

**Siapa yang dapat mengakses:**
- **Ibu Hamil**: Dapat melakukan auto-assign untuk dirinya sendiri

**Proses Auto-Assign:**
1. Mencari puskesmas terdekat dalam radius 20 km dari lokasi ibu hamil
2. Memilih puskesmas yang berstatus 'approved' dan aktif
3. Meng-assign ibu hamil ke puskesmas tersebut
4. Mencari perawat yang tersedia di puskesmas tersebut
5. Jika ada perawat tersedia, assign ibu hamil ke perawat tersebut
6. Mengirim notifikasi ke ibu hamil tentang penugasan

**Catatan:**
- Lokasi ibu hamil harus sudah terisi saat registrasi
- Jika tidak ada puskesmas dalam radius 20 km, akan mengembalikan error 404
- Perawat yang dipilih adalah perawat pertama yang tersedia (berdasarkan workload)

**Response:**
- Data ibu hamil yang sudah di-update dengan puskesmas_id dan perawat_id
- Data puskesmas yang ditugaskan
- Jarak dalam kilometer dari lokasi ibu hamil ke puskesmas
""",
    responses={
        200: {
            "description": "Auto-assign berhasil",
            "content": {
                "application/json": {
                    "example": {
                        "ibu_hamil": {
                            "id": 1,
                            "puskesmas_id": 2,
                            "perawat_id": 3,
                            "nama_lengkap": "Siti Aminah",
                            "nik": "3175091201850001",
                            "location": [101.39, -2.06],
                            "is_active": True
                        },
                        "puskesmas": {
                            "id": 2,
                            "name": "Puskesmas Sungai Penuh",
                            "code": "PKM-ABC-123",
                            "registration_status": "approved",
                            "is_active": True
                        },
                        "distance_km": 1.2
                    }
                }
            }
        },
        403: {
            "description": "Tidak memiliki akses",
            "content": {
                "application/json": {
                    "example": {"detail": "Not authorized"}
                }
            }
        },
        404: {
            "description": "Tidak ada puskesmas terdekat atau ibu hamil tidak ditemukan",
            "content": {
                "application/json": {
                    "examples": {
                        "ibu_not_found": {
                            "summary": "Ibu hamil tidak ditemukan",
                            "value": {"detail": "Ibu Hamil not found"}
                        },
                        "no_puskesmas": {
                            "summary": "Tidak ada puskesmas terdekat",
                            "value": {"detail": "Tidak ada Puskesmas terdekat dengan kapasitas tersedia dalam radius"}
                        }
                    }
                }
            }
        }
    }
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
        ibu_hamil=IbuHamilResponse.model_validate(assigned_ibu),
        puskesmas=PuskesmasResponse.model_validate(puskesmas),
        distance_km=distance,
    )


@router.get(
    "/by-puskesmas/{puskesmas_id}",
    response_model=List[IbuHamilResponse],
    status_code=status.HTTP_200_OK,
    summary="Daftar ibu hamil per puskesmas",
    description="""
Mendapatkan daftar ibu hamil yang terdaftar di puskesmas tertentu.

**Akses:**
- Super admin (read-only)
- Admin puskesmas tersebut
- Perawat di puskesmas tersebut

**Query Parameters:**
- skip: Jumlah data yang dilewati (default: 0)
- limit: Maksimal jumlah data yang dikembalikan (default: 100)

**Response:**
- Daftar ibu hamil yang ter-assign ke puskesmas ini
- Termasuk informasi risk level: `risk_level`, `risk_level_set_by`, `risk_level_set_by_name`, `risk_level_set_at`
""",
    responses={
        200: {
            "description": "Daftar ibu hamil berhasil diambil",
            "content": {
                "application/json": {
                    "example": [
                        {
                            "id": 1,
                            "user_id": 20,
                            "puskesmas_id": 1,
                            "perawat_id": 5,
                            "assigned_by_user_id": 10,
                            "nama_lengkap": "Siti Aminah",
                            "nik": "3175091201850001",
                            "date_of_birth": "1985-12-12",
                            "age": 39,
                            "blood_type": "O+",
                            "profile_photo_url": "/uploads/photos/profiles/ibu_hamil_1.jpg",
                            "last_menstrual_period": "2024-12-01",
                            "estimated_due_date": "2025-09-08",
                            "usia_kehamilan": 8,
                            "kehamilan_ke": 2,
                            "jumlah_anak": 1,
                            "miscarriage_number": 0,
                            "jarak_kehamilan_terakhir": "2 tahun",
                            "previous_pregnancy_complications": None,
                            "pernah_caesar": False,
                            "pernah_perdarahan_saat_hamil": False,
                            "address": "Jl. Mawar No. 10, RT 02 RW 05",
                            "provinsi": "Jambi",
                            "kota_kabupaten": "Kerinci",
                            "kelurahan": "Sungai Penuh",
                            "kecamatan": "Pesisir Bukit",
                            "location": [101.3912, -2.0645],
                            "emergency_contact_name": "Budi (Suami)",
                            "emergency_contact_phone": "+6281234567890",
                            "emergency_contact_relation": "Suami",
                            "darah_tinggi": False,
                            "diabetes": False,
                            "anemia": False,
                            "penyakit_jantung": False,
                            "asma": False,
                            "penyakit_ginjal": False,
                            "tbc_malaria": False,
                            "risk_level": "tinggi",
                            "risk_level_set_by": 5,
                            "risk_level_set_by_name": "Bidan Rina Wijaya",
                            "risk_level_set_at": "2026-01-20T10:30:00Z",
                            "assignment_date": "2026-01-15T08:00:00Z",
                            "assignment_distance_km": 2.5,
                            "assignment_method": "manual",
                            "healthcare_preference": "puskesmas",
                            "whatsapp_consent": True,
                            "data_sharing_consent": False,
                            "is_active": True,
                            "created_at": "2026-01-10T10:00:00Z",
                            "updated_at": "2026-01-20T10:30:00Z"
                        }
                    ]
                }
            }
        },
        403: {
            "description": "Tidak memiliki akses",
            "content": {
                "application/json": {
                    "example": {"detail": "Not authorized"}
                }
            }
        },
        404: {
            "description": "Puskesmas tidak ditemukan",
            "content": {
                "application/json": {
                    "example": {"detail": "Puskesmas tidak ditemukan"}
                }
            }
        }
    }
)
async def list_by_puskesmas(
    puskesmas_id: int,
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> List[IbuHamilResponse]:
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
        perawat = crud_perawat.get_by_user_id(db, user_id=current_user.id)
        if not perawat or perawat.puskesmas_id != puskesmas_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized",
            )

    # Query with eager loading for risk_assessor relationship
    ibu_hamil_list = (
        db.execute(
            select(IbuHamil)
            .options(selectinload(IbuHamil.risk_assessor))
            .where(IbuHamil.puskesmas_id == puskesmas_id)
            .offset(skip)
            .limit(limit)
        )
        .scalars()
        .all()
    )

    # Build response with risk_level_set_by_name
    result = []
    for ibu in ibu_hamil_list:
        response = IbuHamilResponse.model_validate(ibu)
        # Populate risk_level_set_by_name from relationship
        if ibu.risk_assessor:
            response.risk_level_set_by_name = ibu.risk_assessor.nama_lengkap
        result.append(response)

    return result


@router.get(
    "/by-perawat/{perawat_id}",
    response_model=List[IbuHamilResponse],
    status_code=status.HTTP_200_OK,
    summary="Daftar ibu hamil yang ditangani perawat",
    description="""
Mendapatkan daftar ibu hamil yang ditugaskan ke perawat tertentu.

**Siapa yang dapat mengakses:**
- **Super Admin**: Dapat melihat semua data (read-only)
- **Perawat**: Dapat melihat daftar ibu hamil yang ditugaskan kepadanya sendiri
- **Admin Puskesmas**: Dapat melihat daftar ibu hamil dari perawat di puskesmasnya

**Kegunaan:**
- Untuk perawat melihat daftar pasien yang harus ditangani
- Untuk admin puskesmas monitoring workload perawat
- Untuk super admin monitoring layanan

**Response:**
- Daftar ibu hamil dengan perawat_id sesuai parameter
- Termasuk informasi risk level dan data kehamilan lengkap
""",
    responses={
        200: {
            "description": "Daftar ibu hamil berhasil diambil",
            "content": {
                "application/json": {
                    "example": [
                        {
                            "id": 1,
                            "user_id": 15,
                            "puskesmas_id": 2,
                            "perawat_id": 3,
                            "nama_lengkap": "Siti Aminah",
                            "nik": "3175091201850001",
                            "date_of_birth": "1985-12-12",
                            "age": 39,
                            "blood_type": "O+",
                            "usia_kehamilan": 8,
                            "risk_level": "sedang",
                            "is_active": True
                        }
                    ]
                }
            }
        },
        403: {
            "description": "Tidak memiliki akses",
            "content": {
                "application/json": {
                    "example": {"detail": "Not authorized"}
                }
            }
        },
        404: {
            "description": "Perawat tidak ditemukan",
            "content": {
                "application/json": {
                    "example": {"detail": "Perawat tidak ditemukan"}
                }
            }
        }
    }
)
async def list_by_perawat(
    perawat_id: int,
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> List[IbuHamilResponse]:
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

    # Query with eager loading for risk_assessor relationship
    ibu_hamil_list = (
        db.execute(
            select(IbuHamil)
            .options(selectinload(IbuHamil.risk_assessor))
            .where(IbuHamil.perawat_id == perawat_id)
            .offset(skip)
            .limit(limit)
        )
        .scalars()
        .all()
    )

    # Build response with risk_level_set_by_name
    result = []
    for ibu in ibu_hamil_list:
        response = IbuHamilResponse.model_validate(ibu)
        if ibu.risk_assessor:
            response.risk_level_set_by_name = ibu.risk_assessor.nama_lengkap
        result.append(response)

    return result


@router.get(
    "/puskesmas/my-patients",
    response_model=List[IbuHamilResponse],
    status_code=status.HTTP_200_OK,
    summary="Daftar ibu hamil di puskesmas saya",
    description="""
Mendapatkan daftar lengkap ibu hamil yang terdaftar di puskesmas milik admin yang sedang login.

**Siapa yang dapat mengakses:**
- **Admin Puskesmas**: Hanya dapat melihat ibu hamil di puskesmasnya sendiri

**Data yang dikembalikan (sesuai data registrasi):**
- **Identitas Pribadi:** nama_lengkap, NIK, date_of_birth, age, blood_type, profile_photo_url
- **Data Kehamilan:** last_menstrual_period (HPHT), estimated_due_date (HPL), usia_kehamilan,
  kehamilan_ke, jumlah_anak, miscarriage_number, jarak_kehamilan_terakhir,
  previous_pregnancy_complications, pernah_caesar, pernah_perdarahan_saat_hamil
- **Alamat & Lokasi:** address, provinsi, kota_kabupaten, kelurahan, kecamatan, location
- **Kontak Darurat:** emergency_contact_name, emergency_contact_phone, emergency_contact_relation
- **Riwayat Kesehatan:** darah_tinggi, diabetes, anemia, penyakit_jantung, asma, penyakit_ginjal, tbc_malaria
- **Risk Assessment:** risk_level, risk_level_set_by, risk_level_set_by_name, risk_level_set_at
- **Assignment:** puskesmas_id, perawat_id, assignment_date, assignment_distance_km, assignment_method
- **Status:** is_active, created_at, updated_at
""",
    responses={
        200: {
            "description": "Daftar ibu hamil berhasil diambil",
            "content": {
                "application/json": {
                    "example": [
                        {
                            "id": 1,
                            "user_id": 15,
                            "puskesmas_id": 2,
                            "perawat_id": 3,
                            "nama_lengkap": "Siti Aminah",
                            "nik": "3175091201850001",
                            "date_of_birth": "1985-12-12",
                            "age": 39,
                            "blood_type": "O+",
                            "usia_kehamilan": 8,
                            "kehamilan_ke": 2,
                            "jumlah_anak": 1,
                            "risk_level": "sedang",
                            "address": "Jl. Mawar No. 10",
                            "emergency_contact_name": "Budi (Suami)",
                            "emergency_contact_phone": "+6281234567890",
                            "is_active": True
                        }
                    ]
                }
            }
        },
        403: {
            "description": "Tidak memiliki akses atau bukan admin puskesmas",
            "content": {
                "application/json": {
                    "example": {"detail": "Hanya admin puskesmas yang dapat mengakses endpoint ini"}
                }
            }
        },
        404: {
            "description": "Puskesmas tidak ditemukan",
            "content": {
                "application/json": {
                    "example": {"detail": "Puskesmas tidak ditemukan untuk user ini"}
                }
            }
        }
    }
)
async def list_my_patients_puskesmas(
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(require_role("puskesmas")),
    db: Session = Depends(get_db),
) -> List[IbuHamilResponse]:
    """
    Mendapatkan daftar ibu hamil di puskesmas milik admin yang sedang login.
    """
    # Cari puskesmas berdasarkan admin_user_id
    puskesmas = crud_puskesmas.get_by_admin_user_id(db, admin_user_id=current_user.id)
    if not puskesmas:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Puskesmas tidak ditemukan untuk user ini",
        )

    # Query with eager loading for risk_assessor relationship
    ibu_hamil_list = (
        db.execute(
            select(IbuHamil)
            .options(selectinload(IbuHamil.risk_assessor))
            .where(IbuHamil.puskesmas_id == puskesmas.id)
            .offset(skip)
            .limit(limit)
        )
        .scalars()
        .all()
    )

    # Build response with risk_level_set_by_name
    result = []
    for ibu in ibu_hamil_list:
        response = IbuHamilResponse.model_validate(ibu)
        if ibu.risk_assessor:
            response.risk_level_set_by_name = ibu.risk_assessor.nama_lengkap
        result.append(response)

    return result


@router.get(
    "/perawat/my-patients",
    response_model=List[IbuHamilResponse],
    status_code=status.HTTP_200_OK,
    summary="Daftar ibu hamil yang saya tangani",
    description="""
Mendapatkan daftar lengkap ibu hamil yang ditugaskan ke perawat yang sedang login.

**Siapa yang dapat mengakses:**
- **Perawat**: Hanya dapat melihat ibu hamil yang ditugaskan kepadanya

**Data yang dikembalikan (sesuai data registrasi):**
- **Identitas Pribadi:** nama_lengkap, NIK, date_of_birth, age, blood_type, profile_photo_url
- **Data Kehamilan:** last_menstrual_period (HPHT), estimated_due_date (HPL), usia_kehamilan,
  kehamilan_ke, jumlah_anak, miscarriage_number, jarak_kehamilan_terakhir,
  previous_pregnancy_complications, pernah_caesar, pernah_perdarahan_saat_hamil
- **Alamat & Lokasi:** address, provinsi, kota_kabupaten, kelurahan, kecamatan, location
- **Kontak Darurat:** emergency_contact_name, emergency_contact_phone, emergency_contact_relation
- **Riwayat Kesehatan:** darah_tinggi, diabetes, anemia, penyakit_jantung, asma, penyakit_ginjal, tbc_malaria
- **Risk Assessment:** risk_level, risk_level_set_by, risk_level_set_by_name, risk_level_set_at
- **Assignment:** puskesmas_id, perawat_id, assignment_date, assignment_distance_km, assignment_method
- **Status:** is_active, created_at, updated_at
""",
    responses={
        200: {
            "description": "Daftar ibu hamil berhasil diambil",
            "content": {
                "application/json": {
                    "example": [
                        {
                            "id": 1,
                            "user_id": 15,
                            "puskesmas_id": 2,
                            "perawat_id": 3,
                            "nama_lengkap": "Siti Aminah",
                            "nik": "3175091201850001",
                            "date_of_birth": "1985-12-12",
                            "age": 39,
                            "blood_type": "O+",
                            "usia_kehamilan": 8,
                            "kehamilan_ke": 2,
                            "jumlah_anak": 1,
                            "risk_level": "sedang",
                            "address": "Jl. Mawar No. 10",
                            "emergency_contact_name": "Budi (Suami)",
                            "emergency_contact_phone": "+6281234567890",
                            "is_active": True
                        }
                    ]
                }
            }
        },
        403: {
            "description": "Tidak memiliki akses atau bukan perawat",
            "content": {
                "application/json": {
                    "example": {"detail": "Hanya perawat yang dapat mengakses endpoint ini"}
                }
            }
        },
        404: {
            "description": "Profil perawat tidak ditemukan",
            "content": {
                "application/json": {
                    "example": {"detail": "Profil perawat tidak ditemukan untuk user ini"}
                }
            }
        }
    }
)
async def list_my_patients_perawat(
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(require_role("perawat")),
    db: Session = Depends(get_db),
) -> List[IbuHamilResponse]:
    """
    Mendapatkan daftar ibu hamil yang ditugaskan ke perawat yang sedang login.
    """
    # Cari perawat berdasarkan user_id
    perawat = crud_perawat.get_by_user_id(db, user_id=current_user.id)
    if not perawat:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Profil perawat tidak ditemukan untuk user ini",
        )

    # Query with eager loading for risk_assessor relationship
    ibu_hamil_list = (
        db.execute(
            select(IbuHamil)
            .options(selectinload(IbuHamil.risk_assessor))
            .where(IbuHamil.perawat_id == perawat.id)
            .offset(skip)
            .limit(limit)
        )
        .scalars()
        .all()
    )

    # Build response with risk_level_set_by_name
    result = []
    for ibu in ibu_hamil_list:
        response = IbuHamilResponse.model_validate(ibu)
        if ibu.risk_assessor:
            response.risk_level_set_by_name = ibu.risk_assessor.nama_lengkap
        result.append(response)

    return result


@router.get(
    "/perawat/{ibu_id}/latest-health-record",
    response_model=HealthRecordResponse,
    status_code=status.HTTP_200_OK,
    summary="Ambil health record terbaru ibu hamil (untuk perawat)",
    description="""
Mengambil health record terbaru dari ibu hamil tertentu yang ditugaskan ke perawat yang sedang login.

Endpoint ini digunakan untuk menampilkan ringkasan kondisi kesehatan terakhir ibu hamil di halaman dashboard perawat.

## Akses
- **Role yang diizinkan:** `perawat`
- Perawat hanya dapat mengakses health record ibu hamil yang ditugaskan kepadanya

## Path Parameter
| Parameter | Tipe | Keterangan |
|-----------|------|------------|
| ibu_id | integer | ID ibu hamil yang ingin dilihat health record-nya |

## Response Fields

### Data Pemeriksaan
| Field | Tipe | Keterangan |
|-------|------|------------|
| id | integer | ID unik health record |
| ibu_hamil_id | integer | ID ibu hamil |
| perawat_id | integer | ID perawat yang memeriksa (null jika mandiri) |
| checkup_date | date | Tanggal pemeriksaan (YYYY-MM-DD) |
| checked_by | string | Siapa yang memeriksa: `perawat` atau `mandiri` |

### Usia Kehamilan
| Field | Tipe | Keterangan |
|-------|------|------------|
| gestational_age_weeks | integer | Usia kehamilan dalam minggu |
| gestational_age_days | integer | Usia kehamilan dalam hari (sisa) |

### Tanda Vital (Wajib)
| Field | Tipe | Keterangan |
|-------|------|------------|
| blood_pressure_systolic | integer | Tekanan darah sistolik (mmHg) |
| blood_pressure_diastolic | integer | Tekanan darah diastolik (mmHg) |
| heart_rate | integer | Detak jantung (bpm) |
| body_temperature | float | Suhu tubuh (°C) |
| weight | float | Berat badan (kg) |
| complaints | string | Keluhan yang dirasakan |

### Data Lab/Puskesmas (Opsional)
| Field | Tipe | Keterangan |
|-------|------|------------|
| hemoglobin | float | Kadar hemoglobin (g/dL) |
| blood_glucose | float | Gula darah (mg/dL) |
| protein_urin | string | Protein urin (negatif, +1, +2, +3, +4) |
| upper_arm_circumference | float | Lingkar lengan atas/LILA (cm) |
| fundal_height | float | Tinggi fundus uteri (cm) |
| fetal_heart_rate | integer | Detak jantung janin (bpm) |
| notes | string | Catatan tambahan dari perawat |

### Timestamp
| Field | Tipe | Keterangan |
|-------|------|------------|
| created_at | datetime | Waktu record dibuat |
| updated_at | datetime | Waktu record terakhir diupdate |

## Error Handling
- **401**: Token tidak valid atau expired
- **403**: User bukan perawat atau ibu hamil tidak ditugaskan ke perawat ini
- **404**: Profil perawat tidak ditemukan, ibu hamil tidak ditemukan, atau belum ada health record
""",
    responses={
        200: {
            "description": "Health record terbaru berhasil diambil",
            "content": {
                "application/json": {
                    "example": {
                        "id": 1,
                        "ibu_hamil_id": 1,
                        "perawat_id": 1,
                        "checkup_date": "2025-02-15",
                        "checked_by": "perawat",
                        "gestational_age_weeks": 28,
                        "gestational_age_days": 3,
                        "blood_pressure_systolic": 120,
                        "blood_pressure_diastolic": 80,
                        "heart_rate": 72,
                        "body_temperature": 36.8,
                        "weight": 65.5,
                        "complaints": "Tidak ada keluhan",
                        "hemoglobin": 12.5,
                        "blood_glucose": 95.0,
                        "protein_urin": "negatif",
                        "upper_arm_circumference": 25.0,
                        "fundal_height": 28.0,
                        "fetal_heart_rate": 140,
                        "notes": "Ibu dalam kondisi sehat",
                        "created_at": "2025-02-15T10:00:00Z",
                        "updated_at": "2025-02-15T10:00:00Z",
                    }
                }
            },
        },
        401: {
            "description": "Token tidak valid atau expired",
            "content": {
                "application/json": {
                    "example": {"detail": "Could not validate credentials"}
                }
            },
        },
        403: {
            "description": "Tidak memiliki akses",
            "content": {
                "application/json": {
                    "examples": {
                        "not_perawat": {
                            "summary": "Bukan role perawat",
                            "value": {"detail": "Hanya perawat yang dapat mengakses endpoint ini"}
                        },
                        "not_assigned": {
                            "summary": "Ibu hamil tidak ditugaskan ke perawat ini",
                            "value": {"detail": "Anda tidak memiliki akses ke data ibu hamil ini"}
                        }
                    }
                }
            },
        },
        404: {
            "description": "Data tidak ditemukan",
            "content": {
                "application/json": {
                    "examples": {
                        "perawat_not_found": {
                            "summary": "Profil perawat tidak ditemukan",
                            "value": {"detail": "Profil perawat tidak ditemukan untuk user ini"}
                        },
                        "ibu_not_found": {
                            "summary": "Ibu hamil tidak ditemukan",
                            "value": {"detail": "Ibu hamil tidak ditemukan"}
                        },
                        "no_health_record": {
                            "summary": "Belum ada health record",
                            "value": {"detail": "Belum ada data health record. Silakan lakukan pemeriksaan kesehatan terlebih dahulu."}
                        }
                    }
                }
            },
        },
    },
)
async def get_ibu_hamil_latest_health_record_for_perawat(
    ibu_id: int,
    current_user: User = Depends(require_role("perawat")),
    db: Session = Depends(get_db),
) -> HealthRecordResponse:
    """
    Mengambil health record terbaru dari ibu hamil tertentu untuk perawat.

    Args:
        ibu_id: ID ibu hamil yang ingin dilihat health record-nya
        current_user: User yang sedang login (harus role perawat)
        db: Database session

    Returns:
        HealthRecordResponse: Data health record terbaru

    Raises:
        HTTPException 403: Jika bukan role perawat atau ibu hamil tidak ditugaskan ke perawat ini
        HTTPException 404: Jika profil perawat tidak ditemukan, ibu hamil tidak ditemukan, atau belum ada health record
    """
    # Cari perawat berdasarkan user_id
    perawat = crud_perawat.get_by_user_id(db, user_id=current_user.id)
    if not perawat:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Profil perawat tidak ditemukan untuk user ini",
        )

    # Cari ibu hamil berdasarkan ID
    ibu = crud_ibu_hamil.get(db, id=ibu_id)
    if not ibu:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Ibu hamil tidak ditemukan",
        )

    # Validasi bahwa ibu hamil ditugaskan ke perawat ini
    if ibu.perawat_id != perawat.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Anda tidak memiliki akses ke data ibu hamil ini",
        )

    # Get latest health record
    latest_record = crud_health_record.get_latest(db, ibu_hamil_id=ibu.id)
    if not latest_record:
        raise HealthRecordNotFoundException()

    return HealthRecordResponse.model_validate(latest_record)


@router.get(
    "/{ibu_id}/detail",
    response_model=IbuHamilResponse,
    status_code=status.HTTP_200_OK,
    summary="Detail lengkap ibu hamil",
    description="""
Mendapatkan data detail lengkap seorang ibu hamil berdasarkan ID.
Data yang dikembalikan adalah semua data yang diisi saat registrasi.

**Siapa yang dapat mengakses:**
- **Admin Puskesmas**: Dapat melihat detail ibu hamil yang terdaftar di puskesmasnya
- **Perawat**: Dapat melihat detail ibu hamil yang ditugaskan kepadanya
- **Super Admin**: Dapat melihat semua data (read-only)
- **Ibu Hamil**: Dapat melihat data dirinya sendiri
- **Kerabat**: Dapat melihat data ibu hamil yang terhubung dengannya

**Data yang dikembalikan (sesuai data registrasi):**
- **Identitas Pribadi:** nama_lengkap, NIK, date_of_birth, age, blood_type, profile_photo_url
- **Data Kehamilan:**
  - last_menstrual_period (HPHT - Hari Pertama Haid Terakhir)
  - estimated_due_date (HPL - Hari Perkiraan Lahir)
  - usia_kehamilan (dalam minggu)
  - kehamilan_ke, jumlah_anak, miscarriage_number
  - jarak_kehamilan_terakhir
  - previous_pregnancy_complications (komplikasi kehamilan sebelumnya)
  - pernah_caesar (riwayat operasi caesar)
  - pernah_perdarahan_saat_hamil (riwayat perdarahan)
- **Alamat & Lokasi:** address, provinsi, kota_kabupaten, kelurahan, kecamatan, location [longitude, latitude]
- **Kontak Darurat:** emergency_contact_name, emergency_contact_phone, emergency_contact_relation
- **Riwayat Kesehatan Ibu:**
  - darah_tinggi (hipertensi)
  - diabetes
  - anemia
  - penyakit_jantung
  - asma
  - penyakit_ginjal
  - tbc_malaria
- **Risk Assessment:** risk_level (rendah/sedang/tinggi), risk_level_set_by, risk_level_set_by_name, risk_level_set_at
- **Assignment:** puskesmas_id, perawat_id, assignment_date, assignment_distance_km, assignment_method
- **Preferensi:** healthcare_preference, whatsapp_consent, data_sharing_consent
- **Status:** is_active, created_at, updated_at
""",
    responses={
        200: {
            "description": "Detail ibu hamil berhasil diambil",
            "content": {
                "application/json": {
                    "example": {
                        "id": 1,
                        "user_id": 15,
                        "puskesmas_id": 2,
                        "perawat_id": 3,
                        "assigned_by_user_id": 10,
                        "nama_lengkap": "Siti Aminah",
                        "nik": "3175091201850001",
                        "date_of_birth": "1985-12-12",
                        "age": 39,
                        "blood_type": "O+",
                        "profile_photo_url": "/uploads/photos/profiles/ibu_hamil/ibu_hamil_1.jpg",
                        "last_menstrual_period": "2024-12-01",
                        "estimated_due_date": "2025-09-08",
                        "usia_kehamilan": 8,
                        "kehamilan_ke": 2,
                        "jumlah_anak": 1,
                        "miscarriage_number": 0,
                        "jarak_kehamilan_terakhir": "2 tahun",
                        "previous_pregnancy_complications": None,
                        "pernah_caesar": False,
                        "pernah_perdarahan_saat_hamil": False,
                        "address": "Jl. Mawar No. 10, RT 02 RW 05",
                        "provinsi": "Jambi",
                        "kota_kabupaten": "Kerinci",
                        "kelurahan": "Sungai Penuh",
                        "kecamatan": "Pesisir Bukit",
                        "location": [101.3912, -2.0645],
                        "emergency_contact_name": "Budi (Suami)",
                        "emergency_contact_phone": "+6281234567890",
                        "emergency_contact_relation": "Suami",
                        "darah_tinggi": False,
                        "diabetes": False,
                        "anemia": False,
                        "penyakit_jantung": False,
                        "asma": False,
                        "penyakit_ginjal": False,
                        "tbc_malaria": False,
                        "risk_level": "sedang",
                        "risk_level_set_by": 3,
                        "risk_level_set_by_name": "Bidan Rina",
                        "risk_level_set_at": "2026-01-15T10:00:00Z",
                        "assignment_date": "2026-01-10T08:00:00Z",
                        "assignment_distance_km": 2.5,
                        "assignment_method": "auto",
                        "healthcare_preference": "puskesmas",
                        "whatsapp_consent": True,
                        "data_sharing_consent": False,
                        "is_active": True,
                        "created_at": "2026-01-10T08:00:00Z",
                        "updated_at": "2026-01-15T10:00:00Z"
                    }
                }
            }
        },
        403: {
            "description": "Tidak memiliki akses",
            "content": {
                "application/json": {
                    "example": {"detail": "Not authorized to access this record"}
                }
            }
        },
        404: {
            "description": "Ibu hamil tidak ditemukan",
            "content": {
                "application/json": {
                    "example": {"detail": "Ibu Hamil not found"}
                }
            }
        }
    }
)
async def get_ibu_hamil_detail(
    ibu_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> IbuHamilResponse:
    """
    Mendapatkan data detail lengkap ibu hamil berdasarkan ID.
    """
    # Query with eager loading for risk_assessor relationship
    ibu = (
        db.execute(
            select(IbuHamil)
            .options(selectinload(IbuHamil.risk_assessor))
            .where(IbuHamil.id == ibu_id)
        )
        .scalars()
        .first()
    )

    if not ibu:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Ibu Hamil not found",
        )

    # Authorize access
    _authorize_view(ibu, current_user, db)

    # Build response with risk_level_set_by_name
    response = IbuHamilResponse.model_validate(ibu)
    if ibu.risk_assessor:
        response.risk_level_set_by_name = ibu.risk_assessor.nama_lengkap

    return response


__all__ = ["router"]
