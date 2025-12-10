"""CRUD operations package - exports singleton instances for all models."""

from .base import CRUDBase
from .user import crud_user
from .puskesmas import crud_puskesmas
from .perawat import crud_perawat
from .ibu_hamil import crud_ibu_hamil
from .kerabat import crud_kerabat
from .health_record import crud_health_record
from .notification import crud_notification
from .transfer_request import crud_transfer_request


__all__ = [
    # Base
    "CRUDBase",
    # CRUD instances
    "crud_user",
    "crud_puskesmas",
    "crud_perawat",
    "crud_ibu_hamil",
    "crud_kerabat",
    "crud_health_record",
    "crud_notification",
    "crud_transfer_request",
]
