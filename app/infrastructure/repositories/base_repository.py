"""
SQLAlchemy implementation of the Base Repository.
"""

from typing import Any, Generic, List, Optional, Type, TypeVar

from sqlalchemy.orm import Session
from app.domain.repositories.base import BaseRepository
from app.infrastructure.database import Base

ModelType = TypeVar("ModelType", bound=Base)


class SQLAlchemyRepository(BaseRepository[ModelType], Generic[ModelType]):
    """Generic repository implementation for SQLAlchemy models."""

    def __init__(self, db: Session, model: Type[ModelType]):
        self.db = db
        self.model = model

    def get_by_id(self, id: int) -> Optional[ModelType]:
        return self.db.query(self.model).filter(self.model.id == id).first()

    def list(self, skip: int = 0, limit: int = 100) -> List[ModelType]:
        return self.db.query(self.model).offset(skip).limit(limit).all()

    def create(self, obj_in: Any) -> ModelType:
        # Assuming obj_in is a dict or pydantic model
        if hasattr(obj_in, "dict"):
            obj_data = obj_in.dict(exclude_unset=True)
        else:
            obj_data = obj_in
            
        db_obj = self.model(**obj_data)
        self.db.add(db_obj)
        self.db.commit()
        self.db.refresh(db_obj)
        return db_obj

    def update(self, db_obj: ModelType, obj_in: Any) -> ModelType:
        if hasattr(obj_in, "dict"):
            update_data = obj_in.dict(exclude_unset=True)
        else:
            update_data = obj_in

        # Helper for pydantic models or dicts
        for field in update_data:
            if hasattr(db_obj, field):
                setattr(db_obj, field, update_data[field])

        self.db.add(db_obj)
        self.db.commit()
        self.db.refresh(db_obj)
        return db_obj

    def delete(self, id: int) -> Optional[ModelType]:
        obj = self.db.query(self.model).get(id)
        if obj:
            self.db.delete(obj)
            self.db.commit()
        return obj
