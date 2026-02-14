"""Upload API routes — upload XLSX/CSV files."""

import os
import uuid

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, BackgroundTasks
from sqlalchemy.orm import Session

from app.config import get_settings
from app.infrastructure.database import get_db
from app.interfaces.api.deps import get_current_user
from app.domain.models.user import User
from app.domain.models.upload import Upload
from app.domain.schemas.notification import UploadRead
from app.application.services.xlsx_transformer import transform_xlsx_to_csv, transform_csv_to_db

settings = get_settings()
router = APIRouter(prefix="/api/uploads", tags=["Uploads"])


def _index_rag_background(upload_id: int):
    """Background task to re-index RAG after upload."""
    from app.infrastructure.database import SessionLocal
    from app.rag.chain import index_products

    db = SessionLocal()
    try:
        index_products(db, upload_id=upload_id)
    except Exception as e:
        import logging
        logging.getLogger(__name__).error(f"RAG indexing failed: {e}")
    finally:
        db.close()


@router.post("")
async def upload_file(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    if not file.filename:
        raise HTTPException(status_code=400, detail="Arquivo não informado")

    ext = file.filename.rsplit(".", 1)[-1].lower() if "." in file.filename else ""
    if ext not in ("xlsx", "csv"):
        raise HTTPException(status_code=400, detail="Apenas arquivos .xlsx e .csv são aceitos")

    # Save uploaded file
    os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
    safe_name = f"{uuid.uuid4().hex}_{file.filename}"
    file_path = os.path.join(settings.UPLOAD_DIR, safe_name)

    with open(file_path, "wb") as f:
        content = await file.read()
        f.write(content)

    try:
        if ext == "xlsx":
            result = transform_xlsx_to_csv(
                file_path=file_path,
                db=db,
                original_name=file.filename,
                uploaded_by=user.email,
            )
        else:
            result = transform_csv_to_db(
                file_path=file_path,
                db=db,
                original_name=file.filename,
                uploaded_by=user.email,
            )

        # Trigger RAG re-indexing in background
        background_tasks.add_task(_index_rag_background, result["upload_id"])

        return {
            "message": f"Upload concluído: {result['row_count']} produtos importados",
            **result,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao processar arquivo: {str(e)}")


@router.get("")
def list_uploads(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    uploads = db.query(Upload).order_by(Upload.created_at.desc()).limit(50).all()
    return [UploadRead.model_validate(u) for u in uploads]
