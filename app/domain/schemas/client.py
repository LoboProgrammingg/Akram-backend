"""Pydantic schemas for Client domain."""

from pydantic import BaseModel
from datetime import date, datetime
from typing import Optional


class ClientBase(BaseModel):
    codigo: Optional[int] = None
    razao_social: Optional[str] = None
    fantasia: Optional[str] = None
    cod_rede: Optional[int] = None
    cidade: Optional[str] = None
    estado: Optional[str] = None
    telefone: Optional[str] = None
    celular: Optional[str] = None
    dt_ult_compra: Optional[date] = None


class ClientCreate(ClientBase):
    pass


class ClientRead(ClientBase):
    id: int
    upload_id: Optional[int] = None
    created_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class ClientFilter(BaseModel):
    estado: Optional[str] = None
    cidade: Optional[str] = None
    cod_rede: Optional[int] = None
    dt_ult_compra_before: Optional[date] = None
    page: int = 1
    page_size: int = 50


class ClientStats(BaseModel):
    total_clients: int
    inactive_30d: int
    inactive_60d: int
    inactive_90d: int
    sem_data: int
    estados: list[str]
    cidades_count: int


class ClientUploadRead(BaseModel):
    id: int
    filename: str
    original_name: str
    row_count: int
    uploaded_by: Optional[str] = None
    status: str
    error_message: Optional[str] = None
    created_at: Optional[datetime] = None

    model_config = {"from_attributes": True}
