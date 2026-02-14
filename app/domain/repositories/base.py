"""
Base Repository Interface.
Defines the standard contract for data access operations.
"""

from typing import Generic, TypeVar, List, Optional, Any, Protocol

T = TypeVar("T")


class BaseRepository(Protocol[T]):
    """Interface for generic CRUD operations."""

    def get_by_id(self, id: int) -> Optional[T]:
        """Get a single entity by ID."""
        ...

    def list(self, skip: int = 0, limit: int = 100) -> List[T]:
        """List entities with pagination."""
        ...

    def create(self, obj_in: Any) -> T:
        """Create a new entity."""
        ...

    def update(self, db_obj: T, obj_in: Any) -> T:
        """Update an existing entity."""
        ...
    
    def delete(self, id: int) -> Optional[T]:
        """Delete an entity by ID."""
        ...
