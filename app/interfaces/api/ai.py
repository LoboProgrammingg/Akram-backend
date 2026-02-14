"""AI Query API route — ask questions to the RAG system."""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.infrastructure.database import get_db
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
