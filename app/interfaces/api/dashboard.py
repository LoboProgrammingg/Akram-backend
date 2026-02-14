"""Dashboard API — aggregated stats for the frontend dashboard."""

from fastapi import APIRouter, Depends

from app.interfaces.api.deps import get_current_user
from app.interfaces.deps import get_product_repository
from app.domain.repositories.product_repository import ProductRepository
from app.domain.models.user import User
from app.application.services.product_service import (
    get_product_stats,
    get_chart_data_by_classe,
    get_chart_data_by_filial,
    get_chart_data_expiry_timeline,
)

router = APIRouter(prefix="/api/dashboard", tags=["Dashboard"])


@router.get("/summary")
def dashboard_summary(
    repo: ProductRepository = Depends(get_product_repository),
    user: User = Depends(get_current_user),
):
    """Get all dashboard data in a single request."""
    stats = get_product_stats(repo)
    by_classe = get_chart_data_by_classe(repo)
    by_filial = get_chart_data_by_filial(repo)
    expiry = get_chart_data_expiry_timeline(repo)

    return {
        "stats": stats,
        "charts": {
            "by_classe": by_classe,
            "by_filial": by_filial,
            "expiry_timeline": expiry,
        },
    }
