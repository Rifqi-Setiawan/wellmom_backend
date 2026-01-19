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
        # Exclude 'password' karena disimpan di tabel users, bukan puskesmas
        puskesmas_data = puskesmas_in.model_dump(exclude_unset=True, exclude={"password"})

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

    def deactivate(
        self, db: Session, *, puskesmas_id: int, super_admin_id: int, reason: Optional[str] = None
    ) -> Optional[Puskesmas]:
        """
        Deactivate (nonaktifkan) puskesmas yang sedang aktif.
        
        Cascade effects:
        1. Set puskesmas_id = NULL dan perawat_id = NULL untuk semua ibu hamil di puskesmas ini
        2. Hapus semua perawat yang terdaftar di puskesmas ini (akan cascade delete user juga)
        3. Nonaktifkan akun admin puskesmas (set is_active = False)
        4. Set puskesmas.is_active = False
        
        Args:
            db: Database session
            puskesmas_id: ID puskesmas yang akan dinonaktifkan
            super_admin_id: ID super admin yang melakukan deactivation
            reason: Alasan deactivation (optional)
            
        Returns:
            Puskesmas yang sudah dinonaktifkan atau None jika tidak ditemukan
        """
        puskesmas = self.get(db, puskesmas_id)
        if not puskesmas:
            return None
        
        # Pastikan puskesmas sedang aktif
        if not puskesmas.is_active:
            return puskesmas  # Sudah tidak aktif, return as-is
        
        try:
            # 1. Unassign semua ibu hamil dari puskesmas ini (set puskesmas_id dan perawat_id = NULL)
            ibu_hamil_list = db.scalars(
                select(IbuHamil).where(IbuHamil.puskesmas_id == puskesmas_id)
            ).all()
            
            for ibu in ibu_hamil_list:
                ibu.puskesmas_id = None
                ibu.perawat_id = None
                db.add(ibu)
            
            # 2. Hapus semua perawat di puskesmas ini
            # Karena FK perawat.puskesmas_id memiliki ondelete="CASCADE", 
            # menghapus perawat akan otomatis menghapus user terkait jika ada
            perawat_list = db.scalars(
                select(Perawat).where(Perawat.puskesmas_id == puskesmas_id)
            ).all()
            
            for perawat in perawat_list:
                db.delete(perawat)
            
            # 3. Nonaktifkan akun admin puskesmas
            if puskesmas.admin_user_id:
                from app.models.user import User
                admin_user = db.get(User, puskesmas.admin_user_id)
                if admin_user:
                    admin_user.is_active = False
                    db.add(admin_user)
            
            # 4. Nonaktifkan puskesmas
            puskesmas.is_active = False
            if reason:
                puskesmas.admin_notes = f"{puskesmas.admin_notes or ''}\n[Deactivated] {reason}".strip()
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
        self, db: Session, *, latitude: float, longitude: float, limit: int = 5
    ) -> List[Tuple[Puskesmas, float]]:
        """Find nearest Puskesmas using PostGIS distance.

        Returns list of (Puskesmas, distance_km) tuples, ordered by distance.
        Only returns approved and active puskesmas, limited to specified count.
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
            .where(Puskesmas.location.isnot(None))
            .order_by(distance_km)
            .limit(limit)
        )

        results = db.execute(stmt).all()
        return [(row[0], row[1]) for row in results]

    def get_by_admin_user_id(self, db: Session, *, admin_user_id: int) -> Optional[Puskesmas]:
        """Find puskesmas owned by a specific admin user."""
        stmt = select(Puskesmas).where(Puskesmas.admin_user_id == admin_user_id).limit(1)
        return db.scalars(stmt).first()

    def update_with_location(
        self, db: Session, *, db_obj: Puskesmas, obj_in: PuskesmasUpdate
    ) -> Puskesmas:
        """Update Puskesmas including PostGIS location if latitude/longitude changed."""
        update_data = obj_in.model_dump(exclude_unset=True)

        # Handle location update if lat/long provided
        lat = update_data.get("latitude")
        lon = update_data.get("longitude")
        if lat is not None and lon is not None:
            location_wkt = f"POINT({lon} {lat})"
            db_obj.location = ST_GeogFromText(location_wkt)

        # Update other fields
        for field, value in update_data.items():
            if hasattr(db_obj, field) and field not in ("latitude", "longitude"):
                setattr(db_obj, field, value)
            elif field in ("latitude", "longitude"):
                # Also set the raw lat/lon fields
                setattr(db_obj, field, value)

        try:
            db.add(db_obj)
            db.commit()
            db.refresh(db_obj)
        except Exception:
            db.rollback()
            raise
        return db_obj

# Singleton instance
crud_puskesmas = CRUDPuskesmas(Puskesmas)
