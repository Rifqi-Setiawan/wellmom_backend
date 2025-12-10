"""Generic CRUD base class for SQLAlchemy models."""

from __future__ import annotations

from typing import Any, Dict, Generic, Iterable, Optional, Type, TypeVar, Union

from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import Base


ModelType = TypeVar("ModelType", bound=Base)
CreateSchemaType = TypeVar("CreateSchemaType", bound=BaseModel)
UpdateSchemaType = TypeVar("UpdateSchemaType", bound=BaseModel)


class CRUDBase(Generic[ModelType, CreateSchemaType, UpdateSchemaType]):
	"""Reusable CRUD helper for SQLAlchemy models.

	All methods operate on model instances and return database objects, not schemas.
	"""

	def __init__(self, model: Type[ModelType]):
		self.model = model

	# ----- Read -----
	def get(self, db: Session, id: Any) -> Optional[ModelType]:
		"""Get one record by primary key."""
		return db.get(self.model, id)

	def get_multi(self, db: Session, *, skip: int = 0, limit: int = 100) -> Iterable[ModelType]:
		"""Get records with pagination."""
		stmt = select(self.model).offset(skip).limit(limit)
		return db.scalars(stmt).all()

	def get_by_field(self, db: Session, field_name: str, value: Any) -> Optional[ModelType]:
		"""Get first record where given field equals value."""
		if not hasattr(self.model, field_name):
			raise AttributeError(f"Model '{self.model.__name__}' has no field '{field_name}'")
		stmt = select(self.model).where(getattr(self.model, field_name) == value).limit(1)
		return db.scalars(stmt).first()

	# ----- Create -----
	def create(self, db: Session, *, obj_in: CreateSchemaType) -> ModelType:
		"""Create a new record from a Pydantic schema."""
		obj_in_data: Dict[str, Any] = obj_in.model_dump(exclude_unset=True) if isinstance(obj_in, BaseModel) else dict(obj_in)
		db_obj = self.model(**obj_in_data)  # type: ignore[arg-type]
		try:
			db.add(db_obj)
			db.commit()
			db.refresh(db_obj)
		except Exception:
			db.rollback()
			raise
		return db_obj

	# ----- Update -----
	def update(
		self,
		db: Session,
		*,
		db_obj: ModelType,
		obj_in: Union[UpdateSchemaType, Dict[str, Any]],
	) -> ModelType:
		"""Update a record with fields from a Pydantic schema or dict."""
		update_data = obj_in.model_dump(exclude_unset=True) if isinstance(obj_in, BaseModel) else dict(obj_in)

		for field, value in update_data.items():
			if hasattr(db_obj, field):
				setattr(db_obj, field, value)

		try:
			db.add(db_obj)
			db.commit()
			db.refresh(db_obj)
		except Exception:
			db.rollback()
			raise
		return db_obj

	# ----- Delete -----
	def delete(self, db: Session, *, id: Any) -> Optional[ModelType]:
		"""Delete a record.

		Prefer soft-delete if the model has an `is_active` field; otherwise hard delete.
		Returns the affected object (or None if not found).
		"""
		db_obj = self.get(db, id)
		if not db_obj:
			return None

		try:
			if hasattr(db_obj, "is_active"):
				setattr(db_obj, "is_active", False)
				db.add(db_obj)
			else:
				db.delete(db_obj)
			db.commit()
			if hasattr(db_obj, "is_active"):
				db.refresh(db_obj)
		except Exception:
			db.rollback()
			raise
		return db_obj
