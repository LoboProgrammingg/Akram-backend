"""Product service — business logic for product queries and stats."""

from typing import Dict, List, Any

from app.domain.repositories.product_repository import ProductRepository
from app.domain.schemas.product import ProductFilter, ProductStats
from app.domain.models.product import Product


def get_products(repo: ProductRepository, filters: ProductFilter) -> Dict[str, Any]:
    """Get products with filtering and pagination."""
    return repo.get_with_filters(filters)


def get_product_stats(repo: ProductRepository) -> ProductStats:
    """Get dashboard statistics."""
    return repo.get_stats()


def get_muito_critico_products(repo: ProductRepository) -> List[Product]:
    """Get all products with Classe == 'Muito Critico' for notifications."""
    return repo.get_muito_critico()


def get_critico_products(repo: ProductRepository) -> List[Product]:
    """Get all products with Classe == 'Critico' (excluding Muito Critico)."""
    return repo.get_critico()


def get_atencao_products(repo: ProductRepository) -> List[Product]:
    """Get all products with Classe == 'Atencao' or 'Atenção'."""
    return repo.get_atencao()


def get_chart_data_by_classe(repo: ProductRepository) -> List[Dict[str, Any]]:
    """Get product count and total cost grouped by Classe."""
    return repo.get_chart_data_by_classe()


def get_chart_data_by_filial(repo: ProductRepository) -> List[Dict[str, Any]]:
    """Get product count grouped by Filial."""
    return repo.get_chart_data_by_filial()


def get_chart_data_expiry_timeline(repo: ProductRepository) -> List[Dict[str, Any]]:
    """Get product count grouped by expiry date (next 30 days)."""
    return repo.get_chart_data_expiry_timeline()


def get_filter_options(repo: ProductRepository) -> Dict[str, List[str]]:
    """Get all distinct values for filter dropdowns."""
    return repo.get_filter_options()
