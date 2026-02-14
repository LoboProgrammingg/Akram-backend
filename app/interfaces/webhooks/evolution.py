"""Evolution API webhook — receives incoming WhatsApp messages for AI queries."""

import logging

from fastapi import APIRouter, Depends, Request, HTTPException
from sqlalchemy.orm import Session

from app.infrastructure.database import get_db
from app.domain.models.phone_number import PhoneNumber
from app.domain.models.notification_log import NotificationLog
from app.rag.chain import query_rag
from app.application.services.notification_service import send_message_to_number

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/webhooks", tags=["Webhooks"])


@router.post("/evolution")
async def evolution_webhook(request: Request, db: Session = Depends(get_db)):
    """
    Receive incoming WhatsApp messages from Evolution API 1.8.2.
    Routes authorized messages to the RAG system and responds.
    """
    try:
        body = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON body")

    # Evolution API 1.8.2 webhook structure
    event = body.get("event")
    
    # We only care about new messages
    if event != "messages.upsert":
        return {"status": "ignored", "event": event}

    data = body.get("data", {})
    key = data.get("key", {})
    message_data = data.get("message", {})
    message_type = data.get("messageType", "")

    # Ignore outgoing messages (fromMe)
    if key.get("fromMe", False):
        return {"status": "ignored", "reason": "outgoing"}

    # Ignore status updates (stories) or groups (if configured not to, but usually valid JID check handles it)
    # Status updates usually have 'status@broadcast' or similar
    remote_jid = key.get("remoteJid", "")
    if "status@broadcast" in remote_jid:
        return {"status": "ignored", "reason": "status_broadcast"}
    
    # Process only text messages for now
    if message_type not in ["conversation", "extendedTextMessage"]:
        return {"status": "ignored", "reason": "not_text_message"}

    # Extract sender phone
    sender_phone = remote_jid.split("@")[0] if "@" in remote_jid else remote_jid

    # Get message text
    message_text = (
        message_data.get("conversation")
        or message_data.get("extendedTextMessage", {}).get("text")
        or ""
    )

    if not message_text:
        return {"status": "ignored", "reason": "empty_text"}

    # Authorization Check
    # Ensure exact match or robust suffix match
    # Removing country code might be risky if not standardized, but usually safe to match end
    authorized = db.query(PhoneNumber).filter(
        PhoneNumber.number == sender_phone, # Try exact match first
        PhoneNumber.is_active == True,
    ).first()

    if not authorized:
         # Try matching with/without 55 
         # (If stored as 55..., and incoming is 55...) - covered by exact
         # If incoming is without 55 (unlikely from API but possible)
         pass

    if not authorized or not authorized.can_query_ai:
        logger.warning(f"Unauthorized/Disabled AI query from: {sender_phone}")
        # SILENTLY IGNORE to prevent spam wars
        return {"status": "ignored", "reason": "unauthorized"}

    # Query RAG
    logger.info(f"WhatsApp AI query from {sender_phone}: {message_text[:100]}")
    
    try:
        from app.rag.chain import query_rag
        answer = query_rag(message_text, use_whatsapp_format=True)
    except Exception as e:
        logger.error(f"RAG Error: {e}")
        answer = "Desculpe, estou enfrentando problemas técnicos no momento."

    # Send response
    try:
        await send_message_to_number(db, sender_phone, answer)
    except Exception as e:
        logger.error(f"Failed to send reply: {e}")

    return {"status": "processed", "query": message_text[:50]}
