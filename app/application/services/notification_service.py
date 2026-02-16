"""Notification service — sends messages via Evolution API 1.8.2.

Features:
- Message splitting for large product lists (WhatsApp char limit)
- Duplicate notification prevention (per-day tracking)
- Daily alert formatting with emojis
- Single message sending with logging
"""

from datetime import datetime, date
from typing import Optional
import json

import pytz
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.config import get_settings
from app.domain.models.notification_log import NotificationLog
from app.domain.models.phone_number import PhoneNumber
from app.domain.models.product import Product
from app.domain.repositories.product_repository import ProductRepository
from app.infrastructure.evolution_api import EvolutionAPIClient

settings = get_settings()
tz = pytz.timezone(settings.TIMEZONE)

MAX_MESSAGE_LENGTH = 4000  # WhatsApp safe limit
PRODUCTS_PER_MESSAGE = 25  # Split large lists


def format_critical_products_message(products: list[Product], part: int = 0, total_parts: int = 1, start_index: int = 1) -> str:
    """Format the daily alert message for critical products."""
    now = datetime.now(tz)
    date_str = now.strftime("%d/%m/%Y")
    time_str = now.strftime("%H:%M")

    lines = [
        "🚨 *ALERTA DE PRODUTOS* 🚨",
        "",
        f"📅 {date_str} às {time_str}",
    ]

    if total_parts > 1:
        lines.append(f"📋 Parte {part + 1} de {total_parts}")

    lines.extend([
        f"📊 {len(products)} produto{'s' if len(products) > 1 else ''}",
        "",
        "━" * 30,
    ])

    last_class_label = None

    for i, p in enumerate(products, start_index):
        # Determine emoji and label based on class
        p_class = (p.classe or "").upper()
        if "MUITO" in p_class:
            emoji = "⚫" # BLACK - MUITO CRITICO
            class_label = "MUITO CRÍTICO"
        elif "CRITICO" in p_class or "CRÍTICO" in p_class:
            emoji = "🔴" # RED - CRITICO
            class_label = "CRÍTICO"
        elif "TEN" in p_class: # ATENCAO / ATENÇÃO
            emoji = "🟡" # YELLOW - ATENÇÃO
            class_label = "ATENÇÃO"
        else:
            emoji = "⚪"
            class_label = p.classe or "OUTROS"
        
        # Insert Header if class changes (or start of message)
        if class_label != last_class_label:
            lines.append("")
            lines.append(f"🏷️ *{class_label}*")
            lines.append("─" * 20)
            last_class_label = class_label

        validade_str = p.validade.strftime("%d/%m/%Y") if p.validade else "N/A"
        custo_unitario = p.preco_com_st or 0
        custo_str = f"R$: {custo_unitario:,.2f}"

        lines.extend([
            f"{emoji} *{i}. {p.descricao}*",
            f"   📦 Cód: {p.codigo} | 📦 Emb: {p.embalagem or '—'}",
            f"   📅 Vence: {validade_str} | 📊 Qtd: {p.quantidade or 0}",
            f"   💰 *Valor: {custo_str}* | 🏪 {p.filial or '—'}",
        ])

    lines.extend([
        "",
        "━" * 30,
        "",
        "🤖 _Enviado automaticamente pelo Akram Monitor_"
    ])

    return "\n".join(lines)


def _was_notified_today(db: Session, phone: str) -> bool:
    """Check if alerts were already sent to this number today."""
    today = datetime.now(tz).date()
    count = (
        db.query(func.count(NotificationLog.id))
        .filter(
            NotificationLog.phone == phone,
            NotificationLog.status == "sent",
            NotificationLog.direction == "outbound",
            func.date(NotificationLog.sent_at) == today,
        )
        .scalar()
    )
    return (count or 0) > 0




