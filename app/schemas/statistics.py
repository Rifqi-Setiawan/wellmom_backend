"""Statistics schemas for dashboard data."""

from pydantic import BaseModel, Field


class PlatformStatisticsResponse(BaseModel):
    """Response schema for platform statistics."""
    
    # Puskesmas statistics
    total_puskesmas_active: int = Field(..., description="Total puskesmas yang aktif")
    total_puskesmas_pending: int = Field(..., description="Total puskesmas yang pending approval")
    total_puskesmas_approved: int = Field(..., description="Total puskesmas yang sudah approved")
    total_puskesmas_rejected: int = Field(..., description="Total puskesmas yang ditolak")
    total_puskesmas_draft: int = Field(..., description="Total puskesmas yang masih draft")
    
    # Perawat statistics
    total_perawat: int = Field(..., description="Total perawat yang terdaftar")
    total_perawat_active: int = Field(..., description="Total perawat yang aktif")
    
    # Ibu Hamil statistics
    total_ibu_hamil: int = Field(..., description="Total ibu hamil yang terdaftar")
    total_ibu_hamil_active: int = Field(..., description="Total ibu hamil yang aktif")
    total_ibu_hamil_risk_low: int = Field(..., description="Total ibu hamil dengan risiko rendah")
    total_ibu_hamil_risk_normal: int = Field(..., description="Total ibu hamil dengan risiko normal")
    total_ibu_hamil_risk_high: int = Field(..., description="Total ibu hamil dengan risiko tinggi")
