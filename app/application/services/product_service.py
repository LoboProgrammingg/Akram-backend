"""Product service — business logic for product queries and stats."""

from datetime import date, datetime
from typing import Optional

import pytz
from sqlalchemy import func, case
from sqlalchemy.orm import Session

from app.config import get_settings
from app.domain.models.product import Product
from app.domain.schemas.product import ProductFilter, ProductStats

settings = get_settings()
tz = pytz.timezone(settings.TIMEZONE)


def get_current_date() -> date:
    """Get current date in America/Cuiaba timezone."""
    return datetime.now(tz).date()


def get_products(db: Session, filters: ProductFilter) -> dict:
    """Get products with filtering and pagination."""
    query = db.query(Product)

    if filters.filial:
        query = query.filter(Product.filial == filters.filial)
    if filters.classe:
        query = query.filter(Product.classe == filters.classe)
    if filters.uf:
        query = query.filter(Product.uf == filters.uf)
    if filters.comprador:
        query = query.filter(Product.comprador == filters.comprador)
    if filters.validade_start:
        query = query.filter(Product.validade >= filters.validade_start)
    if filters.validade_end:
        query = query.filter(Product.validade <= filters.validade_end)

    total = query.count()
    offset = (filters.page - 1) * filters.page_size
    products = (
        query.order_by(Product.validade.asc().nullslast())
        .offset(offset)
        .limit(filters.page_size)
        .all()
    )

    return {
        "items": products,
        "total": total,
        "page": filters.page,
        "page_size": filters.page_size,
        "total_pages": (total + filters.page_size - 1) // filters.page_size,
    }


def get_product_stats(db: Session) -> ProductStats:
    """Get dashboard statistics."""
    total = db.query(func.count(Product.id)).scalar() or 0
    muito_critico = db.query(func.count(Product.id)).filter(
        func.upper(Product.classe).like("%MUITO CR%")
    ).scalar() or 0
    critico = db.query(func.count(Product.id)).filter(
        func.upper(Product.classe).like("%CRITICO%"),
        ~func.upper(Product.classe).like("%MUITO%"),
    ).scalar() or 0
    vencido = db.query(func.count(Product.id)).filter(
        func.upper(Product.classe).like("%VENCIDO%")
    ).scalar() or 0

    total_custo = db.query(func.coalesce(func.sum(Product.custo_total), 0)).scalar()
    total_custo_mc = db.query(func.coalesce(func.sum(Product.custo_total), 0)).filter(
        func.upper(Product.classe).like("%MUITO CR%")
    ).scalar()

    filiais = [r[0] for r in db.query(Product.filial).distinct().filter(Product.filial.isnot(None)).all()]
    classes = [r[0] for r in db.query(Product.classe).distinct().filter(Product.classe.isnot(None)).all()]

    return ProductStats(
        total_products=total,
        total_muito_critico=muito_critico,
        total_critico=critico,
        total_vencido=vencido,
        total_custo=float(total_custo),
        total_custo_muito_critico=float(total_custo_mc),
        filiais=sorted(filiais),
        classes=sorted(classes),
    )


def get_muito_critico_products(db: Session) -> list[Product]:
    """Get all products with Classe == 'Muito Critico' for notifications."""
    return (
        db.query(Product)
        .filter(func.upper(Product.classe).like("%MUITO CR%"))
        .order_by(Product.validade.asc().nullslast())
        .all()
    )


def get_critico_products(db: Session) -> list[Product]:
    """Get all products with Classe == 'Critico' (excluding Muito Critico)."""
    return (
        db.query(Product)
        .filter(
            func.upper(Product.classe).like("%CRITICO%"),
            ~func.upper(Product.classe).like("%MUITO%")
        )
        .order_by(Product.validade.asc().nullslast())
        .all()
    )


def get_atencao_products(db: Session) -> list[Product]:
    """Get all products with Classe == 'Atencao' or 'Atenção'."""
    return (
        db.query(Product)
        .filter(
            (func.upper(Product.classe).like("%TEN%")) # Matches ATENCAO, ATENÇÃO
        )
        .order_by(Product.validade.asc().nullslast())
        .all()
    )


def get_chart_data_by_classe(db: Session) -> list[dict]:
    """Get product count and total cost grouped by Classe."""
    results = (
        db.query(
            Product.classe,
            func.count(Product.id).label("count"),
            func.coalesce(func.sum(Product.custo_total), 0).label("total_cost"),
        )
        .filter(Product.classe.isnot(None))
        .group_by(Product.classe)
        .all()
    )
    return [{"classe": r.classe, "count": r.count, "total_cost": float(r.total_cost)} for r in results]


def get_chart_data_by_filial(db: Session) -> list[dict]:
    """Get product count grouped by Filial."""
    results = (
        db.query(
            Product.filial,
            func.count(Product.id).label("count"),
            func.coalesce(func.sum(Product.custo_total), 0).label("total_cost"),
        )
        .filter(Product.filial.isnot(None))
        .group_by(Product.filial)
        .all()
    )
    return [{"filial": r.filial, "count": r.count, "total_cost": float(r.total_cost)} for r in results]


def get_chart_data_expiry_timeline(db: Session) -> list[dict]:
    """Get product count grouped by expiry date (next 30 days)."""
    today = get_current_date()
    results = (
        db.query(
            Product.validade,
            func.count(Product.id).label("count"),
        )
        .filter(Product.validade.isnot(None))
        .filter(Product.validade >= today)
        .group_by(Product.validade)
        .order_by(Product.validade)
        .limit(30)
        .all()
    )
    return [{"date": r.validade.isoformat(), "count": r.count} for r in results]


def get_filter_options(db: Session) -> dict:
    """Get all distinct values for filter dropdowns."""
    filiais = [r[0] for r in db.query(Product.filial).distinct().filter(Product.filial.isnot(None)).all()]
    classes = [r[0] for r in db.query(Product.classe).distinct().filter(Product.classe.isnot(None)).all()]
    ufs = [r[0] for r in db.query(Product.uf).distinct().filter(Product.uf.isnot(None)).all()]
    compradores = [r[0] for r in db.query(Product.comprador).distinct().filter(Product.comprador.isnot(None)).all()]

    return {
        "filiais": sorted(filiais),
        "classes": sorted(classes),
        "ufs": sorted(ufs),
        "compradores": sorted(compradores),
    }
