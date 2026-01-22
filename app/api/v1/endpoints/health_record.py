"""Health Record endpoints."""

from datetime import date, timedelta
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status, Query, Path
from sqlalchemy.orm import Session

from app.api.deps import get_current_active_user, get_db, require_role
from app.crud import crud_health_record, crud_ibu_hamil, crud_perawat, crud_puskesmas
from app.models.user import User
from app.models.ibu_hamil import IbuHamil
from app.schemas.health_record import (
    HealthRecordCreate,
    HealthRecordUpdate,
    HealthRecordResponse,
    HealthRecordListResponse,
    HealthRecordLast7DaysResponse,
)

router = APIRouter(
    prefix="/health-records",
    tags=["Health Records"],
)

# Allowed roles for health records access
ALLOWED_ROLES = ("ibu_hamil", "perawat", "puskesmas", "super_admin")
# Roles that can create/update/delete health records
WRITE_ROLES = ("perawat", "puskesmas", "super_admin")


def _get_ibu_hamil_by_user_id(db: Session, user_id: int) -> IbuHamil:
    """Get IbuHamil by user_id."""
    ibu_hamil = crud_ibu_hamil.get_by_field(db, "user_id", user_id)
    if not ibu_hamil:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Profil ibu hamil tidak ditemukan."
        )
    return ibu_hamil


def _authorize_read_access(
    db: Session,
    ibu_hamil_id: int,
    current_user: User
) -> None:
    """Verify that current user has read access to this ibu_hamil's health records.

    Access rules:
    - Ibu Hamil: Can only access their own records
    - Perawat: Can access all ibu hamil records
    - Puskesmas: Can access all ibu hamil records
    - Super Admin: Can access all records
    """
    # Verify ibu_hamil exists
    ibu_hamil = crud_ibu_hamil.get(db, ibu_hamil_id)
    if not ibu_hamil:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Ibu hamil tidak ditemukan."
        )

    if current_user.role == "ibu_hamil":
        user_ibu_hamil = _get_ibu_hamil_by_user_id(db, current_user.id)
        if user_ibu_hamil.id != ibu_hamil_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Anda tidak memiliki akses ke health records ini."
            )
    elif current_user.role == "perawat":
        # All perawat can access any ibu_hamil's health records
        perawat = crud_perawat.get_by_field(db, "user_id", current_user.id)
        if not perawat:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Profil perawat tidak ditemukan."
            )
    elif current_user.role == "puskesmas":
        # Puskesmas can access all health records
        puskesmas = crud_puskesmas.get_by_field(db, "user_id", current_user.id)
        if not puskesmas:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Profil puskesmas tidak ditemukan."
            )
    elif current_user.role == "super_admin":
        # Super admin can access all records
        pass
    else:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Anda tidak memiliki akses ke health records."
        )


def _authorize_write_access(
    db: Session,
    ibu_hamil_id: int,
    current_user: User
) -> Optional[int]:
    """Verify that current user has write access to this ibu_hamil's health records.

    Returns perawat_id if current user is a perawat, None otherwise.

    Access rules:
    - Perawat: Can create/update/delete health records for any ibu hamil
    - Puskesmas: Can create/update/delete health records for any ibu hamil
    - Super Admin: Can create/update/delete all records
    """
    # Verify ibu_hamil exists
    ibu_hamil = crud_ibu_hamil.get(db, ibu_hamil_id)
    if not ibu_hamil:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Ibu hamil tidak ditemukan."
        )

    perawat_id = None

    if current_user.role == "perawat":
        perawat = crud_perawat.get_by_field(db, "user_id", current_user.id)
        if not perawat:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Profil perawat tidak ditemukan."
            )
        perawat_id = perawat.id
    elif current_user.role == "puskesmas":
        puskesmas = crud_puskesmas.get_by_field(db, "user_id", current_user.id)
        if not puskesmas:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Profil puskesmas tidak ditemukan."
            )
    elif current_user.role == "super_admin":
        pass
    else:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Anda tidak memiliki akses untuk mengubah health records."
        )

    return perawat_id


# ==================== CREATE ====================

