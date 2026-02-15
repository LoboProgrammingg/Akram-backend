"""AI Query API route — ask questions to the RAG system."""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.interfaces.deps import get_db
from app.interfaces.api.deps import get_current_user
from app.domain.models.user import User
from app.domain.schemas.notification import AIQueryRequest, AIQueryResponse
from app.rag.chain import query_rag

router = APIRouter(prefix="/api/ai", tags=["AI"])


@router.post("/query", response_model=AIQueryResponse)
def ai_query(
    body: AIQueryRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Query the AI with a natural language question about products."""
    answer = query_rag(body.question, use_whatsapp_format=False)
    return AIQueryResponse(answer=answer)


@router.post("/reindex")
def reindex_products(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Manually trigger RAG re-indexing for the latest upload."""
    from app.infrastructure.repositories.product_repository import SQLAlchemyProductRepository
    from app.domain.models.product import Product
    from app.rag.chain import index_products
    
    repo = SQLAlchemyProductRepository(db, Product)
    upload_id = repo.get_latest_upload_id()
    
    if not upload_id:
        return {"message": "Nenhum upload encontrado para indexar."}
        
    count = index_products(repo, upload_id=upload_id)
    return {"message": f"Indexação concluída. {count} chunks criados para upload {upload_id}."}
