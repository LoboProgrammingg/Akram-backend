"""Phone Numbers API routes — CRUD for WhatsApp contacts."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.interfaces.deps import get_db
from app.interfaces.api.deps import get_current_user, require_admin
from app.domain.models.user import User
from app.domain.models.phone_number import PhoneNumber
from app.domain.schemas.notification import PhoneNumberCreate, PhoneNumberRead, PhoneNumberUpdate

router = APIRouter(prefix="/api/phone-numbers", tags=["Phone Numbers"])


@router.get("")
def list_phone_numbers(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    numbers = db.query(PhoneNumber).order_by(PhoneNumber.created_at.desc()).all()
    return [PhoneNumberRead.model_validate(n) for n in numbers]


@router.post("", response_model=PhoneNumberRead, status_code=status.HTTP_201_CREATED)
def create_phone_number(
    body: PhoneNumberCreate,
    db: Session = Depends(get_db),
    user: User = Depends(require_admin),
):
    existing = db.query(PhoneNumber).filter(PhoneNumber.number == body.number).first()
    if existing:
        raise HTTPException(status_code=400, detail="Número já cadastrado")

    phone = PhoneNumber(**body.model_dump(exclude_unset=True))
    db.add(phone)
    db.commit()
    db.refresh(phone)
    return PhoneNumberRead.model_validate(phone)


@router.patch("/{phone_id}", response_model=PhoneNumberRead)
def update_phone_number(
    phone_id: int,
    body: PhoneNumberUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(require_admin),
):
    phone = db.query(PhoneNumber).filter(PhoneNumber.id == phone_id).first()
    if not phone:
        raise HTTPException(status_code=404, detail="Número não encontrado")

    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(phone, field, value)

    db.commit()
    db.refresh(phone)
    return PhoneNumberRead.model_validate(phone)


@router.delete("/{phone_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_phone_number(
    phone_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(require_admin),
):
    phone = db.query(PhoneNumber).filter(PhoneNumber.id == phone_id).first()
    if not phone:
        raise HTTPException(status_code=404, detail="Número não encontrado")

    db.delete(phone)
    db.commit()
