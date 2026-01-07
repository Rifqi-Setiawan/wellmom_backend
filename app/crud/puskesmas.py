"""CRUD operations for `Puskesmas` model."""

from __future__ import annotations

from datetime import datetime
from typing import List, Optional, Tuple

from geoalchemy2.functions import ST_Distance, ST_GeogFromText
from sqlalchemy import select, func
from sqlalchemy.orm import Session

from app.crud.base import CRUDBase
from app.models.puskesmas import Puskesmas
from app.models.ibu_hamil import IbuHamil
from app.models.perawat import Perawat
from app.schemas.puskesmas import PuskesmasCreate, PuskesmasUpdate


class CRUDPuskesmas(CRUDBase[Puskesmas, PuskesmasCreate, PuskesmasUpdate]):
    def create_with_location(self, db: Session, *, puskesmas_in: PuskesmasCreate) -> Puskesmas:
        """Create Puskesmas and fill PostGIS location from latitude/longitude."""
        puskesmas_data = puskesmas_in.model_dump(exclude_unset=True)

        lat = puskesmas_data.get("latitude")
        lon = puskesmas_data.get("longitude")
        location_geog = None
        if lat is not None and lon is not None:
            location_wkt = f"POINT({lon} {lat})"
            location_geog = ST_GeogFromText(location_wkt)

        db_obj = Puskesmas(**puskesmas_data, location=location_geog)
        try:
            db.add(db_obj)
            db.commit()
            db.refresh(db_obj)
        except Exception:
            db.rollback()
            raise
        return db_obj

    def get_pending_registrations(self, db: Session) -> List[Puskesmas]:
        """Get all Puskesmas with pending registration status."""
        stmt = select(Puskesmas).where(Puskesmas.registration_status == "pending_approval")
        return db.scalars(stmt).all()

    def approve(self, db: Session, *, puskesmas_id: int, admin_id: int) -> Optional[Puskesmas]:
        """Approve a Puskesmas registration."""
        puskesmas = self.get(db, puskesmas_id)
        if not puskesmas:
            return None
        
        puskesmas.registration_status = "approved"
        puskesmas.approved_by_admin_id = admin_id
        puskesmas.approved_at = datetime.utcnow()
        puskesmas.is_active = True
        puskesmas.rejection_reason = None
        
        try:
            db.add(puskesmas)
            db.commit()
            db.refresh(puskesmas)
        except Exception:
            db.rollback()
            raise
        return puskesmas

    def reject(
        self, db: Session, *, puskesmas_id: int, admin_id: int, reason: str
    ) -> Optional[Puskesmas]:
        """Reject a Puskesmas registration."""
        puskesmas = self.get(db, puskesmas_id)
        if not puskesmas:
            return None
        
        puskesmas.registration_status = "rejected"
        puskesmas.approved_by_admin_id = admin_id
        puskesmas.approved_at = datetime.utcnow()
        puskesmas.is_active = False
        puskesmas.rejection_reason = reason
        
        try:
            db.add(puskesmas)
            db.commit()
            db.refresh(puskesmas)
        except Exception:
            db.rollback()
            raise
        return puskesmas

    def suspend(
        self, db: Session, *, puskesmas_id: int, admin_id: int, reason: str
    ) -> Optional[Puskesmas]:
        """Suspend an active Puskesmas with admin-provided reason."""
        puskesmas = self.get(db, puskesmas_id)
        if not puskesmas:
            return None

    def get_by_status(self, db: Session, *, status: str) -> List[Puskesmas]:
        """Get Puskesmas filtered by registration status."""
        stmt = select(Puskesmas).where(Puskesmas.registration_status == status)
        return db.scalars(stmt).all()

    def get_active(self, db: Session) -> List[Puskesmas]:
        """Get only active Puskesmas."""
        stmt = select(Puskesmas).where(Puskesmas.is_active == True).where(Puskesmas.registration_status == "approved")
        return db.scalars(stmt).all()

    def get_active_with_stats(self, db: Session) -> List[tuple[Puskesmas, int, int]]:
        """Return active & approved puskesmas with counts of active ibu hamil and perawat."""
        ibu_counts = (
            select(IbuHamil.puskesmas_id, func.count(IbuHamil.id).label("ibu_count"))
            .where(IbuHamil.is_active == True)
            .group_by(IbuHamil.puskesmas_id)
            .subquery()
        )

        perawat_counts = (
            select(Perawat.puskesmas_id, func.count(Perawat.id).label("perawat_count"))
            .where(Perawat.is_active == True)
            .group_by(Perawat.puskesmas_id)
            .subquery()
        )

        stmt = (
            select(
                Puskesmas,
                func.coalesce(ibu_counts.c.ibu_count, 0).label("active_ibu_hamil_count"),
                func.coalesce(perawat_counts.c.perawat_count, 0).label("active_perawat_count"),
            )
            .outerjoin(ibu_counts, ibu_counts.c.puskesmas_id == Puskesmas.id)
            .outerjoin(perawat_counts, perawat_counts.c.puskesmas_id == Puskesmas.id)
            .where(Puskesmas.registration_status == "approved")
            .where(Puskesmas.is_active == True)
        )
        return db.execute(stmt).all()

    def get_with_stats(
        self, db: Session, *, puskesmas_id: int
    ) -> Optional[tuple[Puskesmas, int, int]]:
        """Get single puskesmas with aggregated active ibu hamil and perawat counts."""
        ibu_counts = (
            select(IbuHamil.puskesmas_id, func.count(IbuHamil.id).label("ibu_count"))
            .where(IbuHamil.is_active == True)
            .group_by(IbuHamil.puskesmas_id)
            .subquery()
        )

        perawat_counts = (
            select(Perawat.puskesmas_id, func.count(Perawat.id).label("perawat_count"))
            .where(Perawat.is_active == True)
            .group_by(Perawat.puskesmas_id)
            .subquery()
        )

        stmt = (
            select(
                Puskesmas,
                func.coalesce(ibu_counts.c.ibu_count, 0).label("active_ibu_hamil_count"),
                func.coalesce(perawat_counts.c.perawat_count, 0).label("active_perawat_count"),
            )
            .outerjoin(ibu_counts, ibu_counts.c.puskesmas_id == Puskesmas.id)
            .outerjoin(perawat_counts, perawat_counts.c.puskesmas_id == Puskesmas.id)
            .where(Puskesmas.id == puskesmas_id)
        )

        result = db.execute(stmt).first()
        if not result:
            return None
        return result

    def find_nearest(
        self, db: Session, *, latitude: float, longitude: float, radius_km: float = 10.0
    ) -> List[Tuple[Puskesmas, float]]:
        """Find Puskesmas within radius using PostGIS distance.
        
        Returns list of (Puskesmas, distance_km) tuples, ordered by distance.
        """
        # Create point from input coordinates
        point_wkt = f"POINT({longitude} {latitude})"
        reference_point = ST_GeogFromText(point_wkt)
        
        # Calculate distance in meters, convert to km
        distance_m = ST_Distance(Puskesmas.location, reference_point)
        distance_km = distance_m / 1000.0
        
        stmt = (
            select(Puskesmas, distance_km.label("distance"))
            .where(Puskesmas.is_active == True)
            .where(Puskesmas.registration_status == "approved")
            .where(distance_km <= radius_km)
            .order_by(distance_km)
        )
        
        results = db.execute(stmt).all()
        return [(row[0], row[1]) for row in results]

    def get_by_admin_user_id(self, db: Session, *, admin_user_id: int) -> Optional[Puskesmas]:
        """Find puskesmas owned by a specific admin user."""
        stmt = select(Puskesmas).where(Puskesmas.admin_user_id == admin_user_id).limit(1)
        return db.scalars(stmt).first()

# Singleton instance
crud_puskesmas = CRUDPuskesmas(Puskesmas)
