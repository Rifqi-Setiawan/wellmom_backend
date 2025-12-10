"""Pydantic schemas for `Puskesmas` domain objects."""

from datetime import datetime
from typing import Optional, Tuple

from pydantic import BaseModel, ConfigDict, EmailStr, field_validator


REGISTRATION_STATUSES = {"pending", "approved", "rejected", "suspended"}


def _validate_phone(value: str) -> str:
	# Accepts Indonesian format: +62 or 0 followed by 8xxx, minimal length 10 digits
	import re

	if not value:
		raise ValueError("Phone is required")
	if not re.match(r"^(\+62|0)8[1-9][0-9]{7,10}$", value):
		raise ValueError("Phone must start with +62 or 08 and contain 10-13 digits")
	return value


def _validate_code(value: str) -> str:
	import re

	if not re.match(r"^PKM-[A-Z0-9]{3}-[A-Z0-9]{3}$", value):
		raise ValueError("Code must match format PKM-XXX-XXX")
	return value


def _validate_nik(value: str) -> str:
	import re

	if not re.match(r"^[0-9]{16}$", value):
		raise ValueError("NIK must be exactly 16 digits")
	return value


def _validate_location(value: Tuple[float, float]) -> Tuple[float, float]:
	if value is None:
		raise ValueError("Location is required")
	if not isinstance(value, tuple) or len(value) != 2:
		raise ValueError("Location must be a (longitude, latitude) tuple")
	lon, lat = value
	if not (-180.0 <= lon <= 180.0 and -90.0 <= lat <= 90.0):
		raise ValueError("Longitude must be between -180 and 180, latitude between -90 and 90")
	return lon, lat


class PuskesmasBase(BaseModel):
	admin_user_id: Optional[int] = None
	name: str
	code: str
	sk_number: str
	sk_document_url: str
	operational_license_number: str
	license_document_url: str
	npwp: Optional[str] = None
	npwp_document_url: Optional[str] = None
	accreditation_level: Optional[str] = None
	accreditation_cert_url: Optional[str] = None
	address: str
	kelurahan: Optional[str] = None
	kecamatan: Optional[str] = None
	kabupaten: Optional[str] = "Kerinci"
	provinsi: Optional[str] = "Jambi"
	postal_code: Optional[str] = None
	phone: str
	email: EmailStr
	location: Tuple[float, float]
	building_photo_url: str
	kepala_name: str
	kepala_nip: str
	kepala_sk_number: str
	kepala_sk_document_url: str
	kepala_nik: str
	kepala_ktp_url: str
	kepala_phone: str
	kepala_email: EmailStr
	kepala_phone_verified: bool = False
	kepala_email_verified: bool = False
	verification_photo_url: str
	total_perawat: Optional[int] = 0
	operational_hours: Optional[str] = None
	facilities: Optional[str] = None
	max_patients: Optional[int] = 100
	current_patients: Optional[int] = 0

	@field_validator("phone")
	@classmethod
	def validate_phone(cls, v: str) -> str:
		return _validate_phone(v)

	@field_validator("kepala_phone")
	@classmethod
	def validate_kepala_phone(cls, v: str) -> str:
		return _validate_phone(v)

	@field_validator("code")
	@classmethod
	def validate_code(cls, v: str) -> str:
		return _validate_code(v)

	@field_validator("kepala_nik")
	@classmethod
	def validate_kepala_nik(cls, v: str) -> str:
		return _validate_nik(v)

	@field_validator("location")
	@classmethod
	def validate_location(cls, v: Tuple[float, float]) -> Tuple[float, float]:
		return _validate_location(v)

	model_config = ConfigDict(json_schema_extra={
		"example": {
			"admin_user_id": 10,
			"name": "Puskesmas Sungai Penuh",
			"code": "PKM-ABC-123",
			"sk_number": "SK-2025-001",
			"sk_document_url": "/files/sk_pkm.pdf",
			"operational_license_number": "IZIN-OP-2025-09",
			"license_document_url": "/files/izin_operasional.pdf",
			"npwp": "12.345.678.9-012.345",
			"npwp_document_url": "/files/npwp.pdf",
			"accreditation_level": "paripurna",
			"accreditation_cert_url": "/files/akreditasi.pdf",
			"address": "Jl. Merdeka No. 1",
			"kelurahan": "Sungai Penuh",
			"kecamatan": "Pesisir Bukit",
			"kabupaten": "Kerinci",
			"provinsi": "Jambi",
			"postal_code": "37111",
			"phone": "+6281234567890",
			"email": "admin@puskesmas.go.id",
			"location": [101.3912, -2.0645],
			"building_photo_url": "/files/gedung.jpg",
			"kepala_name": "dr. Rina",
			"kepala_nip": "198012312010012001",
			"kepala_sk_number": "SK-KAPUS-2025",
			"kepala_sk_document_url": "/files/sk_kepala.pdf",
			"kepala_nik": "3175091201010001",
			"kepala_ktp_url": "/files/ktp_kepala.pdf",
			"kepala_phone": "+628111222333",
			"kepala_email": "kepala@puskesmas.go.id",
			"kepala_phone_verified": False,
			"kepala_email_verified": False,
			"verification_photo_url": "/files/verifikasi.jpg",
			"total_perawat": 12,
			"operational_hours": "Senin-Jumat 08:00-16:00",
			"facilities": "UGD, Rawat Jalan, Laboratorium",
			"max_patients": 200,
			"current_patients": 45,
		}
	})


