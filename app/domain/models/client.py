"""Client domain model — maps to the 'clients' table."""

from sqlalchemy import Column, Integer, String, Date, DateTime, ForeignKey
from sqlalchemy.sql import func

from app.infrastructure.database import Base


class Client(Base):
    __tablename__ = "clients"

    id = Column(Integer, primary_key=True, autoincrement=True)

    # Core CSV columns
    codigo = Column(Integer, nullable=True, index=True)
    razao_social = Column(String(500), nullable=True)
    fantasia = Column(String(300), nullable=True)
    cod_rede = Column(Integer, nullable=True)
    cidade = Column(String(200), nullable=True, index=True)
    estado = Column(String(50), nullable=True, index=True)
    telefone = Column(String(20), nullable=True)
    celular = Column(String(20), nullable=True)
    dt_ult_compra = Column(Date, nullable=True, index=True)

    # Relationships / metadata
    upload_id = Column(Integer, ForeignKey("client_uploads.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    def __repr__(self):
        return f"<Client {self.codigo} - {self.fantasia}>"
