"""Health Record endpoints."""

from datetime import date, timedelta
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status, Query, Path
from sqlalchemy.orm import Session

from app.api.deps import get_current_active_user, get_db, require_role
from app.crud import crud_health_record, crud_ibu_hamil, crud_perawat
from app.models.user import User
from app.models.ibu_hamil import IbuHamil
from app.schemas.health_record import (
    HealthRecordResponse,
    HealthRecordListResponse,
    HealthRecordLast7DaysResponse,
)

router = APIRouter(
    prefix="/health-records",
    tags=["Health Records"],
)


def _get_ibu_hamil_by_user_id(db: Session, user_id: int) -> IbuHamil:
    """Get IbuHamil by user_id."""
    ibu_hamil = crud_ibu_hamil.get_by_field(db, "user_id", user_id)
    if not ibu_hamil:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Profil ibu hamil tidak ditemukan."
        )
    return ibu_hamil


def _authorize_access(
    db: Session,
    ibu_hamil_id: int,
    current_user: User
) -> None:
    """Verify that current user has access to this ibu_hamil's health records."""
    if current_user.role == "ibu_hamil":
        ibu_hamil = _get_ibu_hamil_by_user_id(db, current_user.id)
        if ibu_hamil.id != ibu_hamil_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Anda tidak memiliki akses ke health records ini."
            )
    elif current_user.role == "perawat":
        perawat = crud_perawat.get_by_field(db, "user_id", current_user.id)
        if not perawat:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Profil perawat tidak ditemukan."
            )
        # Check if ibu_hamil is assigned to this perawat
        ibu_hamil = crud_ibu_hamil.get(db, ibu_hamil_id)
        if not ibu_hamil or ibu_hamil.perawat_id != perawat.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Ibu hamil ini tidak ter-assign ke Anda."
            )
    elif current_user.role == "super_admin":
        # Super admin can view all (read-only)
        pass
    else:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Anda tidak memiliki akses ke health records."
        )


@router.get(
    "/ibu-hamil/{ibu_hamil_id}/by-date",
    response_model=HealthRecordListResponse,
    status_code=status.HTTP_200_OK,
    summary="Get health records by date",
    description="""
    Get all health records for a specific ibu hamil on a specific date.
    
    **Access:**
    - Ibu Hamil: Can only access their own records
    - Perawat: Can access records of assigned ibu hamil
    - Super Admin: Can access all records (read-only)
    """,
)
def get_health_records_by_date(
    ibu_hamil_id: int,
    checkup_date: date = Query(..., description="Date to filter health records (YYYY-MM-DD)"),
    current_user: User = Depends(require_role("ibu_hamil", "perawat", "super_admin")),
    db: Session = Depends(get_db),
) -> HealthRecordListResponse:
    """Get health records by date."""
    _authorize_access(db, ibu_hamil_id, current_user)
    
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
    - Perawat: Can access records of assigned ibu hamil
    - Super Admin: Can access all records (read-only)
    """,
)
def get_health_records_last_7_days(
    ibu_hamil_id: int,
    category: str = Path(
        ...,
        description="Category filter: blood_pressure, blood_glucose, temperature, or heart_rate",
        regex="^(blood_pressure|blood_glucose|temperature|heart_rate)$"
    ),
    current_user: User = Depends(require_role("ibu_hamil", "perawat", "super_admin")),
    db: Session = Depends(get_db),
) -> HealthRecordLast7DaysResponse:
    """Get health records from last 7 days by category."""
    _authorize_access(db, ibu_hamil_id, current_user)
    
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
    - Perawat: Can access records of assigned ibu hamil
    - Super Admin: Can access all records (read-only)
    """,
)
def get_all_health_records(
    ibu_hamil_id: int,
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(50, ge=1, le=100, description="Maximum number of records to return"),
    current_user: User = Depends(require_role("ibu_hamil", "perawat", "super_admin")),
    db: Session = Depends(get_db),
) -> HealthRecordListResponse:
    """Get all health records for an ibu hamil."""
    _authorize_access(db, ibu_hamil_id, current_user)
    
    records = crud_health_record.get_by_ibu_hamil(
        db, ibu_hamil_id=ibu_hamil_id, limit=limit
    )
    
    # Apply pagination
    paginated_records = records[skip:skip + limit]
    
    return HealthRecordListResponse(
        records=[HealthRecordResponse.model_validate(record) for record in paginated_records],
        total=len(records)
    )