@router.post(
    "/",
    response_model=HealthRecordResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new health record",
    description="""
    Create a new health record for an ibu hamil.

    **Required fields:**
    - ibu_hamil_id: ID of the ibu hamil
    - checkup_date: Date of checkup (YYYY-MM-DD)
    - checked_by: Who performed the check ('perawat' or 'mandiri')
    - blood_pressure_systolic: Systolic blood pressure
    - blood_pressure_diastolic: Diastolic blood pressure
    - heart_rate: Heart rate (bpm)
    - body_temperature: Body temperature (Celsius)
    - weight: Weight in kg
    - complaints: Complaints/keluhan

    **Optional fields:**
    - hemoglobin, blood_glucose, protein_urin, upper_arm_circumference, fundal_height, fetal_heart_rate, notes

    **Access:**
    - Perawat: Can create health records for any ibu hamil
    - Puskesmas: Can create health records for any ibu hamil
    - Super Admin: Can create all records
    """,
)
def create_health_record(
    health_record_in: HealthRecordCreate,
    current_user: User = Depends(require_role(*WRITE_ROLES)),
    db: Session = Depends(get_db),
) -> HealthRecordResponse:
    """Create a new health record."""
    perawat_id = _authorize_write_access(db, health_record_in.ibu_hamil_id, current_user)

    # If perawat_id is not provided in request but user is perawat, use their perawat_id
    create_data = health_record_in.model_dump()
    if perawat_id and not create_data.get("perawat_id"):
        create_data["perawat_id"] = perawat_id

    # Create schema with updated data
    health_record_create = HealthRecordCreate(**create_data)

    record = crud_health_record.create(db, obj_in=health_record_create)
    return HealthRecordResponse.model_validate(record)


# ==================== READ ====================

@router.get(
    "/{record_id}",
    response_model=HealthRecordResponse,
    status_code=status.HTTP_200_OK,
    summary="Get health record by ID",
    description="""
    Get a specific health record by its ID.

    **Access:**
    - Ibu Hamil: Can only access their own records
    - Perawat: Can access all health records
    - Puskesmas: Can access all health records
    - Super Admin: Can access all records
    """,
)
def get_health_record(
    record_id: int = Path(..., description="Health record ID"),
    current_user: User = Depends(require_role(*ALLOWED_ROLES)),
    db: Session = Depends(get_db),
) -> HealthRecordResponse:
    """Get health record by ID."""
    record = crud_health_record.get(db, record_id)
    if not record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Health record tidak ditemukan."
        )

    _authorize_read_access(db, record.ibu_hamil_id, current_user)
    return HealthRecordResponse.model_validate(record)


@router.get(
    "/ibu-hamil/{ibu_hamil_id}/by-date",
    response_model=HealthRecordListResponse,
    status_code=status.HTTP_200_OK,
    summary="Get health records by date",
    description="""
    Get all health records for a specific ibu hamil on a specific date.

    **Access:**
    - Ibu Hamil: Can only access their own records
    - Perawat: Can access all health records
    - Puskesmas: Can access all health records
    - Super Admin: Can access all records
    """,
)
def get_health_records_by_date(
    ibu_hamil_id: int,
    checkup_date: date = Query(..., description="Date to filter health records (YYYY-MM-DD)"),
    current_user: User = Depends(require_role(*ALLOWED_ROLES)),
    db: Session = Depends(get_db),
) -> HealthRecordListResponse:
    """Get health records by date."""
    _authorize_read_access(db, ibu_hamil_id, current_user)

    records = crud_health_record.get_by_date(
        db, ibu_hamil_id=ibu_hamil_id, checkup_date=checkup_date
    )

    return HealthRecordListResponse(
        records=[HealthRecordResponse.model_validate(record) for record in records],
        total=len(records)
    )


