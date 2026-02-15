"""Client notification service — sends product alerts to inactive clients via Evolution API.

Features:
- Identifies clients inactive for 30+ days (DTULTCOMPRA_GERAL)
- Normalizes phone numbers (adds "55" prefix for Brazilian DDD-only numbers)
- Sends product tables via WhatsApp to their celular
- Robust error handling: skips invalid numbers, logs all attempts
- One notification per client per day
"""

import re
from datetime import datetime
from typing import List, Optional

import pytz
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.config import get_settings
from app.domain.models.client import Client
from app.domain.models.notification_log import NotificationLog
from app.domain.models.product import Product
from app.domain.repositories.client_repository import ClientRepository
from app.domain.repositories.product_repository import ProductRepository
from app.infrastructure.evolution_api import EvolutionAPIClient

settings = get_settings()
tz = pytz.timezone(settings.TIMEZONE)

PRODUCTS_PER_MESSAGE = 15


def normalize_phone(raw: Optional[str]) -> Optional[str]:
    """Normalize a Brazilian phone number for WhatsApp.

    Rules:
    - Strip non-digits
    - If starts with "55" and has 12-13 digits → already correct
    - If 10-11 digits (DDD + number) → prepend "55"
    - If < 10 digits → invalid (returns None)
    - If > 13 digits → invalid (returns None)

    Examples:
        "66996109797"   → "5566996109797"   (11 digits → +55)
        "5566999557737" → "5566999557737"   (13 digits → already has 55)
        "065924198"     → None              (too short after cleanup)
        "VERIFICAR"     → None              (non-numeric)
    """
    if not raw:
        return None

    digits = re.sub(r"\D", "", str(raw).strip())

    if not digits or len(digits) < 10:
        return None  # Too short, can't be valid

    if len(digits) > 13:
        return None  # Too long, likely garbage

    # Already has country code
    if digits.startswith("55") and len(digits) >= 12:
        return digits

    # DDD + number (10 or 11 digits) → add "55"
    if 10 <= len(digits) <= 11:
        return f"55{digits}"

    return None  # Doesn't fit any valid pattern


def format_client_products_message(
    client: Client,
    products: List[Product],
    part: int = 0,
    total_parts: int = 1,
) -> str:
    """Format the product alert message for an inactive client."""
    now = datetime.now(tz)
    date_str = now.strftime("%d/%m/%Y")
    time_str = now.strftime("%H:%M")

    client_name = client.fantasia or client.razao_social or f"Cliente {client.codigo}"
    last_purchase = client.dt_ult_compra.strftime("%d/%m/%Y") if client.dt_ult_compra else "N/A"

    lines = [
        "📋 *AVISO — PRODUTOS DISPONÍVEIS* 📋",
        "",
        f"👤 *{client_name}*",
        f"📅 Última compra: {last_purchase}",
        f"🕐 Enviado em: {date_str} às {time_str}",
    ]

    if total_parts > 1:
        lines.append(f"📄 Parte {part + 1} de {total_parts}")

    lines.extend([
        "",
        f"📊 {len(products)} produto{'s' if len(products) > 1 else ''} em destaque:",
        "",
        "━" * 30,
    ])

    for i, p in enumerate(products, 1):
        validade_str = p.validade.strftime("%d/%m/%Y") if p.validade else "N/A"
        custo_str = f"R$ {p.custo_medio or 0:,.2f}"

        # Severity emoji
        p_class = (p.classe or "").upper()
        if "MUITO" in p_class:
            emoji = "⚫"
            class_label = "MUITO CRÍTICO"
        elif "CRITICO" in p_class or "CRÍTICO" in p_class:
            emoji = "🔴"
            class_label = "CRÍTICO"
        elif "TEN" in p_class:
            emoji = "🟡"
            class_label = "ATENÇÃO"
        else:
            emoji = "⚪"
            class_label = p.classe or "Outros"

        lines.extend([
            "",
            f"{emoji} *{i}. {p.descricao}*",
            f"   🏷️ {class_label}",
            f"   📦 Cód: {p.codigo} | Emb: {p.embalagem or '—'}",
            f"   📅 Vence: {validade_str} | Qtd: {p.quantidade or 0}",
            f"   💰 Valor: {custo_str} | 🏪 {p.filial or '—'}",
        ])

    lines.extend([
        "",
        "━" * 30,
        "",
        "📞 _Entre em contato para fazer seu pedido!_",
        "",
        "🤖 _Enviado automaticamente pelo Akram Monitor_",
    ])

    return "\n".join(lines)


