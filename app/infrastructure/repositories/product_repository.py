"""
SQLAlchemy Implementation of Product Repository.
"""

from typing import Any, Dict, List
from datetime import date, datetime
import pytz

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.domain.models.product import Product
from app.domain.models.upload import Upload
from app.domain.repositories.product_repository import ProductRepository
from app.infrastructure.repositories.base_repository import SQLAlchemyRepository
from app.domain.schemas.product import ProductFilter, ProductStats
from app.config import get_settings

settings = get_settings()
tz = pytz.timezone(settings.TIMEZONE)


class SQLAlchemyProductRepository(SQLAlchemyRepository[Product], ProductRepository):
    """Product repository implementation using SQLAlchemy."""

    def get_latest_upload_id(self) -> int | None:
        """Get the ID of the most recent upload."""
        latest = (
            self.db.query(Upload.id)
            .filter(Upload.status == "completed")
            .order_by(Upload.created_at.desc())
            .first()
        )
        return latest[0] if latest else None

    def get_current_date(self) -> date:
        """Get current date in the configured timezone."""
        return datetime.now(tz).date()

    def get_with_filters(self, filters: ProductFilter, upload_id: int | None = None) -> Dict[str, Any]:
        """Get products with filtering and pagination."""
        query = self.db.query(Product)

        if upload_id:
            query = query.filter(Product.upload_id == upload_id)

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

    def get_stats(self, upload_id: int | None = None) -> ProductStats:
        """Get dashboard statistics."""
        base_query = self.db.query(func.count(Product.id))
        if upload_id:
            base_query = base_query.filter(Product.upload_id == upload_id)

        total = base_query.scalar() or 0
        
        muito_critico_query = self.db.query(func.count(Product.id)).filter(
            func.upper(Product.classe).like("%MUITO CR%")
        )
        if upload_id:
            muito_critico_query = muito_critico_query.filter(Product.upload_id == upload_id)
        muito_critico = muito_critico_query.scalar() or 0

        critico_query = self.db.query(func.count(Product.id)).filter(
            func.upper(Product.classe).like("%CRITICO%"),
            ~func.upper(Product.classe).like("%MUITO%"),
        )
        if upload_id:
            critico_query = critico_query.filter(Product.upload_id == upload_id)
        critico = critico_query.scalar() or 0

        vencido_query = self.db.query(func.count(Product.id)).filter(
            func.upper(Product.classe).like("%VENCIDO%")
        )
        if upload_id:
            vencido_query = vencido_query.filter(Product.upload_id == upload_id)
        vencido = vencido_query.scalar() or 0

        atencao_query = self.db.query(func.count(Product.id)).filter(
            (func.upper(Product.classe).like("%TEN%")) | 
            (func.upper(Product.classe).like("%AMAREL%")) |
            (func.upper(Product.classe).like("%YELLOW%"))
        )
        if upload_id:
            atencao_query = atencao_query.filter(Product.upload_id == upload_id)
        atencao = atencao_query.scalar() or 0

        total_custo_query = self.db.query(func.coalesce(func.sum(func.coalesce(Product.preco_com_st, 0)), 0))
        if upload_id:
            total_custo_query = total_custo_query.filter(Product.upload_id == upload_id)
        total_custo = total_custo_query.scalar()

        total_custo_mc_query = self.db.query(func.coalesce(func.sum(func.coalesce(Product.preco_com_st, 0)), 0)).filter(
            func.upper(Product.classe).like("%MUITO CR%")
        )
        if upload_id:
            total_custo_mc_query = total_custo_mc_query.filter(Product.upload_id == upload_id)
        total_custo_mc = total_custo_mc_query.scalar()

        filiais_query = self.db.query(Product.filial).distinct().filter(Product.filial.isnot(None))
        if upload_id:
            filiais_query = filiais_query.filter(Product.upload_id == upload_id)
        filiais = [r[0] for r in filiais_query.all()]

        classes_query = self.db.query(Product.classe).distinct().filter(Product.classe.isnot(None))
        if upload_id:
            classes_query = classes_query.filter(Product.upload_id == upload_id)
        classes = [r[0] for r in classes_query.all()]

        return ProductStats(
            total_products=total,
            total_muito_critico=muito_critico,
            total_critico=critico,
            total_atencao=atencao,
            total_vencido=vencido,
            total_custo=float(total_custo),
            total_custo_muito_critico=float(total_custo_mc),
            filiais=sorted(filiais),
            classes=sorted(classes),
        )

    def get_muito_critico(self, upload_id: int | None = None) -> List[Product]:
        """Get all products with Classe == 'Muito Critico'."""
        query = self.db.query(Product).filter(func.upper(Product.classe).like("%MUITO CR%"))
        if upload_id:
            query = query.filter(Product.upload_id == upload_id)
        return query.order_by(Product.validade.asc().nullslast()).all()

    def get_critico(self, upload_id: int | None = None) -> List[Product]:
        """Get all products with Classe == 'Critico' (excluding Muito Critico)."""
        query = self.db.query(Product).filter(
            func.upper(Product.classe).like("%CRITICO%"),
            ~func.upper(Product.classe).like("%MUITO%")
        )
        if upload_id:
            query = query.filter(Product.upload_id == upload_id)
        return query.order_by(Product.validade.asc().nullslast()).all()

    def get_atencao(self, upload_id: int | None = None) -> List[Product]:
        """Get all products with Classe == 'Atencao', 'Atenção', 'Amarelo' or 'Yellow'."""
        query = self.db.query(Product).filter(
            (func.upper(Product.classe).like("%TEN%")) | 
            (func.upper(Product.classe).like("%AMAREL%")) |
            (func.upper(Product.classe).like("%YELLOW%"))
        )
        if upload_id:
            query = query.filter(Product.upload_id == upload_id)
        return query.order_by(Product.validade.asc().nullslast()).all()

    def get_all_for_indexing(self, upload_id: int | None = None) -> List[Product]:
        """Get all products for RAG indexing, optionally filtered by upload."""
        query = self.db.query(Product)
        if upload_id:
            query = query.filter(Product.upload_id == upload_id)
        return query.all()

    def get_chart_data_by_classe(self, upload_id: int | None = None) -> List[Dict[str, Any]]:
        """Get product count and total cost grouped by Classe."""
        query = self.db.query(
            Product.classe,
            Product.classe,
            func.count(Product.id).label("count"),
            func.coalesce(func.sum(func.coalesce(Product.preco_com_st, 0)), 0).label("total_cost"),
        ).filter(Product.classe.isnot(None))
        
        if upload_id:
            query = query.filter(Product.upload_id == upload_id)
            
        results = query.group_by(Product.classe).all()
        return [{"classe": r.classe, "count": r.count, "total_cost": float(r.total_cost)} for r in results]

    def get_chart_data_by_filial(self, upload_id: int | None = None) -> List[Dict[str, Any]]:
        """Get product count grouped by Filial."""
        query = self.db.query(
            Product.filial,
            Product.filial,
            func.count(Product.id).label("count"),
            func.coalesce(func.sum(func.coalesce(Product.preco_com_st, 0)), 0).label("total_cost"),
        ).filter(Product.filial.isnot(None))
        
        if upload_id:
            query = query.filter(Product.upload_id == upload_id)
            
        results = query.group_by(Product.filial).all()
        return [{"filial": r.filial, "count": r.count, "total_cost": float(r.total_cost)} for r in results]

    def get_chart_data_expiry_timeline(self, days: int = 30, upload_id: int | None = None) -> List[Dict[str, Any]]:
        """Get product count grouped by expiry date (next N days)."""
        today = self.get_current_date()
        query = (
            self.db.query(
                Product.validade,
                func.count(Product.id).label("count"),
            )
            .filter(Product.validade.isnot(None))
            .filter(Product.validade >= today)
        )
        
        if upload_id:
            query = query.filter(Product.upload_id == upload_id)
            
        results = (
            query.group_by(Product.validade)
            .order_by(Product.validade)
            .limit(days)
            .all()
        )
        return [{"date": r.validade.isoformat(), "count": r.count} for r in results]

    def get_filter_options(self, upload_id: int | None = None) -> Dict[str, List[str]]:
        """Get all distinct values for filter dropdowns."""
        base_query_filial = self.db.query(Product.filial).distinct().filter(Product.filial.isnot(None))
        base_query_classe = self.db.query(Product.classe).distinct().filter(Product.classe.isnot(None))
        base_query_uf = self.db.query(Product.uf).distinct().filter(Product.uf.isnot(None))
        base_query_comprador = self.db.query(Product.comprador).distinct().filter(Product.comprador.isnot(None))

        if upload_id:
            base_query_filial = base_query_filial.filter(Product.upload_id == upload_id)
            base_query_classe = base_query_classe.filter(Product.upload_id == upload_id)
            base_query_uf = base_query_uf.filter(Product.upload_id == upload_id)
            base_query_comprador = base_query_comprador.filter(Product.upload_id == upload_id)

        filiais = [r[0] for r in base_query_filial.all()]
        classes = [r[0] for r in base_query_classe.all()]
        ufs = [r[0] for r in base_query_uf.all()]
        compradores = [r[0] for r in base_query_comprador.all()]

        return {
            "filiais": sorted(filiais),
            "classes": sorted(classes),
            "ufs": sorted(ufs),
            "compradores": sorted(compradores),
        }

    def get_chart_data_by_uf(self, upload_id: int | None = None) -> List[Dict[str, Any]]:
        """Get product count and total value grouped by UF (region)."""
        query = self.db.query(
            Product.uf,
            func.count(Product.id).label("count"),
            func.coalesce(func.sum(func.coalesce(Product.quantidade, 0)), 0).label("total_qtd"),
            func.coalesce(func.sum(func.coalesce(Product.preco_com_st, 0)), 0).label("total_valor"),
            func.coalesce(func.sum(func.coalesce(Product.custo_total, 0)), 0).label("total_custo"),
        ).filter(Product.uf.isnot(None))
        
        if upload_id:
            query = query.filter(Product.upload_id == upload_id)
            
        results = query.group_by(Product.uf).order_by(func.count(Product.id).desc()).all()
        return [
            {
                "uf": r.uf, 
                "count": r.count, 
                "total_qtd": float(r.total_qtd),
                "total_valor": float(r.total_valor),
                "total_custo": float(r.total_custo),
            } 
            for r in results
        ]

    def get_top_critical_products(self, upload_id: int | None = None, limit: int = 10) -> List[Dict[str, Any]]:
        """Get top critical products ordered by quantity (most urgent to sell)."""
        query = self.db.query(Product).filter(
            func.upper(Product.classe).like("%MUITO CR%")
        )
        if upload_id:
            query = query.filter(Product.upload_id == upload_id)
        
        results = query.order_by(Product.validade.asc().nullslast()).limit(limit).all()
        return [
            {
                "id": p.id,
                "codigo": p.codigo,
                "descricao": p.descricao,
                "quantidade": p.quantidade,
                "validade": p.validade.isoformat() if p.validade else None,
                "preco_com_st": p.preco_com_st,
                "custo_total": p.custo_total,
                "classe": p.classe,
                "uf": p.uf,
                "filial": p.filial,
            }
            for p in results
        ]

    def get_expiry_summary_by_week(self, upload_id: int | None = None, weeks: int = 4) -> List[Dict[str, Any]]:
        """Get product count grouped by week (next N weeks) with class breakdown."""
        today = self.get_current_date()
        results = []
        
        for week in range(weeks):
            week_start = today + timedelta(days=week * 7)
            week_end = today + timedelta(days=(week + 1) * 7)
            
            # Count by class for this week
            query = self.db.query(
                Product.classe,
                func.count(Product.id).label("count"),
                func.coalesce(func.sum(func.coalesce(Product.quantidade, 0)), 0).label("total_qtd"),
            ).filter(
                Product.validade.isnot(None),
                Product.validade >= week_start,
                Product.validade < week_end,
            )
            
            if upload_id:
                query = query.filter(Product.upload_id == upload_id)
            
            class_data = query.group_by(Product.classe).all()
            
            week_data = {
                "semana": f"Semana {week + 1}",
                "inicio": week_start.isoformat(),
                "fim": week_end.isoformat(),
                "muito_critico": 0,
                "critico": 0,
                "atencao": 0,
                "total": 0,
                "total_qtd": 0,
            }
            
            for row in class_data:
                classe = (row.classe or "").upper()
                if "MUITO" in classe:
                    week_data["muito_critico"] = row.count
                elif "CRITICO" in classe or "CRÍTICO" in classe:
                    week_data["critico"] = row.count
                elif "TEN" in classe:
                    week_data["atencao"] = row.count
                week_data["total"] += row.count
                week_data["total_qtd"] += float(row.total_qtd)
            
            results.append(week_data)
        
        return results

    def get_value_summary(self, upload_id: int | None = None) -> Dict[str, Any]:
        """Get summary of total values by class."""
        query = self.db.query(
            Product.classe,
            func.count(Product.id).label("count"),
            func.coalesce(func.sum(func.coalesce(Product.quantidade, 0)), 0).label("total_qtd"),
            func.coalesce(func.sum(func.coalesce(Product.preco_com_st, 0)), 0).label("total_valor_unit"),
            func.coalesce(func.sum(func.coalesce(Product.custo_total, 0)), 0).label("total_custo"),
        )
        
        if upload_id:
            query = query.filter(Product.upload_id == upload_id)
        
        results = query.group_by(Product.classe).all()
        
        summary = {
            "muito_critico": {"count": 0, "total_qtd": 0, "total_valor_unit": 0, "total_custo": 0},
            "critico": {"count": 0, "total_qtd": 0, "total_valor_unit": 0, "total_custo": 0},
            "atencao": {"count": 0, "total_qtd": 0, "total_valor_unit": 0, "total_custo": 0},
            "outros": {"count": 0, "total_qtd": 0, "total_valor_unit": 0, "total_custo": 0},
            "total": {"count": 0, "total_qtd": 0, "total_valor_unit": 0, "total_custo": 0},
        }
        
        for row in results:
            classe = (row.classe or "").upper()
            data = {
                "count": row.count,
                "total_qtd": float(row.total_qtd),
                "total_valor_unit": float(row.total_valor_unit),
                "total_custo": float(row.total_custo),
            }
            
            if "MUITO" in classe:
                summary["muito_critico"] = data
            elif "CRITICO" in classe or "CRÍTICO" in classe:
                summary["critico"] = data
            elif "TEN" in classe:
                summary["atencao"] = data
            else:
                summary["outros"]["count"] += data["count"]
                summary["outros"]["total_qtd"] += data["total_qtd"]
                summary["outros"]["total_valor_unit"] += data["total_valor_unit"]
                summary["outros"]["total_custo"] += data["total_custo"]
            
            summary["total"]["count"] += data["count"]
            summary["total"]["total_qtd"] += data["total_qtd"]
            summary["total"]["total_valor_unit"] += data["total_valor_unit"]
            summary["total"]["total_custo"] += data["total_custo"]
        
        return summary