async def send_daily_alerts(db: Session, repo: ProductRepository, force: bool = False):
    """Send periodic alerts based on contact preferences to active phone numbers.
    
    Args:
        db: Database session for logs and phone numbers.
        repo: Product repository for fetching products.
        force: If True, skip duplicate check and send even if already sent today.
    """
    # 1. Fetch all product categories once
    upload_id = repo.get_latest_upload_id()
    if not upload_id:
        return {"sent": 0, "skipped": 0, "message": "Nenhum arquivo processado encontrado"}

    products_map = {
        "MUITO CRÍTICO": repo.get_muito_critico(upload_id),
        "CRITICO": repo.get_critico(upload_id),
        "ATENÇÃO": repo.get_atencao(upload_id),
    }

    # 2. Get all active phone numbers
    phone_numbers = db.query(PhoneNumber).filter(PhoneNumber.is_active == True).all()
    if not phone_numbers:
        return {"sent": 0, "skipped": 0, "message": "Nenhum número ativo cadastrado"}

    client = EvolutionAPIClient()
    sent_count = 0
    skipped_count = 0
    errors = []

    for phone in phone_numbers:
        # 3. Determine which products this contact should receive
        try:
            # Default to ALL if null or empty
            user_types = json.loads(phone.notification_types) if phone.notification_types else ["MUITO CRÍTICO", "CRITICO", "ATENÇÃO"]
            if not isinstance(user_types, list):
                user_types = ["MUITO CRÍTICO"]
        except:
            user_types = ["MUITO CRÍTICO"] # Fallback

        contact_products = []
        for p_type in user_types:
            if p_type in products_map:
                contact_products.extend(products_map[p_type])

        # Deduplicate products by id (in case of overlap, though unlikely with strict classes)
        # Using dict to preserve order and uniqueness
        unique_products = {p.id: p for p in contact_products}.values()
        contact_products = list(unique_products)

        if not contact_products:
            skipped_count += 1
            continue

        # 4. Check if already notified today (per contact)
        # NOTE: With 30-min run, we MUST check if we sent ANY message to this phone today
        # If we want to allow multiple updates per day (e.g. new products), logic needs to be smarter.
        # For now, adhering to "don't spam" rule: 1 message set per day per contact.
        if not force and _was_notified_today(db, phone.number):
            skipped_count += 1
            continue

        # 5. Split and Send
        chunks = [contact_products[i:i + PRODUCTS_PER_MESSAGE] for i in range(0, len(contact_products), PRODUCTS_PER_MESSAGE)]
        
        for chunk_idx, chunk in enumerate(chunks):
            # We use the generic formatter but could customize based on types if needed
            # Calculate start index for continuous numbering
            start_index = (chunk_idx * PRODUCTS_PER_MESSAGE) + 1
            
            message = format_critical_products_message(
                chunk, part=chunk_idx, total_parts=len(chunks), start_index=start_index
            )

            log = NotificationLog(
                phone=phone.number,
                message=message[:500] + "..." if len(message) > 500 else message,
                status="pending",
                direction="outbound",
            )
            db.add(log)

            try:
                await client.send_text(phone.number, message)
                log.status = "sent"
                sent_count += 1
            except Exception as e:
                log.status = "failed"
                log.error = str(e)[:500]
                errors.append({"phone": phone.number, "error": str(e)})

            db.commit()

    return {
        "sent": sent_count,
        "skipped": skipped_count,
        "total_phones": len(phone_numbers),
        "errors": errors,
    }


async def send_message_to_number(db: Session, phone: str, message: str) -> dict:
    """Send a single message to a specific phone number."""
    client = EvolutionAPIClient()

    log = NotificationLog(
        phone=phone,
        message=message[:500],
        status="pending",
        direction="outbound",
    )
    db.add(log)

    try:
        await client.send_text(phone, message)
        log.status = "sent"
        db.commit()
        return {"status": "sent", "phone": phone}
    except Exception as e:
        log.status = "failed"
        log.error = str(e)[:500]
        db.commit()
        return {"status": "failed", "phone": phone, "error": str(e)}


async def send_test_message(db: Session, phone: str) -> dict:
    """Send a test message to verify WhatsApp connectivity."""
    now = datetime.now(tz)
    message = (
        "✅ *Akram Monitor — Teste de Conexão*\n\n"
        f"📅 {now.strftime('%d/%m/%Y')} às {now.strftime('%H:%M')}\n\n"
        "Este é um teste do sistema de monitoramento.\n"
        "Se você recebeu esta mensagem, a integração está funcionando! 🎉\n\n"
        "_Enviado pelo Akram Monitor_"
    )
    return await send_message_to_number(db, phone, message)