def _was_client_notified_today(db: Session, phone: str) -> bool:
    """Check if client alerts were already sent to this number today."""
    today = datetime.now(tz).date()
    count = (
        db.query(func.count(NotificationLog.id))
        .filter(
            NotificationLog.phone == phone,
            NotificationLog.status == "sent",
            NotificationLog.notification_type == "client",
            func.date(NotificationLog.sent_at) == today,
        )
        .scalar()
    )
    return (count or 0) > 0


async def send_client_alerts(
    db: Session,
    product_repo: ProductRepository,
    client_repo: ClientRepository,
    force: bool = False,
) -> dict:
    """Send product alerts to inactive clients (>30 days without purchase).

    Flow:
    1. Get critical products from latest product upload
    2. Get inactive clients (30+ days no purchase, with valid phone)
    3. Normalize phone (add "55" prefix if needed)
    4. Check daily duplicate (skip if already sent today)
    5. Send via WhatsApp, log everything
    6. Continue on errors (don't break loop)
    """
    # 1. Get products to send
    product_upload_id = product_repo.get_latest_upload_id()
    if not product_upload_id:
        return {"sent": 0, "skipped": 0, "failed": 0, "errors": [], "message": "Nenhum arquivo de produtos processado"}

    products = (
        product_repo.get_muito_critico(product_upload_id)
        + product_repo.get_critico(product_upload_id)
        + product_repo.get_atencao(product_upload_id)
    )

    if not products:
        return {"sent": 0, "skipped": 0, "failed": 0, "errors": [], "message": "Nenhum produto crítico encontrado"}

    # 2. Get inactive clients with valid phone numbers
    inactive_clients = client_repo.get_inactive_clients(days=30)
    if not inactive_clients:
        return {"sent": 0, "skipped": 0, "failed": 0, "errors": [], "message": "Nenhum cliente inativo com telefone válido"}

    evolution_client = EvolutionAPIClient()
    sent_count = 0
    skipped_count = 0
    failed_count = 0
    errors = []
    no_phone_count = 0

    for c in inactive_clients:
        # 3. Normalize phone number (add "55" prefix)
        phone = normalize_phone(c.celular)
        if not phone:
            no_phone_count += 1
            continue

        # 4. Check if already notified today
        if not force and _was_client_notified_today(db, phone):
            skipped_count += 1
            continue

        # 5. Split and send
        chunks = [products[i:i + PRODUCTS_PER_MESSAGE] for i in range(0, len(products), PRODUCTS_PER_MESSAGE)]

        for chunk_idx, chunk in enumerate(chunks):
            message = format_client_products_message(
                c, chunk, part=chunk_idx, total_parts=len(chunks)
            )

            log = NotificationLog(
                phone=phone,
                message=message[:500] + "..." if len(message) > 500 else message,
                status="pending",
                direction="outbound",
                notification_type="client",
            )
            db.add(log)

            try:
                await evolution_client.send_text(phone, message)
                log.status = "sent"
                sent_count += 1
            except Exception as e:
                log.status = "failed"
                log.error = str(e)[:500]
                failed_count += 1
                errors.append({
                    "phone": phone,
                    "client": c.fantasia or c.razao_social or str(c.codigo),
                    "error": str(e)[:200],
                })

            db.commit()

    return {
        "sent": sent_count,
        "skipped": skipped_count,
        "failed": failed_count,
        "no_phone": no_phone_count,
        "total_inactive_clients": len(inactive_clients),
        "total_products": len(products),
        "errors": errors[:20],  # Cap to avoid huge response
    }
