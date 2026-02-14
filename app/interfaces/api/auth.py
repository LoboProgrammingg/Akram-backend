"""Auth API routes — login, register, me."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.infrastructure.database import get_db
from app.application.services.auth_service import (
    authenticate_user,
    create_access_token,
    create_user,
    get_user_by_email,
)
from app.domain.schemas.auth import LoginRequest, TokenResponse, UserCreate, UserRead
from app.interfaces.api.deps import get_current_user
from app.domain.models.user import User

router = APIRouter(prefix="/api/auth", tags=["Auth"])


@router.post("/login", response_model=TokenResponse)
def login(body: LoginRequest, db: Session = Depends(get_db)):
    user = authenticate_user(db, body.email, body.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email ou senha incorretos",
        )

    access_token = create_access_token(data={"sub": user.email, "role": user.role})

    return TokenResponse(
        access_token=access_token,
        user=UserRead.model_validate(user),
    )


@router.post("/register", response_model=UserRead, status_code=status.HTTP_201_CREATED)
def register(body: UserCreate, db: Session = Depends(get_db)):
    existing = get_user_by_email(db, body.email)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email já cadastrado",
        )

    user = create_user(
        db=db,
        name=body.name,
        email=body.email,
        password=body.password,
        role=body.role,
        phone=body.phone,
    )
    return UserRead.model_validate(user)


@router.get("/me", response_model=UserRead)
def get_me(user: User = Depends(get_current_user)):
    return UserRead.model_validate(user)
