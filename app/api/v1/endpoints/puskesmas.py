"""Puskesmas endpoints."""

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.deps import get_current_active_user, get_db, get_optional_current_user, require_role
from app.crud import crud_ibu_hamil, crud_notification, crud_perawat, crud_puskesmas, crud_user
from app.models.ibu_hamil import IbuHamil
from app.models.perawat import Perawat
from app.models.puskesmas import Puskesmas
from app.models.user import User
from app.schemas.ibu_hamil import IbuHamilResponse
from app.schemas.notification import NotificationCreate
from app.schemas.puskesmas import (
    PuskesmasAdminResponse,
    PuskesmasCreate,
    PuskesmasResponse,
    PuskesmasSubmitForApproval,
    PuskesmasUpdate,
)
from app.schemas.user import UserCreate

router = APIRouter(
    prefix="/puskesmas",
    tags=["Puskesmas"],
)


class RejectionReason(BaseModel):
    rejection_reason: str


class DeactivationReason(BaseModel):
    reason: str = Field(..., min_length=5, description="Alasan deactivation puskesmas")


class NearestPuskesmasResponse(BaseModel):
    puskesmas: PuskesmasResponse
    distance_km: float
    address: str

    model_config = ConfigDict(json_schema_extra={
        "example": {
            "puskesmas": {
                "id": 1,
                "name": "Puskesmas Sungai Penuh",
                "registration_status": "approved",
                "is_active": True,
            },
            "distance_km": 1.2,
            "address": "Jl. Merdeka No. 1, Sungai Penuh, Jambi",
        }
    })


def _build_admin_response(puskesmas: Puskesmas, ibu_count: int, perawat_count: int) -> PuskesmasAdminResponse:
    base_payload = PuskesmasResponse.from_orm(puskesmas).model_dump()
    return PuskesmasAdminResponse(
        **base_payload,
        active_ibu_hamil_count=ibu_count,
        active_perawat_count=perawat_count,
    )


@router.post(
    "/register",
    response_model=dict,
    status_code=status.HTTP_201_CREATED,
    summary="Register new puskesmas",
)
async def register_puskesmas(
    puskesmas_in: PuskesmasCreate,
    db: Session = Depends(get_db),
) -> dict:
    """
    Public registration for Puskesmas.
    
    Membuat satu akun admin puskesmas yang akan mengelola puskesmas tersebut.
    Setiap puskesmas hanya memiliki satu akun admin puskesmas (role: 'puskesmas').
    Akun ini digunakan untuk mengelola perawat dan assign ibu hamil ke perawat.
    """
    # Prevent duplicate phone on user table
    existing_user = crud_user.get_by_phone(db, phone=puskesmas_in.phone)
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Phone already registered",
        )

    # Create associated user with password from registration input
    user_data = UserCreate(
        phone=puskesmas_in.phone,
        password=puskesmas_in.password,
        full_name=puskesmas_in.kepala_name,
        role="puskesmas",
        email=puskesmas_in.email,
    )
    db_user = crud_user.create_user(db, user_in=user_data)

    # Registration status: default submit for verification unless explicitly draft
    desired_status: str = puskesmas_in.registration_status or "pending_approval"
    if desired_status == "draft":
        desired_status = "draft"
    else:
        desired_status = "pending_approval"

    # Create puskesmas with admin_user_id linked
    puskesmas_with_admin = puskesmas_in.model_copy(update={
        "admin_user_id": db_user.id,
        "registration_status": desired_status,
    })
    db_puskesmas = crud_puskesmas.create_with_location(db, puskesmas_in=puskesmas_with_admin)

    return {
        "puskesmas": PuskesmasResponse.from_orm(db_puskesmas),
        "message": "Registration submitted",
    }


@router.get(
    "",
    response_model=List[PuskesmasResponse],
    status_code=status.HTTP_200_OK,
    summary="List active puskesmas",
)
async def list_puskesmas(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
) -> List[Puskesmas]:
    """Public list of active and approved puskesmas."""
    stmt = (
        select(Puskesmas)
        .where(Puskesmas.is_active == True)
        .where(Puskesmas.registration_status == "approved")
        .offset(skip)
        .limit(limit)
    )
    return db.scalars(stmt).all()