@router.get(
    "/ibu-hamil/{ibu_hamil_id}/last-7-days/{category}",
    response_model=HealthRecordLast7DaysResponse,
    status_code=status.HTTP_200_OK,
    summary="Get health records last 7 days by category",
    description="""
    Get health records from the last 7 days (including today) filtered by category.

    **Categories:**
    - `blood_pressure`: Returns records with blood pressure (systolic or diastolic)
    - `blood_glucose`: Returns records with blood glucose
    - `temperature`: Returns records with body temperature
    - `heart_rate`: Returns records with heart rate

    **Access:**
    - Ibu Hamil: Can only access their own records
    - Perawat: Can access all health records
    - Puskesmas: Can access all health records
    - Super Admin: Can access all records
    """,
)
def get_health_records_last_7_days(
    ibu_hamil_id: int,
    category: str = Path(
        ...,
        description="Category filter: blood_pressure, blood_glucose, temperature, or heart_rate",
        pattern="^(blood_pressure|blood_glucose|temperature|heart_rate)$"
    ),
    current_user: User = Depends(require_role(*ALLOWED_ROLES)),
    db: Session = Depends(get_db),
) -> HealthRecordLast7DaysResponse:
    """Get health records from last 7 days by category."""
    _authorize_read_access(db, ibu_hamil_id, current_user)

    # Validate category
    valid_categories = {"blood_pressure", "blood_glucose", "temperature", "heart_rate"}
    if category not in valid_categories:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid category. Must be one of: {', '.join(valid_categories)}"
        )

    # Get records
    records = crud_health_record.get_last_7_days_by_category(
        db, ibu_hamil_id=ibu_hamil_id, category=category
    )

    # Calculate date range
    end_date = date.today()
    start_date = end_date - timedelta(days=6)

    return HealthRecordLast7DaysResponse(
        category=category,
        records=[HealthRecordResponse.model_validate(record) for record in records],
        total=len(records),
        start_date=start_date,
        end_date=end_date
    )


@router.get(
    "/ibu-hamil/{ibu_hamil_id}",
    response_model=HealthRecordListResponse,
    status_code=status.HTTP_200_OK,
    summary="Get all health records",
    description="""
    Get all health records for a specific ibu hamil.

    **Access:**
    - Ibu Hamil: Can only access their own records
    - Perawat: Can access all health records
    - Puskesmas: Can access all health records
    - Super Admin: Can access all records
    """,
)
def get_all_health_records(
    ibu_hamil_id: int,
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(50, ge=1, le=100, description="Maximum number of records to return"),
    current_user: User = Depends(require_role(*ALLOWED_ROLES)),
    db: Session = Depends(get_db),
) -> HealthRecordListResponse:
    """Get all health records for an ibu hamil."""
    _authorize_read_access(db, ibu_hamil_id, current_user)

    records = crud_health_record.get_by_ibu_hamil(
        db, ibu_hamil_id=ibu_hamil_id, limit=limit
    )

    # Apply pagination
    paginated_records = records[skip:skip + limit]

    return HealthRecordListResponse(
        records=[HealthRecordResponse.model_validate(record) for record in paginated_records],
        total=len(records)
    )


# ==================== UPDATE ====================

@router.put(
    "/{record_id}",
    response_model=HealthRecordResponse,
    status_code=status.HTTP_200_OK,
    summary="Update a health record",
    description="""
    Update an existing health record.

    **Access:**
    - Perawat: Can update any health record
    - Puskesmas: Can update any health record
    - Super Admin: Can update all records
    """,
)
def update_health_record(
    record_id: int,
    health_record_in: HealthRecordUpdate,
    current_user: User = Depends(require_role(*WRITE_ROLES)),
    db: Session = Depends(get_db),
) -> HealthRecordResponse:
    """Update a health record."""
    record = crud_health_record.get(db, record_id)
    if not record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Health record tidak ditemukan."
        )

    _authorize_write_access(db, record.ibu_hamil_id, current_user)

    updated_record = crud_health_record.update(db, db_obj=record, obj_in=health_record_in)
    return HealthRecordResponse.model_validate(updated_record)


# ==================== DELETE ====================

@router.delete(
    "/{record_id}",
    status_code=status.HTTP_200_OK,
    summary="Delete a health record",
    description="""
    Delete a health record.

    **Access:**
    - Perawat: Can delete any health record
    - Puskesmas: Can delete any health record
    - Super Admin: Can delete all records
    """,
)
def delete_health_record(
    record_id: int,
    current_user: User = Depends(require_role(*WRITE_ROLES)),
    db: Session = Depends(get_db),
) -> dict:
    """Delete a health record."""
    record = crud_health_record.get(db, record_id)
    if not record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Health record tidak ditemukan."
        )

    _authorize_write_access(db, record.ibu_hamil_id, current_user)

    crud_health_record.remove(db, id=record_id)
    return {"message": "Health record berhasil dihapus.", "id": record_id}
