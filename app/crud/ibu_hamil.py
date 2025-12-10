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
        # Convert Pydantic model to dict
        obj_data = obj_in.model_dump(exclude={'location'})
        
        # Convert location tuple to WKT string for PostGIS
        location_wkt = None
        if obj_in.location:
            lon, lat = obj_in.location
            location_wkt = f'POINT({lon} {lat})'
        
        # Create IbuHamil instance
        db_obj = IbuHamil(
            **obj_data,
            user_id=user_id,
            location=location_wkt  # SQLAlchemy will wrap with ST_GeogFromText
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


# Singleton instance
crud_ibu_hamil = CRUDIbuHamil(IbuHamil)
