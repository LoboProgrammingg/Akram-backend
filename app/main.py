"""FastAPI application — main entry point."""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.infrastructure.database import engine, Base

# Import all models so SQLAlchemy knows about them
from app.domain.models.product import Product
from app.domain.models.user import User
from app.domain.models.phone_number import PhoneNumber
from app.domain.models.notification_log import NotificationLog
from app.domain.models.upload import Upload

# Import routers
from app.interfaces.api.auth import router as auth_router
from app.interfaces.api.products import router as products_router
from app.interfaces.api.uploads import router as uploads_router
from app.interfaces.api.phone_numbers import router as phone_numbers_router
from app.interfaces.api.notifications import router as notifications_router
from app.interfaces.api.ai import router as ai_router
from app.interfaces.api.dashboard import router as dashboard_router
from app.interfaces.webhooks.evolution import router as evolution_router

settings = get_settings()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan — startup and shutdown events."""
    # Startup
    logger.info("Starting Akram Monitoring System...")

    # Create DB tables (dev only — use Alembic in production)
    Base.metadata.create_all(bind=engine)
    logger.info("Database tables created/verified")

    # Create default admin user if none exists
    from app.infrastructure.database import SessionLocal
    from app.application.services.auth_service import get_user_by_email, create_user
    db = SessionLocal()
    try:
        admin = get_user_by_email(db, "admin@akram.com")
        if not admin:
            create_user(db, name="Admin", email="admin@akram.com", password="admin123", role="admin")
            logger.info("Default admin user created: admin@akram.com / admin123")
    finally:
        db.close()

    # Start scheduler
    from app.scheduler.jobs import start_scheduler
    start_scheduler()

    yield

    # Shutdown
    from app.scheduler.jobs import stop_scheduler
    stop_scheduler()
    logger.info("Akram Monitoring System stopped")


app = FastAPI(
    title="Akram — Sistema Inteligente de Monitoramento de Validade",
    description="API Backend — Monitoramento de validade com IA, WhatsApp e RAG",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:3001", "*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth_router)
app.include_router(products_router)
app.include_router(uploads_router)
app.include_router(phone_numbers_router)
app.include_router(notifications_router)
app.include_router(ai_router)
app.include_router(dashboard_router)
app.include_router(evolution_router)


@app.get("/")
def root():
    return {
        "name": "Akram Monitoring System",
        "version": "1.0.0",
        "status": "running",
        "docs": "/docs",
    }


@app.get("/health")
def health():
    return {"status": "healthy"}
