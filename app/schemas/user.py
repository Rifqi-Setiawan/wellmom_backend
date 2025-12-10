"""Pydantic schemas for `User` domain objects."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, field_validator


ALLOWED_ROLES = {"admin", "puskesmas", "perawat", "ibu_hamil", "kerabat"}


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
