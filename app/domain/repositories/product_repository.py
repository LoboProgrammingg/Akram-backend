"""
Product Repository Interface.
Defines specific data access operations for Products.
"""

from typing import List, Dict, Any, Protocol
from datetime import date
from app.domain.repositories.base import BaseRepository
from app.domain.models.product import Product
from app.domain.schemas.product import ProductFilter, ProductStats


class ProductRepository(BaseRepository[Product]):
    """Interface for Product-specific operations."""

    def get_with_filters(self, filters: ProductFilter) -> Dict[str, Any]:
        """Get products with complex filtering and pagination."""
        ...

    def get_stats(self) -> ProductStats:
        """Get dashboard statistics."""
        ...

    def get_muito_critico(self) -> List[Product]:
        """Get products with 'Muito Critico' classification."""
        ...

    def get_critico(self) -> List[Product]:
        """Get products with 'Critico' classification."""
        ...

    def get_atencao(self) -> List[Product]:
        """Get products with 'Atencao' classification."""
        ...

    def get_all_for_indexing(self, upload_id: int | None = None) -> List[Product]:
        """Get all products for RAG indexing, optionally filtered by upload."""
        ...

    def get_chart_data_by_classe(self) -> List[Dict[str, Any]]:
        """Get product count and cost by class."""
        ...

    def get_chart_data_by_filial(self) -> List[Dict[str, Any]]:
        """Get product count and cost by filial."""
        ...

    def get_chart_data_expiry_timeline(self, days: int = 30) -> List[Dict[str, Any]]:
        """Get product expiry timeline."""
        ...

    def get_filter_options(self) -> Dict[str, List[str]]:
        """Get distinct values for filter dropdowns."""
        ...
