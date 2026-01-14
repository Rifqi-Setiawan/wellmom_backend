"""Statistics endpoints for dashboard data."""

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.puskesmas import Puskesmas
from app.models.perawat import Perawat
from app.models.ibu_hamil import IbuHamil
from app.schemas.statistics import PlatformStatisticsResponse
from app.api.deps import get_current_active_user, require_role
from app.models.user import User

router = APIRouter(prefix="/statistics", tags=["Statistics"])


@router.get(
    "/platform",
    response_model=PlatformStatisticsResponse,
    summary="Get Platform Statistics",
    description="Get statistics for puskesmas, perawat, and ibu hamil. Only accessible by super_admin."
)
def get_platform_statistics(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("super_admin"))
) -> PlatformStatisticsResponse:
    """
    Get platform-wide statistics including:
    - Total puskesmas (active, pending, approved, rejected, draft)
    - Total perawat (registered, active)
    - Total ibu hamil (registered, active, by risk level)
    """
    
    # ===== PUSKESMAS STATISTICS =====
    # Total active puskesmas
    total_puskesmas_active = db.scalar(
        select(func.count(Puskesmas.id)).where(Puskesmas.is_active == True)
    ) or 0
    
    # Total pending approval
    total_puskesmas_pending = db.scalar(
        select(func.count(Puskesmas.id)).where(Puskesmas.registration_status == "pending_approval")
    ) or 0
    
    # Total approved
    total_puskesmas_approved = db.scalar(
        select(func.count(Puskesmas.id)).where(Puskesmas.registration_status == "approved")
    ) or 0
    
    # Total rejected
    total_puskesmas_rejected = db.scalar(
        select(func.count(Puskesmas.id)).where(Puskesmas.registration_status == "rejected")
    ) or 0
    
    # Total draft
    total_puskesmas_draft = db.scalar(
        select(func.count(Puskesmas.id)).where(Puskesmas.registration_status == "draft")
    ) or 0
    
    # ===== PERAWAT STATISTICS =====
    # Total registered perawat
    total_perawat = db.scalar(
        select(func.count(Perawat.id))
    ) or 0
    
    # Total active perawat
    total_perawat_active = db.scalar(
        select(func.count(Perawat.id)).where(Perawat.is_active == True)
    ) or 0
    
    # ===== IBU HAMIL STATISTICS =====
    # Total registered ibu hamil
    total_ibu_hamil = db.scalar(
        select(func.count(IbuHamil.id))
    ) or 0
    
    # Total active ibu hamil
    total_ibu_hamil_active = db.scalar(
        select(func.count(IbuHamil.id)).where(IbuHamil.is_active == True)
    ) or 0
    
    # By risk level
    total_ibu_hamil_risk_low = db.scalar(
        select(func.count(IbuHamil.id)).where(IbuHamil.risk_level == "low")
    ) or 0
    
    total_ibu_hamil_risk_normal = db.scalar(
        select(func.count(IbuHamil.id)).where(IbuHamil.risk_level == "normal")
    ) or 0
    
    total_ibu_hamil_risk_high = db.scalar(
        select(func.count(IbuHamil.id)).where(IbuHamil.risk_level == "high")
    ) or 0
    
    return PlatformStatisticsResponse(
        total_puskesmas_active=total_puskesmas_active,
        total_puskesmas_pending=total_puskesmas_pending,
        total_puskesmas_approved=total_puskesmas_approved,
        total_puskesmas_rejected=total_puskesmas_rejected,
        total_puskesmas_draft=total_puskesmas_draft,
        total_perawat=total_perawat,
        total_perawat_active=total_perawat_active,
        total_ibu_hamil=total_ibu_hamil,
        total_ibu_hamil_active=total_ibu_hamil_active,
        total_ibu_hamil_risk_low=total_ibu_hamil_risk_low,
        total_ibu_hamil_risk_normal=total_ibu_hamil_risk_normal,
        total_ibu_hamil_risk_high=total_ibu_hamil_risk_high,
    )
