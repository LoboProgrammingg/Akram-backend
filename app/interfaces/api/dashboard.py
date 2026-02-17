"""Dashboard API — aggregated stats for the frontend dashboard."""

import logging
from datetime import datetime, timedelta

import pytz
from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.interfaces.api.deps import get_current_user
from app.interfaces.deps import get_product_repository, get_client_repository, get_db
from app.domain.repositories.product_repository import ProductRepository
from app.domain.repositories.client_repository import ClientRepository
from app.domain.models.user import User
from app.domain.models.notification_log import NotificationLog
from app.application.services.product_service import (
    get_product_stats,
    get_chart_data_by_classe,
    get_chart_data_by_filial,
    get_chart_data_expiry_timeline,
    get_chart_data_by_uf,
    get_top_critical_products,
    get_expiry_summary_by_week,
    get_value_summary,
)
from app.application.services.client_service import (
    get_client_stats,
    get_client_charts,
)
from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()
tz = pytz.timezone(settings.TIMEZONE)
router = APIRouter(prefix="/api/dashboard", tags=["Dashboard"])


def _get_notification_stats(db: Session) -> dict:
    """Aggregate notification stats — safe even if notification_type column is missing."""
    try:
        now = datetime.now(tz)
        today = now.date()
        seven_days_ago = today - timedelta(days=7)

        # Sent today
        sent_today = (
            db.query(func.count(NotificationLog.id))
            .filter(
                NotificationLog.status == "sent",
                func.date(NotificationLog.sent_at) == today,
            )
            .scalar()
            or 0
        )

        # Sent last 7 days
        sent_7d = (
            db.query(func.count(NotificationLog.id))
            .filter(
                NotificationLog.status == "sent",
                func.date(NotificationLog.sent_at) >= seven_days_ago,
            )
            .scalar()
            or 0
        )

        # Failed last 7 days
        failed_7d = (
            db.query(func.count(NotificationLog.id))
            .filter(
                NotificationLog.status == "failed",
                func.date(NotificationLog.sent_at) >= seven_days_ago,
            )
            .scalar()
            or 0
        )

        # Breakdown by type — wrapped in try/except for missing column
        by_type: dict = {}
        try:
            by_type_rows = (
                db.query(
                    NotificationLog.notification_type,
                    NotificationLog.status,
                    func.count(NotificationLog.id).label("count"),
                )
                .filter(func.date(NotificationLog.sent_at) >= seven_days_ago)
                .group_by(NotificationLog.notification_type, NotificationLog.status)
                .all()
            )
            for row in by_type_rows:
                ntype = row.notification_type or "vendor"
                if ntype not in by_type:
                    by_type[ntype] = {"sent": 0, "failed": 0, "pending": 0}
                by_type[ntype][row.status] = row.count
        except Exception as e:
            logger.warning(f"Could not get notification breakdown by type: {e}")
            db.rollback()

        return {
            "sent_today": sent_today,
            "sent_7d": sent_7d,
            "failed_7d": failed_7d,
            "by_type": by_type,
        }
    except Exception as e:
        logger.error(f"Error getting notification stats: {e}")
        try:
            db.rollback()
        except Exception:
            pass
        return {"sent_today": 0, "sent_7d": 0, "failed_7d": 0, "by_type": {}}


@router.get("/summary")
def dashboard_summary(
    db: Session = Depends(get_db),
    product_repo: ProductRepository = Depends(get_product_repository),
    client_repo: ClientRepository = Depends(get_client_repository),
    user: User = Depends(get_current_user),
):
    """Get unified dashboard data: products + clients + notifications."""

    # Products
    product_stats = get_product_stats(product_repo)
    by_classe = get_chart_data_by_classe(product_repo)
    by_filial = get_chart_data_by_filial(product_repo)
    expiry = get_chart_data_expiry_timeline(product_repo)
    by_uf = get_chart_data_by_uf(product_repo)
    top_critical = get_top_critical_products(product_repo, limit=10)
    expiry_by_week = get_expiry_summary_by_week(product_repo, weeks=4)
    value_summary = get_value_summary(product_repo)

    # Clients (safe fallback)
    try:
        client_stats_obj = get_client_stats(client_repo)
        # Convert Pydantic model to dict for JSON serialization
        client_stats = client_stats_obj.model_dump() if hasattr(client_stats_obj, 'model_dump') else client_stats_obj
    except Exception as e:
        logger.error(f"Error getting client stats: {e}")
        client_stats = {
            "total_clients": 0, "inactive_30d": 0, "inactive_60d": 0,
            "inactive_90d": 0, "sem_data": 0, "estados": [], "cidades_count": 0,
        }

    try:
        client_charts = get_client_charts(client_repo)
    except Exception as e:
        logger.error(f"Error getting client charts: {e}")
        client_charts = {"inactivity_distribution": [], "by_estado": [], "by_cidade": []}

    # Notifications
    notification_stats = _get_notification_stats(db)

    return {
        "products": {
            "stats": product_stats,
            "charts": {
                "by_classe": by_classe,
                "by_filial": by_filial,
                "expiry_timeline": expiry,
                "by_uf": by_uf,
                "expiry_by_week": expiry_by_week,
            },
            "top_critical": top_critical,
            "value_summary": value_summary,
        },
        "clients": {
            "stats": client_stats,
            "charts": client_charts,
        },
        "notifications": notification_stats,
        # Backward compatible flat keys
        "stats": product_stats,
        "charts": {
            "by_classe": by_classe,
            "by_filial": by_filial,
            "expiry_timeline": expiry,
            "by_uf": by_uf,
            "expiry_by_week": expiry_by_week,
        },
        "top_critical": top_critical,
        "value_summary": value_summary,
    }
