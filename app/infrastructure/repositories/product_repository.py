"""
SQLAlchemy Implementation of Product Repository.
"""

from typing import Any, Dict, List
from datetime import date, datetime
import pytz

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.domain.models.product import Product
from app.domain.repositories.product_repository import ProductRepository
from app.infrastructure.repositories.base_repository import SQLAlchemyRepository
from app.domain.schemas.product import ProductFilter, ProductStats
from app.config import get_settings

settings = get_settings()
tz = pytz.timezone(settings.TIMEZONE)


class SQLAlchemyProductRepository(SQLAlchemyRepository[Product], ProductRepository):
    """Product repository implementation using SQLAlchemy."""

    def get_current_date(self) -> date:
        """Get current date in configured timezone."""
        return datetime.now(tz).date()

    def get_with_filters(self, filters: ProductFilter) -> Dict[str, Any]:
        """Get products with filtering and pagination."""
        query = self.db.query(Product)

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

    def get_stats(self) -> ProductStats:
        """Get dashboard statistics."""
        total = self.db.query(func.count(Product.id)).scalar() or 0
        muito_critico = self.db.query(func.count(Product.id)).filter(
            func.upper(Product.classe).like("%MUITO CR%")
        ).scalar() or 0
        critico = self.db.query(func.count(Product.id)).filter(
            func.upper(Product.classe).like("%CRITICO%"),
            ~func.upper(Product.classe).like("%MUITO%"),
        ).scalar() or 0
        vencido = self.db.query(func.count(Product.id)).filter(
            func.upper(Product.classe).like("%VENCIDO%")
        ).scalar() or 0

        total_custo = self.db.query(func.coalesce(func.sum(Product.custo_total), 0)).scalar()
        total_custo_mc = self.db.query(func.coalesce(func.sum(Product.custo_total), 0)).filter(
            func.upper(Product.classe).like("%MUITO CR%")
        ).scalar()

        filiais = [r[0] for r in self.db.query(Product.filial).distinct().filter(Product.filial.isnot(None)).all()]
        classes = [r[0] for r in self.db.query(Product.classe).distinct().filter(Product.classe.isnot(None)).all()]

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

    def get_muito_critico(self) -> List[Product]:
        """Get all products with Classe == 'Muito Critico'."""
        return (
            self.db.query(Product)
            .filter(func.upper(Product.classe).like("%MUITO CR%"))
            .order_by(Product.validade.asc().nullslast())
            .all()
        )

    def get_critico(self) -> List[Product]:
        """Get all products with Classe == 'Critico' (excluding Muito Critico)."""
        return (
            self.db.query(Product)
            .filter(
                func.upper(Product.classe).like("%CRITICO%"),
                ~func.upper(Product.classe).like("%MUITO%")
            )
            .order_by(Product.validade.asc().nullslast())
            .all()
        )

    def get_atencao(self) -> List[Product]:
        """Get all products with Classe == 'Atencao' or 'Atenção'."""
        return (
            self.db.query(Product)
            .filter(
                (func.upper(Product.classe).like("%TEN%")) # Matches ATENCAO, ATENÇÃO
            )
            .order_by(Product.validade.asc().nullslast())
            .all()
        )

    def get_all_for_indexing(self, upload_id: int | None = None) -> List[Product]:
        """Get all products for RAG indexing, optionally filtered by upload."""
        query = self.db.query(Product)
        if upload_id:
            query = query.filter(Product.upload_id == upload_id)
        return query.all()

    def get_chart_data_by_classe(self) -> List[Dict[str, Any]]:
        """Get product count and total cost grouped by Classe."""
        results = (
            self.db.query(
                Product.classe,
                func.count(Product.id).label("count"),
                func.coalesce(func.sum(Product.custo_total), 0).label("total_cost"),
            )
            .filter(Product.classe.isnot(None))
            .group_by(Product.classe)
            .all()
        )
        return [{"classe": r.classe, "count": r.count, "total_cost": float(r.total_cost)} for r in results]

    def get_chart_data_by_filial(self) -> List[Dict[str, Any]]:
        """Get product count grouped by Filial."""
        results = (
            self.db.query(
                Product.filial,
                func.count(Product.id).label("count"),
                func.coalesce(func.sum(Product.custo_total), 0).label("total_cost"),
            )
            .filter(Product.filial.isnot(None))
            .group_by(Product.filial)
            .all()
        )
        return [{"filial": r.filial, "count": r.count, "total_cost": float(r.total_cost)} for r in results]

    def get_chart_data_expiry_timeline(self, days: int = 30) -> List[Dict[str, Any]]:
        """Get product count grouped by expiry date (next N days)."""
        today = self.get_current_date()
        results = (
            self.db.query(
                Product.validade,
                func.count(Product.id).label("count"),
            )
            .filter(Product.validade.isnot(None))
            .filter(Product.validade >= today)
            .group_by(Product.validade)
            .order_by(Product.validade)
            .limit(days)
            .all()
        )
        return [{"date": r.validade.isoformat(), "count": r.count} for r in results]

    def get_filter_options(self) -> Dict[str, List[str]]:
        """Get all distinct values for filter dropdowns."""
        filiais = [r[0] for r in self.db.query(Product.filial).distinct().filter(Product.filial.isnot(None)).all()]
        classes = [r[0] for r in self.db.query(Product.classe).distinct().filter(Product.classe.isnot(None)).all()]
        ufs = [r[0] for r in self.db.query(Product.uf).distinct().filter(Product.uf.isnot(None)).all()]
        compradores = [r[0] for r in self.db.query(Product.comprador).distinct().filter(Product.comprador.isnot(None)).all()]

        return {
            "filiais": sorted(filiais),
            "classes": sorted(classes),
            "ufs": sorted(ufs),
            "compradores": sorted(compradores),
        }
