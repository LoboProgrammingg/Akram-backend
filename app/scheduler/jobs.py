"""APScheduler jobs — daily notifications at 08:00 America/Cuiaba."""

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
    """Periodic job: send alerts based on contact preferences every 30 mins."""
    from app.application.services.notification_service import send_daily_alerts

    logger.info(f"Running periodic alert job at {datetime.now(tz).strftime('%d/%m/%Y %H:%M')}")

    db = SessionLocal()
    try:
        result = await send_daily_alerts(db)
        logger.info(f"Periodic alert result: {result}")
    except Exception as e:
        logger.error(f"Periodic alert job failed: {e}")
    finally:
        db.close()


def start_scheduler():
    """Start the APScheduler with periodic alert job."""
    scheduler.add_job(
        periodic_alert_job,
        trigger=IntervalTrigger(minutes=30, timezone=tz),
        id="periodic_critical_products_alert",
        name="Periodic Critical Products Alert (Every 30 mins)",
        replace_existing=True,
    )
    scheduler.start()
    logger.info(f"Scheduler started — daily alert at 08:00 {settings.TIMEZONE}")


def stop_scheduler():
    """Stop the scheduler gracefully."""
    if scheduler.running:
        scheduler.shutdown(wait=False)
        logger.info("Scheduler stopped")