class PuskesmasCreate(PuskesmasBase):
	# All fields inherited from base are required for registration
	model_config = ConfigDict(json_schema_extra={
		"example": {
			**PuskesmasBase.model_config.get("json_schema_extra", {}).get("example", {}),
			"admin_user_id": 10,
		}
	})


class PuskesmasUpdate(BaseModel):
	name: Optional[str] = None
	code: Optional[str] = None
	sk_number: Optional[str] = None
	sk_document_url: Optional[str] = None
	operational_license_number: Optional[str] = None
	license_document_url: Optional[str] = None
	npwp: Optional[str] = None
	npwp_document_url: Optional[str] = None
	accreditation_level: Optional[str] = None
	accreditation_cert_url: Optional[str] = None
	address: Optional[str] = None
	kelurahan: Optional[str] = None
	kecamatan: Optional[str] = None
	kabupaten: Optional[str] = None
	provinsi: Optional[str] = None
	postal_code: Optional[str] = None
	phone: Optional[str] = None
	email: Optional[EmailStr] = None
	location: Optional[Tuple[float, float]] = None
	building_photo_url: Optional[str] = None
	kepala_name: Optional[str] = None
	kepala_nip: Optional[str] = None
	kepala_sk_number: Optional[str] = None
	kepala_sk_document_url: Optional[str] = None
	kepala_nik: Optional[str] = None
	kepala_ktp_url: Optional[str] = None
	kepala_phone: Optional[str] = None
	kepala_email: Optional[EmailStr] = None
	kepala_phone_verified: Optional[bool] = None
	kepala_email_verified: Optional[bool] = None
	verification_photo_url: Optional[str] = None
	total_perawat: Optional[int] = None
	operational_hours: Optional[str] = None
	facilities: Optional[str] = None
	max_patients: Optional[int] = None
	current_patients: Optional[int] = None
	is_active: Optional[bool] = None

	@field_validator("phone")
	@classmethod
	def validate_phone(cls, v: Optional[str]) -> Optional[str]:
		return _validate_phone(v) if v is not None else v

	@field_validator("kepala_phone")
	@classmethod
	def validate_kepala_phone(cls, v: Optional[str]) -> Optional[str]:
		return _validate_phone(v) if v is not None else v

	@field_validator("code")
	@classmethod
	def validate_code(cls, v: Optional[str]) -> Optional[str]:
		return _validate_code(v) if v is not None else v

	@field_validator("kepala_nik")
	@classmethod
	def validate_kepala_nik(cls, v: Optional[str]) -> Optional[str]:
		return _validate_nik(v) if v is not None else v

	@field_validator("location")
	@classmethod
	def validate_location(cls, v: Optional[Tuple[float, float]]) -> Optional[Tuple[float, float]]:
		return _validate_location(v) if v is not None else v

	model_config = ConfigDict(json_schema_extra={
		"example": {
			"phone": "081234567890",
			"email": "admin@puskesmas.go.id",
			"location": [101.4, -2.06],
			"accreditation_level": "utama",
			"facilities": "UGD, Laboratorium",
			"is_active": True,
		}
	})


class PuskesmasResponse(PuskesmasBase):
	id: int
	registration_status: str
	registration_date: Optional[datetime] = None
	approved_by_admin_id: Optional[int] = None
	approved_at: Optional[datetime] = None
	rejection_reason: Optional[str] = None
	is_active: bool
	created_at: datetime
	updated_at: datetime

	model_config = ConfigDict(from_attributes=True, json_schema_extra={
		"example": {
			**PuskesmasBase.model_config.get("json_schema_extra", {}).get("example", {}),
			"id": 1,
			"registration_status": "pending",
			"registration_date": "2025-01-01T10:00:00Z",
			"approved_by_admin_id": None,
			"approved_at": None,
			"rejection_reason": None,
			"is_active": False,
			"created_at": "2025-01-01T10:00:00Z",
			"updated_at": "2025-01-02T11:00:00Z",
		}
	})

	@field_validator("registration_status")
	@classmethod
	def validate_status(cls, v: str) -> str:
		if v not in REGISTRATION_STATUSES:
			raise ValueError(f"Status must be one of {sorted(REGISTRATION_STATUSES)}")
		return v


class PuskesmasAdminResponse(PuskesmasResponse):
	admin_notes: Optional[str] = None

	model_config = ConfigDict(from_attributes=True, json_schema_extra={
		"example": {
			**PuskesmasResponse.model_config.get("json_schema_extra", {}).get("example", {}),
			"admin_notes": "Perlu verifikasi ulang dokumen izin operasional.",
		}
	})


class PuskesmasApproval(BaseModel):
	registration_status: str
	rejection_reason: Optional[str] = None
	approved_by_admin_id: Optional[int] = None
	approved_at: Optional[datetime] = None

	@field_validator("registration_status")
	@classmethod
	def validate_status(cls, v: str) -> str:
		if v not in REGISTRATION_STATUSES:
			raise ValueError(f"Status must be one of {sorted(REGISTRATION_STATUSES)}")
		return v

	model_config = ConfigDict(json_schema_extra={
		"example": {
			"registration_status": "approved",
			"approved_by_admin_id": 1,
			"approved_at": "2025-02-01T09:00:00Z",
			"rejection_reason": None,
		}
	})