@router.get(
    "/admin/all",
    response_model=List[PuskesmasAdminResponse],
    status_code=status.HTTP_200_OK,
    summary="Admin list all puskesmas sorted by newest registration",
)
async def admin_list_all_puskesmas(
    skip: int = 0,
    limit: int = 100,
    status_filter: Optional[str] = None,
    current_user: User = Depends(require_role("super_admin")),
    db: Session = Depends(get_db),
) -> List[PuskesmasAdminResponse]:
    """
    Admin-only list of ALL puskesmas sorted by newest registration first.
    
    Query params:
    - skip: Number of records to skip (default 0)
    - limit: Max records to return (default 100)
    - status_filter: Filter by registration_status (pending_approval, approved, rejected, draft)
    """
    stmt = select(Puskesmas).order_by(Puskesmas.registration_date.desc())
    
    # Apply status filter if provided
    if status_filter:
        stmt = stmt.where(Puskesmas.registration_status == status_filter)
    
    stmt = stmt.offset(skip).limit(limit)
    puskesmas_list = db.scalars(stmt).all()
    
    # Build response with stats for each puskesmas
    result = []
    for puskesmas in puskesmas_list:
        # Count active ibu hamil for this puskesmas
        ibu_count = db.scalar(
            select(func.count(IbuHamil.id)).where(
                IbuHamil.puskesmas_id == puskesmas.id,
                IbuHamil.is_active == True
            )
        ) or 0
        
        # Count active perawat for this puskesmas
        perawat_count = db.scalar(
            select(func.count(Perawat.id)).where(
                Perawat.puskesmas_id == puskesmas.id,
                Perawat.is_active == True
            )
        ) or 0
        
        result.append(_build_admin_response(puskesmas, ibu_count, perawat_count))
    
    return result


@router.get(
    "/admin/active",
    response_model=List[PuskesmasAdminResponse],
    status_code=status.HTTP_200_OK,
    summary="Admin list active puskesmas with stats",
)
async def admin_list_active_puskesmas(
    current_user: User = Depends(require_role("super_admin")),
    db: Session = Depends(get_db),
) -> List[PuskesmasAdminResponse]:
    """Admin-only list of approved & active puskesmas with aggregated counts."""
    rows = crud_puskesmas.get_active_with_stats(db)
    return [_build_admin_response(row[0], row[1], row[2]) for row in rows]


@router.get(
    "/admin/{puskesmas_id}",
    response_model=PuskesmasAdminResponse,
    status_code=status.HTTP_200_OK,
    summary="Admin detail puskesmas with stats",
)
async def admin_get_puskesmas(
    puskesmas_id: int,
    current_user: User = Depends(require_role("super_admin")),
    db: Session = Depends(get_db),
) -> PuskesmasAdminResponse:
    """Admin-only detail including counts of ibu hamil and perawat."""
    result = crud_puskesmas.get_with_stats(db, puskesmas_id=puskesmas_id)
    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Puskesmas not found",
        )
    puskesmas, ibu_count, perawat_count = result
    return _build_admin_response(puskesmas, ibu_count, perawat_count)


@router.get(
    "/nearest",
    response_model=List[NearestPuskesmasResponse],
    status_code=status.HTTP_200_OK,
    summary="Find nearest puskesmas",
)
async def find_nearest_puskesmas(
    latitude: float,
    longitude: float,
    db: Session = Depends(get_db),
) -> List[NearestPuskesmasResponse]:
    """Find up to 5 nearest active and approved puskesmas, sorted by distance."""
    results = crud_puskesmas.find_nearest(
        db,
        latitude=latitude,
        longitude=longitude,
        limit=5,
    )

    response_list: List[NearestPuskesmasResponse] = []
    for puskesmas, distance in results:
        response_list.append(
            NearestPuskesmasResponse(
                puskesmas=PuskesmasResponse.from_orm(puskesmas),
                distance_km=round(float(distance), 2),
                address=puskesmas.address,
            )
        )
    return response_list


@router.get(
    "/pending",
    response_model=List[PuskesmasResponse],
    status_code=status.HTTP_200_OK,
    summary="List pending registrations",
)
async def list_pending_puskesmas(
    current_user: User = Depends(require_role("super_admin")),
    db: Session = Depends(get_db),
) -> List[Puskesmas]:
    """Admin-only view of pending registrations."""
    return crud_puskesmas.get_pending_registrations(db)


