"""Product service — business logic for product queries and stats."""

from typing import Dict, List, Any

from app.domain.repositories.product_repository import ProductRepository
from app.domain.schemas.product import ProductFilter, ProductStats
from app.domain.models.product import Product


def get_products(repo: ProductRepository, filters: ProductFilter) -> Dict[str, Any]:
    """Get products with filtering and pagination."""
    upload_id = repo.get_latest_upload_id()
    if not upload_id:
        return {"items": [], "total": 0, "page": 1, "page_size": 10, "total_pages": 0}
    return repo.get_with_filters(filters, upload_id)


def get_product_stats(repo: ProductRepository) -> ProductStats:
    """Get dashboard statistics."""
    upload_id = repo.get_latest_upload_id()
    if not upload_id:
        return ProductStats(
            total_products=0, total_muito_critico=0, total_critico=0, total_vencido=0,
            total_custo=0, total_custo_muito_critico=0, filiais=[], classes=[]
        )
    return repo.get_stats(upload_id)


def get_muito_critico_products(repo: ProductRepository) -> List[Product]:
    """Get all products with Classe == 'Muito Critico' for notifications."""
    upload_id = repo.get_latest_upload_id()
    if not upload_id:
        return []
    return repo.get_muito_critico(upload_id)


def get_critico_products(repo: ProductRepository) -> List[Product]:
    """Get all products with Classe == 'Critico' (excluding Muito Critico)."""
    upload_id = repo.get_latest_upload_id()
    if not upload_id:
        return []
    return repo.get_critico(upload_id)


def get_atencao_products(repo: ProductRepository) -> List[Product]:
    """Get all products with Classe == 'Atencao' or 'Atenção'."""
    upload_id = repo.get_latest_upload_id()
    if not upload_id:
        return []
    return repo.get_atencao(upload_id)


def get_chart_data_by_classe(repo: ProductRepository) -> List[Dict[str, Any]]:
    """Get product count and total cost grouped by Classe."""
    upload_id = repo.get_latest_upload_id()
    if not upload_id:
        return []
    return repo.get_chart_data_by_classe(upload_id)


def get_chart_data_by_filial(repo: ProductRepository) -> List[Dict[str, Any]]:
    """Get product count grouped by Filial."""
    upload_id = repo.get_latest_upload_id()
    if not upload_id:
        return []
    return repo.get_chart_data_by_filial(upload_id)


def get_chart_data_expiry_timeline(repo: ProductRepository) -> List[Dict[str, Any]]:
    """Get product count grouped by expiry date (next 30 days)."""
    upload_id = repo.get_latest_upload_id()
    if not upload_id:
        return []
    return repo.get_chart_data_expiry_timeline(upload_id=upload_id)


def get_filter_options(repo: ProductRepository) -> Dict[str, List[str]]:
    """Get all distinct values for filter dropdowns."""
    upload_id = repo.get_latest_upload_id()
    if not upload_id:
        return {"filiais": [], "classes": [], "ufs": [], "compradores": []}
    return repo.get_filter_options(upload_id)
