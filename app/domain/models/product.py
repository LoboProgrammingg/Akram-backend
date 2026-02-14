"""Product domain model — maps to the 'products' table."""

from sqlalchemy import Column, Integer, String, Float, Date, DateTime, ForeignKey, Text
from sqlalchemy.sql import func

from app.infrastructure.database import Base


class Product(Base):
    __tablename__ = "products"

    id = Column(Integer, primary_key=True, autoincrement=True)

    # Core spreadsheet columns (13 user-specified + filial, multiplo, vendas)
    filial = Column(String(100), nullable=True, index=True)
    codigo = Column(Integer, nullable=True, index=True)
    descricao = Column(Text, nullable=True)
    embalagem = Column(String(100), nullable=True)
    estoque = Column(Float, nullable=True)
    comprador = Column(String(200), nullable=True, index=True)
    quantidade = Column(Float, nullable=True)
    validade = Column(Date, nullable=True, index=True)
    preco_com_st = Column(Float, nullable=True)
    status = Column(String(100), nullable=True)
    uf = Column(String(200), nullable=True, index=True)
    custo_medio = Column(Float, nullable=True)
    custo_total = Column(Float, nullable=True)
    classe = Column(String(100), nullable=True, index=True)
    multiplo = Column(Float, nullable=True)
    vendas = Column(Float, nullable=True)

    # Relationships / metadata
    upload_id = Column(Integer, ForeignKey("uploads.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    def __repr__(self):
        return f"<Product {self.codigo} - {self.descricao}>"