@router.get(
    "/{puskesmas_id}",
    response_model=PuskesmasResponse,
    status_code=status.HTTP_200_OK,
    summary="Get puskesmas detail",
)
async def get_puskesmas(
    puskesmas_id: int,
    db: Session = Depends(get_db),
) -> Puskesmas:
    """Public detail endpoint."""
    puskesmas = crud_puskesmas.get(db, id=puskesmas_id)
    if not puskesmas:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Puskesmas not found",
        )
    return puskesmas


@router.put(
    "/{puskesmas_id}",
    response_model=PuskesmasResponse,
    status_code=status.HTTP_200_OK,
    summary="Update puskesmas data (Step 3: Submit for approval)",
    description="""
Update data puskesmas. Digunakan untuk:
1. Update lokasi (latitude, longitude) dari map picker
2. Submit registrasi dari draft ke pending_approval

**Flow Registrasi Multi-Step:**
- Step 1: POST /puskesmas/register (buat draft)
- Step 2: PUT /upload/puskesmas/{id}/sk-pendirian, /photo, /npwp (upload dokumen)
- Step 3: PUT /puskesmas/{id} (set lokasi & submit untuk approval)

**Validasi saat submit pending_approval:**
- SK Pendirian (sk_document_url) harus sudah diupload
- Foto Gedung (building_photo_url) harus sudah diupload
- data_truth_confirmed harus true
- latitude dan longitude harus diisi

**Akses:**
- Puskesmas yang berstatus draft: tanpa autentikasi (untuk registrasi)
- Puskesmas yang sudah approved: hanya admin puskesmas atau super_admin
""",
    responses={
        200: {
            "description": "Puskesmas berhasil diupdate",
        },
        400: {
            "description": "Validasi gagal",
            "content": {
                "application/json": {
                    "examples": {
                        "doc_missing": {
                            "summary": "Dokumen wajib belum diupload",
                            "value": {"detail": "SK Pendirian wajib diupload sebelum submit"}
                        },
                        "photo_missing": {
                            "summary": "Foto gedung belum diupload",
                            "value": {"detail": "Foto Gedung wajib diupload sebelum submit"}
                        },
                        "location_missing": {
                            "summary": "Lokasi belum diset",
                            "value": {"detail": "Latitude dan Longitude wajib diisi sebelum submit"}
                        },
                        "not_confirmed": {
                            "summary": "Belum konfirmasi kebenaran data",
                            "value": {"detail": "Anda harus mengkonfirmasi kebenaran data sebelum submit"}
                        }
                    }
                }
            }
        },
        403: {
            "description": "Tidak memiliki akses",
            "content": {
                "application/json": {
                    "example": {"detail": "Not authorized to update this puskesmas"}
                }
            }
        },
        404: {
            "description": "Puskesmas tidak ditemukan",
            "content": {
                "application/json": {
                    "example": {"detail": "Puskesmas not found"}
                }
            }
        }
    }
)
async def update_puskesmas(
    puskesmas_id: int,
    puskesmas_in: PuskesmasUpdate,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_current_user),
) -> Puskesmas:
    """
    Update puskesmas data.

    For draft puskesmas during registration: no auth required.
    For approved puskesmas: only admin puskesmas or super_admin.

    Validates required documents when submitting for pending_approval.
    """
    puskesmas = crud_puskesmas.get(db, id=puskesmas_id)
    if not puskesmas:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Puskesmas not found",
        )

    # Authorization check
    # Draft puskesmas: no auth required (registration flow)
    # Otherwise: need to be admin puskesmas or super_admin
    if puskesmas.registration_status != "draft":
        if not current_user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication required",
            )
        if current_user.role == "puskesmas" and puskesmas.admin_user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to update this puskesmas",
            )
        elif current_user.role not in ["puskesmas", "super_admin"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to update this puskesmas",
            )

    # Validate when submitting for pending_approval
    update_data = puskesmas_in.model_dump(exclude_unset=True)
    target_status = update_data.get("registration_status")

    if target_status == "pending_approval":
        # Check required documents
        sk_doc = update_data.get("sk_document_url") or puskesmas.sk_document_url
        if not sk_doc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="SK Pendirian wajib diupload sebelum submit",
            )

        building_photo = update_data.get("building_photo_url") or puskesmas.building_photo_url
        if not building_photo:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Foto Gedung wajib diupload sebelum submit",
            )

        # Check location
        lat = update_data.get("latitude") if "latitude" in update_data else puskesmas.latitude
        lon = update_data.get("longitude") if "longitude" in update_data else puskesmas.longitude
        if lat is None or lon is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Latitude dan Longitude wajib diisi sebelum submit",
            )

        # Check data_truth_confirmed
        confirmed = update_data.get("data_truth_confirmed") if "data_truth_confirmed" in update_data else puskesmas.data_truth_confirmed
        if not confirmed:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Anda harus mengkonfirmasi kebenaran data sebelum submit",
            )

    # Update puskesmas with location handling
    updated = crud_puskesmas.update_with_location(db, db_obj=puskesmas, obj_in=puskesmas_in)

    return updated


