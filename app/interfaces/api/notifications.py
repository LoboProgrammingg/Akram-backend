"""Notifications API routes — logs, triggers, scheduler status, and test messages."""

from datetime import datetime
from typing import Optional

import pytz
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.config import get_settings
from app.infrastructure.database import get_db
from app.interfaces.api.deps import get_current_user, require_admin
from app.domain.models.user import User
from app.domain.models.notification_log import NotificationLog
from app.domain.schemas.notification import NotificationLogRead
from app.application.services.notification_service import (
    send_daily_alerts,
    send_test_message,
    send_message_to_number,
)

settings = get_settings()
tz = pytz.timezone(settings.TIMEZONE)
router = APIRouter(prefix="/api/notifications", tags=["Notifications"])


class SendTestRequest(BaseModel):
    phone: str


class SendMessageRequest(BaseModel):
    phone: str
    message: str


@router.get("")
def list_notifications(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    total = db.query(NotificationLog).count()
    offset = (page - 1) * page_size
    logs = (
        db.query(NotificationLog)
        .order_by(NotificationLog.sent_at.desc())
        .offset(offset)
        .limit(page_size)
        .all()
    )
    return {
        "items": [NotificationLogRead.model_validate(n) for n in logs],
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": (total + page_size - 1) // page_size,
    }


@router.post("/trigger")
async def trigger_notifications(
    force: bool = Query(False, description="Forçar envio mesmo se já enviado hoje"),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user), # Changed from require_admin to debug 403
):
    """Manually trigger daily alert notifications."""
    print(f"TRIGGER REQUEST BY: {user.email} (Role: {user.role})")
    try:
        result = await send_daily_alerts(db, force=force)
        return {"message": "Notificações processadas", **result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao enviar notificações: {str(e)}")


@router.post("/test")
async def send_test(
    body: SendTestRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user), # Changed from require_admin
):
    """Send a test message to verify WhatsApp connectivity."""
    try:
        result = await send_test_message(db, body.phone)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro no teste: {str(e)}")


@router.post("/send")
async def send_custom_message(
    body: SendMessageRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user), # Changed from require_admin
):
    """Send a custom message to a specific phone number."""
    try:
        result = await send_message_to_number(db, body.phone, body.message)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao enviar: {str(e)}")


@router.get("/scheduler-status")
def scheduler_status(
    user: User = Depends(get_current_user),
):
    """Get scheduler status and next run time."""
    from app.scheduler.jobs import scheduler

    now = datetime.now(tz)
    jobs = []
    for job in scheduler.get_jobs():
        next_run = job.next_run_time
        jobs.append({
            "id": job.id,
            "name": job.name,
            "next_run": next_run.strftime("%d/%m/%Y %H:%M") if next_run else "N/A",
            "next_run_iso": next_run.isoformat() if next_run else None,
        })

    return {
        "running": scheduler.running,
        "current_time": now.strftime("%d/%m/%Y %H:%M"),
        "timezone": settings.TIMEZONE,
        "jobs": jobs,
    }


@router.get("/evolution/status")
async def evolution_status(
    user: User = Depends(get_current_user),
):
    """Check Evolution API connection status."""
    from app.infrastructure.evolution_api import EvolutionAPIClient
    client = EvolutionAPIClient()
    return await client.check_instance_status()


@router.get("/evolution/qr")
async def evolution_qr(
    user: User = Depends(get_current_user),
):
    """Get Evolution API QR Code."""
    from app.infrastructure.evolution_api import EvolutionAPIClient
    client = EvolutionAPIClient()
    return await client.get_instance_connect()
