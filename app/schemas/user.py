"""Pydantic schemas for `User` domain objects."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, field_validator


ALLOWED_ROLES = {"super_admin", "puskesmas", "perawat", "ibu_hamil", "kerabat"}


class UserBase(BaseModel):
	email: Optional[str] = None
	phone: str
	full_name: str
	role: str

	@field_validator("phone")
	@classmethod
	def validate_phone(cls, v: str) -> str:
		# Basic E.164-ish check: optional +, 8-15 digits
		if not v or not __import__("re").match(r"^\+?\d{8,15}$", v):
			raise ValueError("Phone must be 8-15 digits, optional leading '+'")
		return v

	@field_validator("role")
	@classmethod
	def validate_role(cls, v: str) -> str:
		if v not in ALLOWED_ROLES:
			raise ValueError(f"Role must be one of {sorted(ALLOWED_ROLES)}")
		return v

	model_config = ConfigDict(json_schema_extra={
		"example": {
			"email": "ibu@example.com",
			"phone": "+6281234567890",
			"full_name": "Siti Aminah",
			"role": "ibu_hamil",
		}
	})


class UserCreate(UserBase):
	password: str

	model_config = ConfigDict(json_schema_extra={
		"example": {
			"email": "ibu@example.com",
			"phone": "+6281234567890",
			"password": "StrongPass!234",
			"full_name": "Siti Aminah",
			"role": "ibu_hamil",
		}
	})


class UserUpdate(BaseModel):
	email: Optional[str] = None
	phone: Optional[str] = None
	full_name: Optional[str] = None
	role: Optional[str] = None
	profile_photo_url: Optional[str] = None
	is_active: Optional[bool] = None
	is_verified: Optional[bool] = None
	verification_token: Optional[str] = None

	@field_validator("phone")
	@classmethod
	def validate_phone(cls, v: Optional[str]) -> Optional[str]:
		if v is None:
			return v
		if not __import__("re").match(r"^\+?\d{8,15}$", v):
			raise ValueError("Phone must be 8-15 digits, optional leading '+'")
		return v

	@field_validator("role")
	@classmethod
	def validate_role(cls, v: Optional[str]) -> Optional[str]:
		if v is None:
			return v
		if v not in ALLOWED_ROLES:
			raise ValueError(f"Role must be one of {sorted(ALLOWED_ROLES)}")
		return v

	model_config = ConfigDict(json_schema_extra={
		"example": {
			"email": "ibu.new@example.com",
			"phone": "+628111222333",
			"full_name": "Siti A.",
			"role": "ibu_hamil",
			"profile_photo_url": "https://cdn.example.com/photos/siti.jpg",
			"is_active": True,
			"is_verified": True,
		}
	})


class UserResponse(UserBase):
	id: int
	profile_photo_url: Optional[str] = None
	is_active: bool
	is_verified: bool
	verification_token: Optional[str] = None
	fcm_token: Optional[str] = None
	fcm_token_updated_at: Optional[datetime] = None
	created_at: datetime
	updated_at: datetime

	model_config = ConfigDict(from_attributes=True, json_schema_extra={
		"example": {
			"id": 1,
			"email": "ibu@example.com",
			"phone": "+6281234567890",
			"full_name": "Siti Aminah",
			"role": "ibu_hamil",
			"profile_photo_url": "https://cdn.example.com/photos/siti.jpg",
			"is_active": True,
			"is_verified": False,
			"verification_token": "abc123",
			"fcm_token": "dXBkYXRlZF90b2tlbl9leGFtcGxl...",
			"fcm_token_updated_at": "2025-01-02T08:00:00Z",
			"created_at": "2025-01-01T10:00:00Z",
			"updated_at": "2025-01-02T10:00:00Z",
		}
	})


class UserLogin(BaseModel):
	phone: str
	password: str

	@field_validator("phone")
	@classmethod
	def validate_phone(cls, v: str) -> str:
		if not __import__("re").match(r"^\+?\d{8,15}$", v):
			raise ValueError("Phone must be 8-15 digits, optional leading '+'")
		return v

	model_config = ConfigDict(json_schema_extra={
		"example": {
			"phone": "+6281234567890",
			"password": "StrongPass!234",
		}
	})


# ============================================
# Puskesmas Login Schemas
# ============================================

class PuskesmasLoginRequest(BaseModel):
	"""Request body for puskesmas admin login."""
	email: str
	password: str

	model_config = ConfigDict(json_schema_extra={
		"example": {
			"email": "admin@puskesmas.go.id",
			"password": "SecurePass123!",
		}
	})


class PuskesmasLoginUserInfo(BaseModel):
	"""User information in login response."""
	id: int
	email: Optional[str]
	full_name: str

	model_config = ConfigDict(from_attributes=True)


class PuskesmasLoginPuskesmasInfo(BaseModel):
	"""Puskesmas information in login response."""
	id: int
	name: str
	registration_status: str
	is_active: bool

	model_config = ConfigDict(from_attributes=True)


class PuskesmasLoginResponse(BaseModel):
	"""Response body for successful puskesmas admin login."""
	access_token: str
	token_type: str = "bearer"
	role: str
	user: PuskesmasLoginUserInfo
	puskesmas: PuskesmasLoginPuskesmasInfo

	model_config = ConfigDict(json_schema_extra={
		"example": {
			"access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
			"token_type": "bearer",
			"role": "puskesmas",
			"user": {
				"id": 15,
				"email": "admin@puskesmas.go.id",
				"full_name": "Admin Puskesmas Sungai Penuh"
			},
			"puskesmas": {
				"id": 1,
				"name": "Puskesmas Sungai Penuh",
				"registration_status": "approved",
				"is_active": True
			}
		}
	})


# ============================================
# Super Admin Schemas
# ============================================

class SuperAdminRegisterRequest(BaseModel):
	"""Request body for super admin registration."""
	email: str
	phone: str
	password: str
	full_name: str

	model_config = ConfigDict(json_schema_extra={
		"example": {
			"email": "superadmin@wellmom.go.id",
			"phone": "+6281234567890",
			"password": "SuperSecurePass123!",
			"full_name": "Super Admin WellMom"
		}
	})


class SuperAdminLoginRequest(BaseModel):
	"""Request body for super admin login."""
	email: str
	password: str

	model_config = ConfigDict(json_schema_extra={
		"example": {
			"email": "superadmin@wellmom.go.id",
			"password": "SuperSecurePass123!",
		}
	})


class SuperAdminLoginResponse(BaseModel):
	"""Response body for successful super admin login."""
	access_token: str
	token_type: str = "bearer"
	role: str
	user: PuskesmasLoginUserInfo  # Reuse same structure

	model_config = ConfigDict(json_schema_extra={
		"example": {
			"access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
			"token_type": "bearer",
			"role": "super_admin",
			"user": {
				"id": 1,
				"email": "superadmin@wellmom.go.id",
				"full_name": "Super Admin WellMom"
			}
		}
	})


# ============================================
# FCM Token Schemas
# ============================================

class FCMTokenUpdate(BaseModel):
	fcm_token: str

	model_config = ConfigDict(json_schema_extra={
		"example": {
			"fcm_token": "dXBkYXRlZF90b2tlbl9leGFtcGxl..."
		}
	})
