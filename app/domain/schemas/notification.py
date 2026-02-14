"""Pydantic schemas for Notification and PhoneNumber."""

from pydantic import BaseModel
from datetime import datetime
from typing import Optional


class PhoneNumberCreate(BaseModel):
    number: str
    name: Optional[str] = None
    can_query_ai: bool = True
    notification_types: Optional[str] = None


class PhoneNumberRead(BaseModel):
    id: int
    number: str
    name: Optional[str] = None
    is_active: bool
    can_query_ai: bool
    notification_types: Optional[str] = '["MUITO CRÍTICO", "CRITICO", "ATENÇÃO", "VENCIDO"]'
    created_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class PhoneNumberUpdate(BaseModel):
    name: Optional[str] = None
    is_active: Optional[bool] = None
    can_query_ai: Optional[bool] = None
    notification_types: Optional[str] = None


class NotificationLogRead(BaseModel):
    id: int
    phone: str
    message: str
    status: str
    error: Optional[str] = None
    direction: str
    sent_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class UploadRead(BaseModel):
    id: int
    filename: str
    original_name: str
    row_count: int
    uploaded_by: Optional[str] = None
    status: str
    error_message: Optional[str] = None
    created_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class AIQueryRequest(BaseModel):
    question: str


class AIQueryResponse(BaseModel):
    answer: str
    sources: Optional[list[str]] = None