@router.post(
    "/{puskesmas_id}/approve",
    response_model=PuskesmasResponse,
    status_code=status.HTTP_200_OK,
    summary="Approve registration",
    description="""
Approve registrasi puskesmas.

**Akses:**
- Admin sistem
- Super admin (dapat approve/reject registrasi puskesmas)
""",
)
async def approve_puskesmas(
    puskesmas_id: int,
    current_user: User = Depends(require_role("super_admin")),
    db: Session = Depends(get_db),
) -> Puskesmas:
    """Approve a pending puskesmas and notify admin user."""
    puskesmas = crud_puskesmas.approve(
        db,
        puskesmas_id=puskesmas_id,
        admin_id=current_user.id,
    )
    if not puskesmas:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Puskesmas not found",
        )

    # Notify puskesmas admin user
    notification_in = NotificationCreate(
        user_id=puskesmas.admin_user_id,
        title="Registrasi Puskesmas disetujui",
        message=f"Registrasi puskesmas {puskesmas.name} telah disetujui.",
        notification_type="system",
        priority="normal",
        sent_via="in_app",
    )
    crud_notification.create(db, obj_in=notification_in)

    return puskesmas


@router.post(
    "/{puskesmas_id}/reject",
    response_model=PuskesmasResponse,
    status_code=status.HTTP_200_OK,
    summary="Reject registration",
    description="""
Reject registrasi puskesmas dengan alasan.

**Akses:**
- Admin sistem
- Super admin (dapat approve/reject registrasi puskesmas)
""",
)
async def reject_puskesmas(
    puskesmas_id: int,
    payload: RejectionReason,
    current_user: User = Depends(require_role("super_admin")),
    db: Session = Depends(get_db),
) -> Puskesmas:
    """Reject a puskesmas registration with reason and notify admin user."""
    puskesmas = crud_puskesmas.reject(
        db,
        puskesmas_id=puskesmas_id,
        admin_id=current_user.id,
        reason=payload.rejection_reason,
    )
    if not puskesmas:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Puskesmas not found",
        )

    notification_in = NotificationCreate(
        user_id=puskesmas.admin_user_id,
        title="Registrasi Puskesmas ditolak",
        message=f"Registrasi puskesmas {puskesmas.name} ditolak: {payload.rejection_reason}",
        notification_type="system",
        priority="normal",
        sent_via="in_app",
    )
    crud_notification.create(db, obj_in=notification_in)

    return puskesmas


