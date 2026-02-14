"""Dashboard API — aggregated stats for the frontend dashboard."""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.infrastructure.database import get_db
from app.interfaces.api.deps import get_current_user
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
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Get all dashboard data in a single request."""
    stats = get_product_stats(db)
    by_classe = get_chart_data_by_classe(db)
    by_filial = get_chart_data_by_filial(db)
    expiry = get_chart_data_expiry_timeline(db)

    return {
        "stats": stats,
        "charts": {
            "by_classe": by_classe,
            "by_filial": by_filial,
            "expiry_timeline": expiry,
        },
    }
