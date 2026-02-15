"""Client service — business logic for client queries and stats."""

from typing import Dict, List, Any

from app.domain.repositories.client_repository import ClientRepository
from app.domain.schemas.client import ClientFilter, ClientStats
from app.domain.models.client import Client


def get_clients(repo: ClientRepository, filters: ClientFilter) -> Dict[str, Any]:
    """Get clients with filtering and pagination."""
    upload_id = repo.get_latest_upload_id()
    if not upload_id:
        return {"items": [], "total": 0, "page": 1, "page_size": 50, "total_pages": 0}
    return repo.get_with_filters(filters, upload_id)


def get_client_stats(repo: ClientRepository) -> ClientStats:
    """Get client dashboard statistics."""
    upload_id = repo.get_latest_upload_id()
    if not upload_id:
        return ClientStats(
            total_clients=0, inactive_30d=0, inactive_60d=0, inactive_90d=0,
            estados=[], cidades_count=0,
        )
    return repo.get_stats(upload_id)


def get_inactive_clients(repo: ClientRepository, days: int = 30) -> List[Client]:
    """Get clients whose last purchase was more than N days ago."""
    upload_id = repo.get_latest_upload_id()
    if not upload_id:
        return []
    return repo.get_inactive_clients(days, upload_id)


def get_chart_data_by_estado(repo: ClientRepository) -> List[Dict[str, Any]]:
    """Get client count grouped by state."""
    upload_id = repo.get_latest_upload_id()
    if not upload_id:
        return []
    return repo.get_chart_data_by_estado(upload_id)


def get_chart_data_inactivity_distribution(repo: ClientRepository) -> List[Dict[str, Any]]:
    """Get client count grouped by inactivity ranges."""
    upload_id = repo.get_latest_upload_id()
    if not upload_id:
        return []
    return repo.get_chart_data_inactivity_distribution(upload_id)


def get_chart_data_by_cidade(repo: ClientRepository, limit: int = 10) -> List[Dict[str, Any]]:
    """Get client count grouped by city (top N)."""
    upload_id = repo.get_latest_upload_id()
    if not upload_id:
        return []
    return repo.get_chart_data_by_cidade(upload_id, limit)


def get_client_filter_options(repo: ClientRepository) -> Dict[str, List[str]]:
    """Get distinct values for client filter dropdowns."""
    upload_id = repo.get_latest_upload_id()
    if not upload_id:
        return {"estados": [], "cidades": []}
    return repo.get_filter_options(upload_id)