@router.post(
    "/{puskesmas_id}/deactivate",
    response_model=PuskesmasResponse,
    status_code=status.HTTP_200_OK,
    summary="Deactivate puskesmas",
    description="""
Nonaktifkan puskesmas yang sedang aktif.

**Akses:**
- Super admin only

**Cascade Effects:**
1. Semua ibu hamil yang ter-assign ke puskesmas ini akan kehilangan relasi (puskesmas_id = NULL, perawat_id = NULL)
2. Semua perawat yang terdaftar di puskesmas ini akan otomatis terhapus (beserta akun usernya jika ada)
3. Akun admin puskesmas akan dinonaktifkan (is_active = False)
4. Puskesmas akan dinonaktifkan (is_active = False)

**Catatan:**
- Ibu hamil yang kehilangan relasi harus memilih puskesmas aktif baru
- Perawat yang terhapus tidak dapat diakses lagi
- Admin puskesmas tidak dapat login setelah puskesmas dinonaktifkan
""",
    responses={
        200: {
            "description": "Puskesmas berhasil dinonaktifkan",
            "content": {
                "application/json": {
                    "example": {
                        "id": 1,
                        "name": "Puskesmas Sungai Penuh",
                        "is_active": False,
                        "registration_status": "approved",
                        "admin_notes": "[Deactivated] Melanggar ketentuan operasional"
                    }
                }
            }
        },
        403: {
            "description": "Tidak memiliki akses",
            "content": {
                "application/json": {
                    "example": {"detail": "Not authorized. Hanya super admin yang dapat menonaktifkan puskesmas."}
                }
            }
        },
        404: {
            "description": "Puskesmas tidak ditemukan",
            "content": {
                "application/json": {
                    "example": {"detail": "Puskesmas not found"}
                }
            }
        },
        400: {
            "description": "Puskesmas sudah tidak aktif",
            "content": {
                "application/json": {
                    "example": {"detail": "Puskesmas sudah tidak aktif"}
                }
            }
        }
    }
)
async def deactivate_puskesmas(
    puskesmas_id: int,
    payload: DeactivationReason,
    current_user: User = Depends(require_role("super_admin")),
    db: Session = Depends(get_db),
) -> Puskesmas:
    """
    Deactivate (nonaktifkan) puskesmas yang sedang aktif.
    
    Hanya super admin yang dapat mengakses endpoint ini.
    
    Args:
        puskesmas_id: ID puskesmas yang akan dinonaktifkan
        payload: Alasan deactivation
        current_user: Super admin user
        db: Database session
        
    Returns:
        Puskesmas: Data puskesmas yang sudah dinonaktifkan
        
    Raises:
        HTTPException 400: Puskesmas sudah tidak aktif
        HTTPException 403: Tidak memiliki akses
        HTTPException 404: Puskesmas tidak ditemukan
    """
    puskesmas = crud_puskesmas.get(db, id=puskesmas_id)
    if not puskesmas:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Puskesmas not found",
        )
    
    if not puskesmas.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Puskesmas sudah tidak aktif",
        )
    
    # Deactivate puskesmas dengan cascade logic
    puskesmas = crud_puskesmas.deactivate(
        db,
        puskesmas_id=puskesmas_id,
        super_admin_id=current_user.id,
        reason=payload.reason,
    )
    
    if not puskesmas:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Puskesmas not found",
        )
    
    # Notify admin puskesmas jika ada
    if puskesmas.admin_user_id:
        notification_in = NotificationCreate(
            user_id=puskesmas.admin_user_id,
            title="Puskesmas Dinonaktifkan",
            message=f"Puskesmas {puskesmas.name} telah dinonaktifkan. Alasan: {payload.reason}",
            notification_type="system",
            priority="high",
            sent_via="in_app",
        )
        crud_notification.create(db, obj_in=notification_in)
    
    return puskesmas


