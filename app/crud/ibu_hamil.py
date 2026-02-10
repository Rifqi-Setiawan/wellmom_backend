"""CRUD operations for `IbuHamil` model."""

from __future__ import annotations

from typing import List, Optional, Tuple

from geoalchemy2.functions import ST_Distance, ST_GeogFromText
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.crud.base import CRUDBase
from app.models.ibu_hamil import IbuHamil
from app.models.puskesmas import Puskesmas
from app.schemas.ibu_hamil import IbuHamilCreate, IbuHamilUpdate


class CRUDIbuHamil(CRUDBase[IbuHamil, IbuHamilCreate, IbuHamilUpdate]):
    def get_by_puskesmas(self, db: Session, *, puskesmas_id: int) -> List[IbuHamil]:
        """Get all Ibu Hamil assigned to a specific Puskesmas."""
        stmt = select(IbuHamil).where(IbuHamil.puskesmas_id == puskesmas_id)
        return db.scalars(stmt).all()

    def get_by_perawat(self, db: Session, *, perawat_id: int) -> List[IbuHamil]:
        """Get all Ibu Hamil assigned to a specific Perawat."""
        stmt = select(IbuHamil).where(IbuHamil.perawat_id == perawat_id)
        return db.scalars(stmt).all()

    def create_with_location(
        self, db: Session, *, obj_in: IbuHamilCreate, user_id: int
    ) -> IbuHamil:
        """Create Ibu Hamil with PostGIS location conversion.

        Args:
            db: Database session
            obj_in: IbuHamilCreate schema with location as tuple (lon, lat)
            user_id: User ID to link to

        Returns:
            Created IbuHamil instance
        """
        # Convert Pydantic model to dict (exclude location tuple)
        obj_data = obj_in.model_dump(exclude={"location"})
        # Ensure profile photo is not set during registration
        obj_data.pop("profile_photo_url", None)
        # Ensure risk_level is NULL during registration (will be set by perawat later)
        obj_data.pop("risk_level", None)

        # Flatten nested riwayat_kesehatan_ibu -> individual boolean columns
        riwayat = obj_data.pop("riwayat_kesehatan_ibu", None) or {}
        obj_data.update(
            {
                "darah_tinggi": riwayat.get("darah_tinggi"),
                "diabetes": riwayat.get("diabetes"),
                "anemia": riwayat.get("anemia"),
                "penyakit_jantung": riwayat.get("penyakit_jantung"),
                "asma": riwayat.get("asma"),
                "penyakit_ginjal": riwayat.get("penyakit_ginjal"),
                "tbc_malaria": riwayat.get("tbc_malaria"),
            }
        )

        # Convert location tuple to WKT string for PostGIS
        location_wkt = None
        if obj_in.location:
            lon, lat = obj_in.location
            location_wkt = f"POINT({lon} {lat})"
        
        # Create IbuHamil instance
        db_obj = IbuHamil(
            **obj_data,
            user_id=user_id,
            location=ST_GeogFromText(location_wkt) if location_wkt else None,
        )
        
        db.add(db_obj)
        try:
            db.commit()
            db.refresh(db_obj)
        except Exception:
            db.rollback()
            raise
            
        return db_obj

    def get_unassigned(self, db: Session) -> List[IbuHamil]:
        """Get Ibu Hamil not yet assigned to any Puskesmas."""
        stmt = select(IbuHamil).where(IbuHamil.puskesmas_id.is_(None))
        return db.scalars(stmt).all()

    def assign_to_puskesmas(
        self, db: Session, *, ibu_id: int, puskesmas_id: int, distance_km: float
    ) -> Optional[IbuHamil]:
        """Assign Ibu Hamil to a Puskesmas."""
        ibu = self.get(db, ibu_id)
        if not ibu:
            return None
        
        ibu.puskesmas_id = puskesmas_id
        ibu.assignment_distance_km = distance_km
        
        try:
            db.add(ibu)
            db.commit()
            db.refresh(ibu)
        except Exception:
            db.rollback()
            raise
        return ibu

    def assign_to_perawat(
        self, db: Session, *, ibu_id: int, perawat_id: int
    ) -> Optional[IbuHamil]:
        """Assign Ibu Hamil to a Perawat."""
        ibu = self.get(db, ibu_id)
        if not ibu:
            return None
        
        ibu.perawat_id = perawat_id
        
        try:
            db.add(ibu)
            db.commit()
            db.refresh(ibu)
        except Exception:
            db.rollback()
            raise
        return ibu

    def get_by_risk_level(self, db: Session, *, risk_level: str) -> List[IbuHamil]:
        """Get Ibu Hamil filtered by risk level."""
        stmt = select(IbuHamil).where(IbuHamil.risk_level == risk_level)
        return db.scalars(stmt).all()

    def find_nearest_puskesmas(
        self, db: Session, *, ibu_id: int, radius_km: float = 20.0
    ) -> List[Tuple[Puskesmas, float]]:
        """Find nearest active Puskesmas within radius using PostGIS.
        
        Returns list of (Puskesmas, distance_km) tuples, ordered by distance.
        """
        ibu = self.get(db, ibu_id)
        if not ibu or not ibu.location:
            return []
        
        # Calculate distance from Ibu's location to Puskesmas
        distance_m = ST_Distance(Puskesmas.location, ibu.location)
        distance_km = distance_m / 1000.0
        
        stmt = (
            select(Puskesmas, distance_km.label("distance"))
            .where(Puskesmas.is_active == True)
            .where(distance_km <= radius_km)
            .order_by(distance_km)
        )
        
        results = db.execute(stmt).all()
        return [(row[0], row[1]) for row in results]

    def update(
        self, db: Session, *, db_obj: IbuHamil, obj_in: IbuHamilUpdate
    ) -> IbuHamil:
        """Update IbuHamil with proper handling of nested riwayat_kesehatan_ibu and location.
        
        Args:
            db: Database session
            db_obj: Existing IbuHamil instance
            obj_in: IbuHamilUpdate schema with optional fields
            
        Returns:
            Updated IbuHamil instance
        """
        # Convert Pydantic model to dict (exclude location and riwayat_kesehatan_ibu if present)
        update_data = obj_in.model_dump(exclude_unset=True, exclude={"location", "riwayat_kesehatan_ibu"})

        riwayat_kesehatan_ibu = getattr(obj_in, "riwayat_kesehatan_ibu", None)
        # Handle nested riwayat_kesehatan_ibu -> flatten to individual boolean columns
        if riwayat_kesehatan_ibu is not None:
            riwayat = riwayat_kesehatan_ibu.model_dump()
            update_data.update(
                {
                    "darah_tinggi": riwayat.get("darah_tinggi"),
                    "diabetes": riwayat.get("diabetes"),
                    "anemia": riwayat.get("anemia"),
                    "penyakit_jantung": riwayat.get("penyakit_jantung"),
                    "asma": riwayat.get("asma"),
                    "penyakit_ginjal": riwayat.get("penyakit_ginjal"),
                    "tbc_malaria": riwayat.get("tbc_malaria"),
                }
            )

        # Handle location tuple -> convert to PostGIS Geography
        # Only process if location attribute exists and is not None
        if hasattr(obj_in, "location") and obj_in.location is not None:
            lon, lat = obj_in.location
            location_wkt = f"POINT({lon} {lat})"
            update_data["location"] = ST_GeogFromText(location_wkt)
        
        # Update object attributes
        for field, value in update_data.items():
            setattr(db_obj, field, value)
        
        db.add(db_obj)
        try:
            db.commit()
            db.refresh(db_obj)
        except Exception:
            db.rollback()
            raise
        
        return db_obj

    def update_kehamilan(
        self, db: Session, *, db_obj: IbuHamil, obj_in
    ) -> IbuHamil:
        """Update IbuHamil kehamilan data only (without location).
        
        This is specifically for IbuHamilUpdateKehamilan schema which doesn't include location field.
        
        Args:
            db: Database session
            db_obj: Existing IbuHamil instance
            obj_in: IbuHamilUpdateKehamilan schema (kehamilan + riwayat kesehatan data)
            
        Returns:
            Updated IbuHamil instance
        """
        # Convert Pydantic model to dict (exclude riwayat_kesehatan_ibu if present)
        update_data = obj_in.model_dump(exclude_unset=True, exclude={"riwayat_kesehatan_ibu"})

        riwayat_kesehatan_ibu = getattr(obj_in, "riwayat_kesehatan_ibu", None)
        # Handle nested riwayat_kesehatan_ibu -> flatten to individual boolean columns
        if riwayat_kesehatan_ibu is not None:
            riwayat = riwayat_kesehatan_ibu.model_dump()
            update_data.update(
                {
                    "darah_tinggi": riwayat.get("darah_tinggi"),
                    "diabetes": riwayat.get("diabetes"),
                    "anemia": riwayat.get("anemia"),
                    "penyakit_jantung": riwayat.get("penyakit_jantung"),
                    "asma": riwayat.get("asma"),
                    "penyakit_ginjal": riwayat.get("penyakit_ginjal"),
                    "tbc_malaria": riwayat.get("tbc_malaria"),
                }
            )
        
        # Update object attributes
        for field, value in update_data.items():
            setattr(db_obj, field, value)
        
        db.add(db_obj)
        try:
            db.commit()
            db.refresh(db_obj)
        except Exception:
            db.rollback()
            raise
        
        return db_obj

    def update_identitas(
        self, db: Session, *, db_obj: IbuHamil, obj_in
    ) -> IbuHamil:
        """Update IbuHamil identitas data (with location support).
        
        This is specifically for IbuHamilUpdateIdentitas schema which includes location field.
        
        Args:
            db: Database session
            db_obj: Existing IbuHamil instance
            obj_in: IbuHamilUpdateIdentitas schema (identitas + alamat + lokasi data)
            
        Returns:
            Updated IbuHamil instance
        """
        # Convert Pydantic model to dict (exclude location if present)
        update_data = obj_in.model_dump(exclude_unset=True, exclude={"location"})

        # Handle location tuple -> convert to PostGIS Geography
        if hasattr(obj_in, "location") and obj_in.location is not None:
            lon, lat = obj_in.location
            location_wkt = f"POINT({lon} {lat})"
            update_data["location"] = ST_GeogFromText(location_wkt)
        
        # Update object attributes
        for field, value in update_data.items():
            setattr(db_obj, field, value)
        
        db.add(db_obj)
        try:
            db.commit()
            db.refresh(db_obj)
        except Exception:
            db.rollback()
            raise
        
        return db_obj


# Singleton instance
crud_ibu_hamil = CRUDIbuHamil(IbuHamil)
