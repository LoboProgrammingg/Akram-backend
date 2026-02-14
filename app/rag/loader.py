"""RAG loader — converts products from DB to LangChain documents."""

from datetime import date
from typing import Optional

from sqlalchemy.orm import Session
from langchain_core.documents import Document

from app.domain.models.product import Product


def product_to_text(product: Product) -> str:
    """Convert a product record to a formatted text string for embedding."""
    validade_str = product.validade.strftime("%d/%m/%Y") if product.validade else "N/A"
    custo_str = f"R$ {product.custo_total:.2f}" if product.custo_total else "N/A"
    custo_medio_str = f"R$ {product.custo_medio:.2f}" if product.custo_medio else "N/A"
    preco_str = f"R$ {product.preco_com_st:.2f}" if product.preco_com_st else "N/A"

    return (
        f"Produto: {product.descricao or 'N/A'}\n"
        f"Código: {product.codigo or 'N/A'}\n"
        f"Filial: {product.filial or 'N/A'}\n"
        f"Embalagem: {product.embalagem or 'N/A'}\n"
        f"Estoque: {product.estoque or 0}\n"
        f"Quantidade: {product.quantidade or 0}\n"
        f"Validade: {validade_str}\n"
        f"Classe: {product.classe or 'N/A'}\n"
        f"Status: {product.status or 'N/A'}\n"
        f"Comprador: {product.comprador or 'N/A'}\n"
        f"UF: {product.uf or 'N/A'}\n"
        f"Preço c/ST: {preco_str}\n"
        f"Custo Médio: {custo_medio_str}\n"
        f"Custo Total: {custo_str}\n"
    )


def load_products_as_documents(db: Session, upload_id: Optional[int] = None) -> list[Document]:
    """Load all products from DB and convert to LangChain documents."""
    query = db.query(Product)
    if upload_id:
        query = query.filter(Product.upload_id == upload_id)

    products = query.all()

    documents = []
    for product in products:
        text = product_to_text(product)
        metadata = {
            "product_id": product.id,
            "codigo": product.codigo,
            "filial": product.filial or "",
            "classe": product.classe or "",
            "validade": product.validade.isoformat() if product.validade else "",
            "uf": product.uf or "",
        }
        documents.append(Document(page_content=text, metadata=metadata))

    return documents
