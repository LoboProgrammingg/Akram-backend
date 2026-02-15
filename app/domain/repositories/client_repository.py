"""
Client Repository Interface.
Defines specific data access operations for Clients.
"""

from typing import List, Dict, Any

from app.domain.repositories.base import BaseRepository
from app.domain.models.client import Client
from app.domain.schemas.client import ClientFilter, ClientStats


class ClientRepository(BaseRepository[Client]):
    """Interface for Client-specific operations."""

    def get_latest_upload_id(self) -> int | None:
        """Get the ID of the most recent client upload."""
        ...

    def get_with_filters(self, filters: ClientFilter, upload_id: int | None = None) -> Dict[str, Any]:
        """Get clients with complex filtering and pagination."""
        ...

    def get_stats(self, upload_id: int | None = None) -> ClientStats:
        """Get client dashboard statistics."""
        ...

    def get_inactive_clients(self, days: int = 30, upload_id: int | None = None) -> List[Client]:
        """Get clients whose last purchase was more than N days ago."""
        ...

    def get_chart_data_by_estado(self, upload_id: int | None = None) -> List[Dict[str, Any]]:
        """Get client count grouped by state."""
        ...

    def get_chart_data_inactivity_distribution(self, upload_id: int | None = None) -> List[Dict[str, Any]]:
        """Get client count grouped by inactivity range (30d, 60d, 90d, >90d)."""
        ...

    def get_chart_data_by_cidade(self, upload_id: int | None = None, limit: int = 10) -> List[Dict[str, Any]]:
        """Get client count grouped by city (top N)."""
        ...

    def get_filter_options(self, upload_id: int | None = None) -> Dict[str, List[str]]:
        """Get distinct values for filter dropdowns."""
        ...
