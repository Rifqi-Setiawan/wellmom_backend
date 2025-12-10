"""CRUD operations for `Puskesmas` model."""

from __future__ import annotations

from datetime import datetime
from typing import List, Optional, Tuple

from geoalchemy2.functions import ST_Distance, ST_GeogFromText
from sqlalchemy import select, func
from sqlalchemy.orm import Session

from app.crud.base import CRUDBase
from app.models.puskesmas import Puskesmas
from app.schemas.puskesmas import PuskesmasCreate, PuskesmasUpdate


class CRUDPuskesmas(CRUDBase[Puskesmas, PuskesmasCreate, PuskesmasUpdate]):
    def create_with_location(self, db: Session, *, puskesmas_in: PuskesmasCreate) -> Puskesmas:
        """Create Puskesmas with PostGIS location from (longitude, latitude) tuple."""
        puskesmas_data = puskesmas_in.model_dump(exclude_unset=True)
        
        # Extract and convert location tuple to PostGIS Point
        location_tuple = puskesmas_data.pop("location", None)
        if location_tuple:
            lon, lat = location_tuple
            # Create WKT point string: POINT(longitude latitude)
            puskesmas_data["location"] = f"POINT({lon} {lat})"
        
        db_obj = Puskesmas(**puskesmas_data)
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
        stmt = select(Puskesmas).where(Puskesmas.registration_status == "pending")
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

    def get_by_status(self, db: Session, *, status: str) -> List[Puskesmas]:
        """Get Puskesmas filtered by registration status."""
        stmt = select(Puskesmas).where(Puskesmas.registration_status == status)
        return db.scalars(stmt).all()

    def get_active(self, db: Session) -> List[Puskesmas]:
        """Get only active Puskesmas."""
        stmt = select(Puskesmas).where(Puskesmas.is_active == True)
        return db.scalars(stmt).all()

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
            .where(distance_km <= radius_km)
            .order_by(distance_km)
        )
        
        results = db.execute(stmt).all()
        return [(row[0], row[1]) for row in results]

    def update_capacity(
        self, db: Session, *, puskesmas_id: int, increment: int
    ) -> Optional[Puskesmas]:
        """Adjust current_patients count.
        
        Use positive increment to add patients, negative to reduce.
        """
        puskesmas = self.get(db, puskesmas_id)
        if not puskesmas:
            return None
        
        new_count = (puskesmas.current_patients or 0) + increment
        # Ensure it doesn't go below 0
        puskesmas.current_patients = max(0, new_count)
        
        try:
            db.add(puskesmas)
            db.commit()
            db.refresh(puskesmas)
        except Exception:
            db.rollback()
            raise
        return puskesmas


# Singleton instance
crud_puskesmas = CRUDPuskesmas(Puskesmas)
