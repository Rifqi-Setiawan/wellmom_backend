"""Pydantic schemas for `TransferRequest` domain objects."""

from datetime import datetime
from typing import Optional, Tuple

from pydantic import BaseModel, ConfigDict, field_validator


REQUESTER_TYPES = {"perawat", "ibu_hamil"}
STATUSES = {"pending", "approved", "rejected", "cancelled"}


def _validate_location(value: Tuple[float, float]) -> Tuple[float, float]:
	if value is None:
		raise ValueError("Location is required")
	if not isinstance(value, tuple) or len(value) != 2:
		raise ValueError("Location must be a (longitude, latitude) tuple")
	lon, lat = value
	if not (-180.0 <= lon <= 180.0 and -90.0 <= lat <= 90.0):
		raise ValueError("Longitude must be between -180 and 180, latitude between -90 and 90")
	return lon, lat


class TransferRequestBase(BaseModel):
	requester_user_id: int
	requester_type: str
	perawat_id: Optional[int] = None
	from_puskesmas_id: Optional[int] = None
	to_puskesmas_id: Optional[int] = None
	ibu_hamil_id: Optional[int] = None
	new_address: Optional[str] = None
	new_location: Optional[Tuple[float, float]] = None
	reason: str
	status: Optional[str] = "pending"

	@field_validator("requester_type")
	@classmethod
	def validate_requester_type(cls, v: str) -> str:
		if v not in REQUESTER_TYPES:
			raise ValueError(f"Requester type must be one of {sorted(REQUESTER_TYPES)}")
		return v

	@field_validator("status")
	@classmethod
	def validate_status(cls, v: Optional[str]) -> Optional[str]:
		if v is not None and v not in STATUSES:
			raise ValueError(f"Status must be one of {sorted(STATUSES)}")
		return v

	@field_validator("new_location")
	@classmethod
	def validate_new_location(cls, v: Optional[Tuple[float, float]]) -> Optional[Tuple[float, float]]:
		if v is None:
			return v
		return _validate_location(v)

	model_config = ConfigDict(json_schema_extra={
		"example": {
			"requester_user_id": 5,
			"requester_type": "perawat",
			"perawat_id": 2,
			"from_puskesmas_id": 1,
			"to_puskesmas_id": 3,
			"reason": "Pindah domisili",
			"status": "pending",
		}
	})


class TransferRequestCreate(TransferRequestBase):
	model_config = ConfigDict(json_schema_extra={
		"example": {
			**TransferRequestBase.model_config.get("json_schema_extra", {}).get("example", {}),
			"new_address": "Jl. Baru No. 5",
			"new_location": [101.4, -2.05],
		}
	})


class TransferRequestUpdate(BaseModel):
	perawat_id: Optional[int] = None
	from_puskesmas_id: Optional[int] = None
	to_puskesmas_id: Optional[int] = None
	ibu_hamil_id: Optional[int] = None
	new_address: Optional[str] = None
	new_location: Optional[Tuple[float, float]] = None
	reason: Optional[str] = None
	status: Optional[str] = None
	reviewed_by_user_id: Optional[int] = None
	reviewed_at: Optional[datetime] = None
	rejection_reason: Optional[str] = None

	@field_validator("status")
	@classmethod
	def validate_status(cls, v: Optional[str]) -> Optional[str]:
		if v is not None and v not in STATUSES:
			raise ValueError(f"Status must be one of {sorted(STATUSES)}")
		return v

	@field_validator("new_location")
	@classmethod
	def validate_new_location(cls, v: Optional[Tuple[float, float]]) -> Optional[Tuple[float, float]]:
		if v is None:
			return v
		return _validate_location(v)

	model_config = ConfigDict(json_schema_extra={
		"example": {
			"status": "approved",
			"reviewed_by_user_id": 1,
			"reviewed_at": "2025-02-10T09:00:00Z",
			"rejection_reason": None,
		}
	})


class TransferRequestResponse(TransferRequestBase):
	id: int
	reviewed_by_user_id: Optional[int] = None
	reviewed_at: Optional[datetime] = None
	rejection_reason: Optional[str] = None
	created_at: datetime
	updated_at: datetime

	model_config = ConfigDict(from_attributes=True, json_schema_extra={
		"example": {
			**TransferRequestBase.model_config.get("json_schema_extra", {}).get("example", {}),
			"id": 1,
			"reviewed_by_user_id": 1,
			"reviewed_at": "2025-02-10T09:00:00Z",
			"rejection_reason": None,
			"created_at": "2025-02-09T10:00:00Z",
			"updated_at": "2025-02-10T09:00:00Z",
		}
	})
