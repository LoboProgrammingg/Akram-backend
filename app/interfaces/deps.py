"""
API Dependencies.
"""

from typing import Generator

from fastapi import Depends
from sqlalchemy.orm import Session

from app.infrastructure.database import SessionLocal
from app.domain.models.product import Product
from app.domain.repositories.product_repository import ProductRepository
from app.infrastructure.repositories.product_repository import SQLAlchemyProductRepository


from app.infrastructure.database import SessionLocal, get_db


def get_product_repository(db: Session = Depends(get_db)) -> ProductRepository:
    """Get product repository instance."""
    return SQLAlchemyProductRepository(db, Product)
