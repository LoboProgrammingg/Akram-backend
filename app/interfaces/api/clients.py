"""Client API routes — list, filter, stats, and charts for clients."""

from fastapi import APIRouter, Depends

from app.interfaces.api.deps import get_current_user
from app.interfaces.deps import get_client_repository
from app.domain.repositories.client_repository import ClientRepository
from app.domain.models.user import User
from app.domain.schemas.client import ClientFilter
from app.application.services.client_service import (
    get_clients,
    get_client_stats,
    get_inactive_clients,
    get_chart_data_by_estado,
    get_chart_data_inactivity_distribution,
    get_chart_data_by_cidade,
    get_client_filter_options,
)

router = APIRouter(prefix="/api/clients", tags=["Clients"])


@router.get("")
def list_clients(
    estado: str = None,
    cidade: str = None,
    cod_rede: int = None,
    page: int = 1,
    page_size: int = 50,
    repo: ClientRepository = Depends(get_client_repository),
    user: User = Depends(get_current_user),
):
    """List clients with filtering and pagination."""
    filters = ClientFilter(
        estado=estado,
        cidade=cidade,
        cod_rede=cod_rede,
        page=page,
        page_size=page_size,
    )
    return get_clients(repo, filters)


@router.get("/stats")
def client_stats(
    repo: ClientRepository = Depends(get_client_repository),
    user: User = Depends(get_current_user),
):
    """Get client dashboard statistics."""
    return get_client_stats(repo)


@router.get("/inactive")
def inactive_clients(
    days: int = 30,
    repo: ClientRepository = Depends(get_client_repository),
    user: User = Depends(get_current_user),
):
    """Get clients inactive for more than N days."""
    return get_inactive_clients(repo, days)


@router.get("/filters")
def client_filter_options(
    repo: ClientRepository = Depends(get_client_repository),
    user: User = Depends(get_current_user),
):
    """Get distinct values for client filter dropdowns."""
    return get_client_filter_options(repo)


@router.get("/summary")
def client_summary(
    repo: ClientRepository = Depends(get_client_repository),
    user: User = Depends(get_current_user),
):
    """Get all client dashboard data in a single request."""
    stats = get_client_stats(repo)
    by_estado = get_chart_data_by_estado(repo)
    inactivity = get_chart_data_inactivity_distribution(repo)
    by_cidade = get_chart_data_by_cidade(repo)

    return {
        "stats": stats,
        "charts": {
            "by_estado": by_estado,
            "inactivity_distribution": inactivity,
            "by_cidade": by_cidade,
        },
    }
