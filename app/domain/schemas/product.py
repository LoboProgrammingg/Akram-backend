"""Pydantic schemas for Product domain."""

from pydantic import BaseModel
from datetime import date, datetime
from typing import Optional


class ProductBase(BaseModel):
    filial: Optional[str] = None
    codigo: Optional[int] = None
    descricao: Optional[str] = None
    embalagem: Optional[str] = None
    estoque: Optional[float] = None
    comprador: Optional[str] = None
    quantidade: Optional[float] = None
    validade: Optional[date] = None
    preco_com_st: Optional[float] = None
    status: Optional[str] = None
    uf: Optional[str] = None
    custo_medio: Optional[float] = None
    custo_total: Optional[float] = None
    classe: Optional[str] = None
    multiplo: Optional[float] = None
    vendas: Optional[float] = None


class ProductCreate(ProductBase):
    pass


class ProductRead(ProductBase):
    id: int
    upload_id: Optional[int] = None
    created_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class ProductFilter(BaseModel):
    filial: Optional[str] = None
    classe: Optional[str] = None
    uf: Optional[str] = None
    comprador: Optional[str] = None
    validade_start: Optional[date] = None
    validade_end: Optional[date] = None
    page: int = 1
    page_size: int = 50


class ProductStats(BaseModel):
    total_products: int
    total_muito_critico: int
    total_critico: int
    total_vencido: int
    total_custo: float
    total_custo_muito_critico: float
    filiais: list[str]
    classes: list[str]
