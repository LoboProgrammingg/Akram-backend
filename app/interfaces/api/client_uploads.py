"""Client Upload API routes — upload CSV/XLSX files with client data."""

import os
import uuid

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session

from app.config import get_settings
from app.interfaces.deps import get_db
from app.interfaces.api.deps import get_current_user
from app.domain.models.user import User
from app.domain.models.client_upload import ClientUpload
from app.domain.schemas.client import ClientUploadRead
from app.application.services.client_csv_transformer import (
    transform_client_csv_to_db,
    transform_client_xlsx_to_db,
)

settings = get_settings()
router = APIRouter(prefix="/api/client-uploads", tags=["Client Uploads"])


@router.post("")
async def upload_client_file(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Upload a CSV/XLSX file with client data."""
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
            result = transform_client_xlsx_to_db(
                file_path=file_path,
                db=db,
                original_name=file.filename,
                uploaded_by=user.email,
            )
        else:
            result = transform_client_csv_to_db(
                file_path=file_path,
                db=db,
                original_name=file.filename,
                uploaded_by=user.email,
            )

        return {
            "message": f"Upload concluído: {result['row_count']} clientes importados",
            **result,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao processar arquivo: {str(e)}")


@router.get("")
def list_client_uploads(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """List client upload history."""
    uploads = db.query(ClientUpload).order_by(ClientUpload.created_at.desc()).limit(50).all()
    return [ClientUploadRead.model_validate(u) for u in uploads]
