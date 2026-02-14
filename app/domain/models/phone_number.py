"""Phone number registry — WhatsApp contacts for notifications + AI queries."""

from sqlalchemy import Column, Integer, String, Boolean, DateTime
from sqlalchemy.sql import func

from app.infrastructure.database import Base


class PhoneNumber(Base):
    __tablename__ = "phone_numbers"

    id = Column(Integer, primary_key=True, autoincrement=True)
    number = Column(String(20), unique=True, nullable=False, index=True)
    name = Column(String(200), nullable=True)
    is_active = Column(Boolean, default=True)
    can_query_ai = Column(Boolean, default=True)
    notification_types = Column(String(500), default='["MUITO CRÍTICO", "CRITICO", "ATENÇÃO", "VENCIDO"]') # JSON string
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    def __repr__(self):
        return f"<PhoneNumber {self.number} - {self.name}>"