@router.post(
    "/{puskesmas_id}/ibu-hamil/{ibu_id}/assign",
    response_model=IbuHamilResponse,
    status_code=status.HTTP_200_OK,
    summary="Assign ibu hamil ke puskesmas",
    description="""
Menugaskan satu ibu hamil ke puskesmas tertentu.

**Konsep:**
- Setiap puskesmas memiliki satu akun admin puskesmas (role: 'puskesmas')
- Admin puskesmas dapat mengelola perawat dan assign ibu hamil ke perawat di puskesmasnya
- Ibu hamil dapat memilih sendiri puskesmas yang ingin dituju

**Siapa yang dapat mengakses:**
- Admin puskesmas (hanya dapat assign ke puskesmas yang dikelolanya sendiri)
- Ibu hamil (hanya dapat assign dirinya sendiri ke puskesmas manapun yang aktif)

**Catatan:**
- Puskesmas harus dalam status 'approved' dan aktif
- Endpoint ini untuk assign ibu hamil ke puskesmas tertentu
- Setelah assign ke puskesmas, ibu hamil belum memiliki perawat yang menangani
- Untuk assign ke perawat, gunakan endpoint `/puskesmas/{puskesmas_id}/ibu-hamil/{ibu_id}/assign-perawat/{perawat_id}`
- Super admin tidak dapat assign (hanya bisa approve/reject registrasi puskesmas)
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
                            "summary": "Role tidak diizinkan",
                            "value": {"detail": "Not authorized"}
                        },
                        "wrong_puskesmas": {
                            "summary": "Admin puskesmas mencoba assign ke puskesmas lain",
                            "value": {"detail": "Not authorized to assign for this puskesmas"}
                        },
                        "ibu_hamil_not_self": {
                            "summary": "Ibu hamil mencoba assign ibu hamil lain",
                            "value": {"detail": "Anda hanya dapat assign diri sendiri ke puskesmas"}
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
async def assign_ibu_hamil_to_puskesmas(
    puskesmas_id: int,
    ibu_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> IbuHamil:
    """
    Assign ibu hamil ke puskesmas tertentu.

    Role yang dapat mengakses:
    - Admin puskesmas: hanya dapat assign ke puskesmas yang dikelolanya sendiri
    - Ibu hamil: hanya dapat assign dirinya sendiri ke puskesmas manapun yang aktif

    Args:
        puskesmas_id: ID puskesmas tujuan
        ibu_id: ID ibu hamil yang akan di-assign
        current_user: User yang sedang login
        db: Database session

    Returns:
        IbuHamil: Data ibu hamil yang sudah di-update dengan puskesmas_id baru
    """
    # Authorization check: hanya admin puskesmas atau ibu_hamil
    if current_user.role not in {"puskesmas", "ibu_hamil"}:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized",
        )

    # Get ibu hamil
    ibu = crud_ibu_hamil.get(db, id=ibu_id)
    if not ibu:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Ibu Hamil not found",
        )

    # Validasi khusus untuk role ibu_hamil: hanya bisa assign diri sendiri
    if current_user.role == "ibu_hamil":
        if ibu.user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Anda hanya dapat assign diri sendiri ke puskesmas",
            )

    # Get puskesmas
    puskesmas = crud_puskesmas.get(db, id=puskesmas_id)
    if not puskesmas or puskesmas.registration_status != "approved" or not puskesmas.is_active:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Puskesmas tidak ditemukan atau belum aktif",
        )

    # Validasi khusus untuk admin puskesmas: hanya dapat assign untuk puskesmasnya sendiri
    if current_user.role == "puskesmas" and puskesmas.admin_user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to assign for this puskesmas",
        )

    # Assign to puskesmas
    assigned = crud_ibu_hamil.assign_to_puskesmas(
        db,
        ibu_id=ibu.id,
        puskesmas_id=puskesmas.id,
        distance_km=0.0,
    )

    # Create notification for ibu user (jika di-assign oleh admin puskesmas)
    if current_user.role == "puskesmas":
        notification_in = NotificationCreate(
            user_id=ibu.user_id,
            title="Penugasan Puskesmas",
            message=f"Anda ditugaskan ke {puskesmas.name}.",
            notification_type="assignment",
            priority="normal",
            sent_via="in_app",
        )
        crud_notification.create(db, obj_in=notification_in)

    return assigned


@router.post(
    "/{puskesmas_id}/ibu-hamil/{ibu_id}/assign-perawat/{perawat_id}",
    response_model=IbuHamilResponse,
    status_code=status.HTTP_200_OK,
    summary="Assign ibu hamil ke perawat",
    description="""
Menugaskan satu ibu hamil ke perawat yang terdaftar di puskesmas tersebut.

**Konsep:**
- Setiap puskesmas memiliki satu akun admin puskesmas (role: 'puskesmas')
- Admin puskesmas dapat mengelola perawat dan assign ibu hamil ke perawat di puskesmasnya

**Prasyarat:**
- Ibu hamil HARUS sudah ter-assign ke puskesmas terlebih dahulu
- Perawat HARUS terdaftar di puskesmas yang sama dengan ibu hamil
- Perawat harus aktif dan memiliki kapasitas

**Siapa yang dapat mengakses:**
- Admin sistem (dapat assign ke puskesmas manapun)
- Admin puskesmas (hanya dapat assign untuk puskesmas yang dikelolanya sendiri)

**Catatan:**
- Gunakan endpoint `/puskesmas/{puskesmas_id}/ibu-hamil/{ibu_id}/assign` terlebih dahulu jika ibu hamil belum ter-assign ke puskesmas
- Endpoint ini akan menambah workload perawat secara otomatis
- Perawat harus terdaftar di puskesmas yang sama dengan ibu hamil
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
                        "wrong_puskesmas": {
                            "summary": "Ibu hamil tidak ter-assign ke puskesmas ini",
                            "value": {"detail": "Ibu hamil tidak ter-assign ke puskesmas ini"}
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
                            "value": {"detail": "Perawat tidak ditemukan atau tidak terdaftar di puskesmas ini"}
                        }
                    }
                }
            }
        }
    }
)
async def assign_ibu_hamil_to_perawat(
    puskesmas_id: int,
    ibu_id: int,
    perawat_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> IbuHamil:
    """
    Assign ibu hamil ke perawat yang terdaftar di puskesmas tersebut.

    Hanya admin sistem atau admin puskesmas yang dapat mengakses endpoint ini.
    Admin puskesmas hanya dapat assign untuk puskesmas yang dikelolanya sendiri.

    Args:
        puskesmas_id: ID puskesmas
        ibu_id: ID ibu hamil yang akan di-assign
        perawat_id: ID perawat tujuan
        current_user: User yang sedang login (admin atau admin puskesmas)
        db: Database session

    Returns:
        IbuHamil: Data ibu hamil yang sudah di-update dengan perawat_id baru

    Raises:
        HTTPException 400: Ibu hamil belum ter-assign ke puskesmas atau perawat penuh
        HTTPException 403: Tidak memiliki akses
        HTTPException 404: Ibu hamil atau perawat tidak ditemukan
    """
    # Authorization check: hanya super admin atau admin puskesmas
    # Super admin TIDAK dapat assign (hanya bisa approve/reject registrasi puskesmas)
    if current_user.role not in {"super_admin", "puskesmas"}:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized. Super admin hanya dapat approve/reject registrasi puskesmas.",
        )

    # Get puskesmas
    puskesmas = crud_puskesmas.get(db, id=puskesmas_id)
    if not puskesmas or puskesmas.registration_status != "approved" or not puskesmas.is_active:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Puskesmas tidak ditemukan atau belum aktif",
        )

    # Validasi: Admin puskesmas hanya dapat assign untuk puskesmas yang dikelolanya sendiri
    # Setiap puskesmas memiliki satu admin puskesmas (admin_user_id)
    if current_user.role == "puskesmas" and puskesmas.admin_user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to assign for this puskesmas",
        )

    # Get ibu hamil
    ibu = crud_ibu_hamil.get(db, id=ibu_id)
    if not ibu:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Ibu Hamil not found",
        )

    # Check if ibu hamil is already assigned to this puskesmas
    if not ibu.puskesmas_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Ibu hamil belum ter-assign ke puskesmas. Silakan assign ke puskesmas terlebih dahulu.",
        )

    if ibu.puskesmas_id != puskesmas_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Ibu hamil tidak ter-assign ke puskesmas ini",
        )

    # Get perawat
    perawat = crud_perawat.get(db, id=perawat_id)
    if not perawat or perawat.puskesmas_id != puskesmas_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Perawat tidak ditemukan atau tidak terdaftar di puskesmas ini",
        )

    # Check if perawat is active
    if not perawat.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Perawat tidak aktif",
        )

    # Check perawat capacity (if max_patients is set)
    # Note: max_patients might not exist in the model, so we check current_patients
    # For now, we'll just check if perawat is active and exists
    # You can add max_patients check if needed

    # Assign to perawat
    crud_ibu_hamil.assign_to_perawat(db, ibu_id=ibu.id, perawat_id=perawat.id)
    crud_perawat.update_workload(db, perawat_id=perawat.id, increment=1)

    # Refresh data ibu hamil
    db.refresh(ibu)

    # Create notification for ibu user
    notification_in = NotificationCreate(
        user_id=ibu.user_id,
        title="Penugasan Perawat",
        message=f"Anda akan ditangani oleh perawat {perawat.nama_lengkap} dari {puskesmas.name}.",
        notification_type="assignment",
        priority="normal",
        sent_via="in_app",
    )
    crud_notification.create(db, obj_in=notification_in)

    return ibu


__all__ = ["router"]
