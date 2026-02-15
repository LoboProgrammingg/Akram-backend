"""
SQLAlchemy Implementation of Client Repository.
"""

from typing import Any, Dict, List
from datetime import date, datetime, timedelta

import pytz
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.domain.models.client import Client
from app.domain.models.client_upload import ClientUpload
from app.domain.repositories.client_repository import ClientRepository
from app.infrastructure.repositories.base_repository import SQLAlchemyRepository
from app.domain.schemas.client import ClientFilter, ClientStats
from app.config import get_settings

settings = get_settings()
tz = pytz.timezone(settings.TIMEZONE)

# Phones to ignore during notification
INVALID_PHONE_VALUES = {"VERIFICAR", "verificar", "", None}


class SQLAlchemyClientRepository(SQLAlchemyRepository[Client], ClientRepository):
    """Client repository implementation using SQLAlchemy."""

    def get_current_date(self) -> date:
        """Get current date in the configured timezone."""
        return datetime.now(tz).date()

    def get_latest_upload_id(self) -> int | None:
        """Get the ID of the most recent client upload."""
        latest = (
            self.db.query(ClientUpload.id)
            .filter(ClientUpload.status == "completed")
            .order_by(ClientUpload.created_at.desc())
            .first()
        )
        return latest[0] if latest else None

    def get_with_filters(self, filters: ClientFilter, upload_id: int | None = None) -> Dict[str, Any]:
        """Get clients with filtering and pagination."""
        query = self.db.query(Client)

        if upload_id:
            query = query.filter(Client.upload_id == upload_id)

        if filters.estado:
            query = query.filter(Client.estado == filters.estado)
        if filters.cidade:
            query = query.filter(Client.cidade == filters.cidade)
        if filters.cod_rede:
            query = query.filter(Client.cod_rede == filters.cod_rede)
        if filters.dt_ult_compra_before:
            query = query.filter(Client.dt_ult_compra <= filters.dt_ult_compra_before)

        total = query.count()
        offset = (filters.page - 1) * filters.page_size
        clients = (
            query.order_by(Client.dt_ult_compra.asc().nullslast())
            .offset(offset)
            .limit(filters.page_size)
            .all()
        )

        return {
            "items": clients,
            "total": total,
            "page": filters.page,
            "page_size": filters.page_size,
            "total_pages": (total + filters.page_size - 1) // filters.page_size,
        }

    def get_stats(self, upload_id: int | None = None) -> ClientStats:
        """Get client dashboard statistics."""
        today = self.get_current_date()

        base_query = self.db.query(func.count(Client.id))
        if upload_id:
            base_query = base_query.filter(Client.upload_id == upload_id)

        total = base_query.scalar() or 0

        # Clients without date (NULL dt_ult_compra)
        q_null = self.db.query(func.count(Client.id)).filter(
            Client.dt_ult_compra.is_(None),
        )
        if upload_id:
            q_null = q_null.filter(Client.upload_id == upload_id)
        sem_data = q_null.scalar() or 0

        # Inactive 30+ days
        cutoff_30 = today - timedelta(days=30)
        q30 = self.db.query(func.count(Client.id)).filter(
            Client.dt_ult_compra.isnot(None),
            Client.dt_ult_compra < cutoff_30,
        )
        if upload_id:
            q30 = q30.filter(Client.upload_id == upload_id)
        inactive_30 = q30.scalar() or 0

        # Inactive 60+ days
        cutoff_60 = today - timedelta(days=60)
        q60 = self.db.query(func.count(Client.id)).filter(
            Client.dt_ult_compra.isnot(None),
            Client.dt_ult_compra < cutoff_60,
        )
        if upload_id:
            q60 = q60.filter(Client.upload_id == upload_id)
        inactive_60 = q60.scalar() or 0

        # Inactive 90+ days
        cutoff_90 = today - timedelta(days=90)
        q90 = self.db.query(func.count(Client.id)).filter(
            Client.dt_ult_compra.isnot(None),
            Client.dt_ult_compra < cutoff_90,
        )
        if upload_id:
            q90 = q90.filter(Client.upload_id == upload_id)
        inactive_90 = q90.scalar() or 0

        # Distinct states
        estados_query = self.db.query(Client.estado).distinct().filter(Client.estado.isnot(None))
        if upload_id:
            estados_query = estados_query.filter(Client.upload_id == upload_id)
        estados = [r[0] for r in estados_query.all()]

        # Distinct cities count
        cidades_query = self.db.query(func.count(func.distinct(Client.cidade))).filter(
            Client.cidade.isnot(None)
        )
        if upload_id:
            cidades_query = cidades_query.filter(Client.upload_id == upload_id)
        cidades_count = cidades_query.scalar() or 0

        return ClientStats(
            total_clients=total,
            inactive_30d=inactive_30,
            inactive_60d=inactive_60,
            inactive_90d=inactive_90,
            sem_data=sem_data,
            estados=sorted(estados),
            cidades_count=cidades_count,
        )

    def get_inactive_clients(self, days: int = 30, upload_id: int | None = None) -> List[Client]:
        """Get clients whose last purchase was more than N days ago.
        Excludes clients with invalid phone numbers.
        """
        today = self.get_current_date()
        cutoff = today - timedelta(days=days)

        query = self.db.query(Client).filter(
            Client.dt_ult_compra.isnot(None),
            Client.dt_ult_compra < cutoff,
        )

        if upload_id:
            query = query.filter(Client.upload_id == upload_id)

        # Exclude invalid phone entries
        query = query.filter(
            ~Client.celular.in_(INVALID_PHONE_VALUES),
            Client.celular.isnot(None),
        )

        return query.order_by(Client.dt_ult_compra.asc()).all()

    def get_chart_data_by_estado(self, upload_id: int | None = None) -> List[Dict[str, Any]]:
        """Get client count grouped by state."""
        query = self.db.query(
            Client.estado,
            func.count(Client.id).label("count"),
        ).filter(Client.estado.isnot(None))

        if upload_id:
            query = query.filter(Client.upload_id == upload_id)

        results = query.group_by(Client.estado).order_by(func.count(Client.id).desc()).all()
        return [{"estado": r.estado, "count": r.count} for r in results]

    def get_chart_data_inactivity_distribution(self, upload_id: int | None = None) -> List[Dict[str, Any]]:
        """Get client count grouped by inactivity ranges, including clients without dates."""
        today = self.get_current_date()

        cutoff_30 = today - timedelta(days=30)
        cutoff_60 = today - timedelta(days=60)
        cutoff_90 = today - timedelta(days=90)

        def _count_range(start_date, end_date=None):
            q = self.db.query(func.count(Client.id)).filter(
                Client.dt_ult_compra.isnot(None),
            )
            if upload_id:
                q = q.filter(Client.upload_id == upload_id)
            if end_date:
                q = q.filter(Client.dt_ult_compra >= start_date, Client.dt_ult_compra < end_date)
            else:
                q = q.filter(Client.dt_ult_compra < start_date)
            return q.scalar() or 0

        # Active (last 30 days)
        active = self.db.query(func.count(Client.id)).filter(
            Client.dt_ult_compra.isnot(None),
            Client.dt_ult_compra >= cutoff_30,
        )
        if upload_id:
            active = active.filter(Client.upload_id == upload_id)
        active_count = active.scalar() or 0

        # Clients without date
        no_date = self.db.query(func.count(Client.id)).filter(
            Client.dt_ult_compra.is_(None),
        )
        if upload_id:
            no_date = no_date.filter(Client.upload_id == upload_id)
        no_date_count = no_date.scalar() or 0

        return [
            {"faixa": "Ativo (< 30d)", "count": active_count},
            {"faixa": "Inativo 30-60d", "count": _count_range(cutoff_60, cutoff_30)},
            {"faixa": "Inativo 60-90d", "count": _count_range(cutoff_90, cutoff_60)},
            {"faixa": "Inativo > 90d", "count": _count_range(cutoff_90)},
            {"faixa": "Sem Data", "count": no_date_count},
        ]

    def get_chart_data_by_cidade(self, upload_id: int | None = None, limit: int = 10) -> List[Dict[str, Any]]:
        """Get client count grouped by city (top N)."""
        query = self.db.query(
            Client.cidade,
            func.count(Client.id).label("count"),
        ).filter(Client.cidade.isnot(None))

        if upload_id:
            query = query.filter(Client.upload_id == upload_id)

        results = (
            query.group_by(Client.cidade)
            .order_by(func.count(Client.id).desc())
            .limit(limit)
            .all()
        )
        return [{"cidade": r.cidade, "count": r.count} for r in results]

    def get_filter_options(self, upload_id: int | None = None) -> Dict[str, List[str]]:
        """Get all distinct values for filter dropdowns."""
        base_estado = self.db.query(Client.estado).distinct().filter(Client.estado.isnot(None))
        base_cidade = self.db.query(Client.cidade).distinct().filter(Client.cidade.isnot(None))

        if upload_id:
            base_estado = base_estado.filter(Client.upload_id == upload_id)
            base_cidade = base_cidade.filter(Client.upload_id == upload_id)

        estados = [r[0] for r in base_estado.all()]
        cidades = [r[0] for r in base_cidade.all()]

        return {
            "estados": sorted(estados),
            "cidades": sorted(cidades),
        }
