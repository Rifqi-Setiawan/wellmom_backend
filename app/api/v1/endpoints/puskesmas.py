"""Puskesmas endpoints."""

from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_db, require_role
from app.crud import crud_notification, crud_puskesmas, crud_user
from app.models.puskesmas import Puskesmas
from app.models.user import User
from app.schemas.notification import NotificationCreate
from app.schemas.puskesmas import PuskesmasAdminResponse, PuskesmasCreate, PuskesmasResponse
from app.schemas.user import UserCreate

router = APIRouter(
    prefix="/puskesmas",
    tags=["Puskesmas"],
)


class RejectionReason(BaseModel):
    rejection_reason: str


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
        admin_notes=puskesmas.admin_notes,
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
    """Public registration for Puskesmas. Creates linked user with role 'puskesmas'."""
    # Prevent duplicate phone on user table
    existing_user = crud_user.get_by_phone(db, phone=puskesmas_in.phone)
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Phone already registered",
        )

    # Create associated user (temporary password uses kepala_nip)
    user_data = UserCreate(
        phone=puskesmas_in.phone,
        password=puskesmas_in.kepala_nip,
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
    "/admin/active",
    response_model=List[PuskesmasAdminResponse],
    status_code=status.HTTP_200_OK,
    summary="Admin list active puskesmas with stats",
)
async def admin_list_active_puskesmas(
    current_user: User = Depends(require_role("admin")),
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
    current_user: User = Depends(require_role("admin")),
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
    current_user: User = Depends(require_role("admin")),
    db: Session = Depends(get_db),
) -> List[Puskesmas]:
    """Admin-only view of pending registrations."""
    return crud_puskesmas.get_pending_registrations(db)


@router.post(
    "/{puskesmas_id}/approve",
    response_model=PuskesmasResponse,
    status_code=status.HTTP_200_OK,
    summary="Approve registration",
)
async def approve_puskesmas(
    puskesmas_id: int,
    current_user: User = Depends(require_role("admin")),
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
)
async def reject_puskesmas(
    puskesmas_id: int,
    payload: RejectionReason,
    current_user: User = Depends(require_role("admin")),
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


__all__ = ["router"]
