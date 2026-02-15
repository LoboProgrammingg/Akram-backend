"""Dashboard API — aggregated stats for the frontend dashboard."""

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
)
from app.application.services.client_service import (
    get_client_stats,
    get_client_charts,
)
from app.config import get_settings

settings = get_settings()
tz = pytz.timezone(settings.TIMEZONE)
router = APIRouter(prefix="/api/dashboard", tags=["Dashboard"])


def _get_notification_stats(db: Session) -> dict:
    """Aggregate notification stats from notification_log table."""
    now = datetime.now(tz)
    today = now.date()
    seven_days_ago = today - timedelta(days=7)

    # Sent today (all types)
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

    # Breakdown by type (last 7d)
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

    by_type = {}
    for row in by_type_rows:
        ntype = row.notification_type or "vendor"
        if ntype not in by_type:
            by_type[ntype] = {"sent": 0, "failed": 0, "pending": 0}
        by_type[ntype][row.status] = row.count

    return {
        "sent_today": sent_today,
        "sent_7d": sent_7d,
        "failed_7d": failed_7d,
        "by_type": by_type,
    }


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

    # Clients
    client_stats = get_client_stats(client_repo)
    client_charts = get_client_charts(client_repo)

    # Notifications
    notification_stats = _get_notification_stats(db)

    return {
        "products": {
            "stats": product_stats,
            "charts": {
                "by_classe": by_classe,
                "by_filial": by_filial,
                "expiry_timeline": expiry,
            },
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
        },
    }
