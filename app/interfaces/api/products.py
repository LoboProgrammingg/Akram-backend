"""Products API routes — list, filter, stats, charts."""

from fastapi import APIRouter, Depends, Query
from typing import Optional
from datetime import date

from app.interfaces.api.deps import get_current_user
from app.interfaces.deps import get_product_repository
from app.domain.repositories.product_repository import ProductRepository
from app.domain.models.user import User
from app.domain.schemas.product import ProductFilter, ProductRead, ProductStats
from app.application.services.product_service import (
    get_products,
    get_product_stats,
    get_chart_data_by_classe,
    get_chart_data_by_filial,
    get_chart_data_expiry_timeline,
    get_filter_options,
)

router = APIRouter(prefix="/api/products", tags=["Products"])


@router.get("")
def list_products(
    filial: Optional[str] = None,
    classe: Optional[str] = None,
    uf: Optional[str] = None,
    comprador: Optional[str] = None,
    validade_start: Optional[date] = None,
    validade_end: Optional[date] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    repo: ProductRepository = Depends(get_product_repository),
    user: User = Depends(get_current_user),
):
    filters = ProductFilter(
        filial=filial,
        classe=classe,
        uf=uf,
        comprador=comprador,
        validade_start=validade_start,
        validade_end=validade_end,
        page=page,
        page_size=page_size,
    )
    result = get_products(repo, filters)
    result["items"] = [ProductRead.model_validate(p) for p in result["items"]]
    return result


@router.get("/stats", response_model=ProductStats)
def product_stats(
    repo: ProductRepository = Depends(get_product_repository),
    user: User = Depends(get_current_user),
):
    return get_product_stats(repo)


@router.get("/charts/by-classe")
def charts_by_classe(
    repo: ProductRepository = Depends(get_product_repository),
    user: User = Depends(get_current_user),
):
    return get_chart_data_by_classe(repo)


@router.get("/charts/by-filial")
def charts_by_filial(
    repo: ProductRepository = Depends(get_product_repository),
    user: User = Depends(get_current_user),
):
    return get_chart_data_by_filial(repo)


@router.get("/charts/expiry-timeline")
def charts_expiry_timeline(
    repo: ProductRepository = Depends(get_product_repository),
    user: User = Depends(get_current_user),
):
    return get_chart_data_expiry_timeline(repo)


@router.get("/filters")
def filter_options(
    repo: ProductRepository = Depends(get_product_repository),
    user: User = Depends(get_current_user),
):
    return get_filter_options(repo)
