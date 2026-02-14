"""Upload history — tracks uploaded spreadsheets."""

from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy.sql import func

from app.infrastructure.database import Base


class Upload(Base):
    __tablename__ = "uploads"

    id = Column(Integer, primary_key=True, autoincrement=True)
    filename = Column(String(500), nullable=False)
    original_name = Column(String(500), nullable=False)
    row_count = Column(Integer, default=0)
    uploaded_by = Column(String(200), nullable=True)
    status = Column(String(50), default="processing")  # processing, completed, failed
    error_message = Column(String(1000), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    def __repr__(self):
        return f"<Upload {self.original_name} - {self.row_count} rows>"
