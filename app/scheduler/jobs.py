"""APScheduler jobs — vendor alerts every 30 mins, client alerts once daily at 09:00."""

import asyncio
import logging
from datetime import datetime

import pytz
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.triggers.cron import CronTrigger

from app.config import get_settings
from app.infrastructure.database import SessionLocal

settings = get_settings()
logger = logging.getLogger(__name__)
tz = pytz.timezone(settings.TIMEZONE)

scheduler = AsyncIOScheduler(timezone=tz)


async def periodic_alert_job():
    """Periodic job: send vendor alerts based on contact preferences every 30 mins."""
    from app.application.services.notification_service import send_daily_alerts

    logger.info(f"Running periodic vendor alert job at {datetime.now(tz).strftime('%d/%m/%Y %H:%M')}")

    db = SessionLocal()
    try:
        from app.domain.models.product import Product
        from app.infrastructure.repositories.product_repository import SQLAlchemyProductRepository
        
        repo = SQLAlchemyProductRepository(db, Product)
        result = await send_daily_alerts(db, repo)
        logger.info(f"Vendor alert result: {result}")
    except Exception as e:
        logger.error(f"Vendor alert job failed: {e}")
    finally:
        db.close()


async def daily_client_alert_job():
    """Periodic job: send product alerts to inactive clients (hourly 09:00-18:00)."""
    from app.application.services.client_notification_service import send_client_alerts

    logger.info(f"Running periodic client alert job at {datetime.now(tz).strftime('%d/%m/%Y %H:%M')}")

    db = SessionLocal()
    try:
        from app.domain.models.product import Product
        from app.domain.models.client import Client
        from app.infrastructure.repositories.product_repository import SQLAlchemyProductRepository
        from app.infrastructure.repositories.client_repository import SQLAlchemyClientRepository

        product_repo = SQLAlchemyProductRepository(db, Product)
        client_repo = SQLAlchemyClientRepository(db, Client)
        
        # Limit 100 per run
        result = await send_client_alerts(db, product_repo, client_repo, limit=100)
        logger.info(f"Client alert result: {result}")
    except Exception as e:
        logger.error(f"Client alert job failed: {e}")
    finally:
        db.close()


def start_scheduler():
    """Start the APScheduler with vendor (30-min) and client (daily 09:00) jobs."""
    # Vendor alerts — every 30 minutes
    scheduler.add_job(
        periodic_alert_job,
        trigger=IntervalTrigger(minutes=30, timezone=tz),
        id="periodic_vendor_alert",
        name="Vendor Alert (Every 30 mins)",
        replace_existing=True,
    )

    # Client alerts — hourly between 09:00 and 18:00
    scheduler.add_job(
        daily_client_alert_job,
        trigger=CronTrigger(hour="9-18", minute=0, timezone=tz),
        id="periodic_client_alert",
        name="Client Alert (Hourly 09:00-18:00)",
        replace_existing=True,
    )

    scheduler.start()
    logger.info(f"Scheduler started — vendor alerts every 30 mins, client alerts daily at 09:00 {settings.TIMEZONE}")


def stop_scheduler():
    """Stop the scheduler gracefully."""
    if scheduler.running:
        scheduler.shutdown(wait=False)
        logger.info("Scheduler stopped")

