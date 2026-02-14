"""Notification log — tracks all WhatsApp messages sent."""

from sqlalchemy import Column, Integer, String, Text, DateTime
from sqlalchemy.sql import func

from app.infrastructure.database import Base


class NotificationLog(Base):
    __tablename__ = "notifications_log"

    id = Column(Integer, primary_key=True, autoincrement=True)
    phone = Column(String(20), nullable=False, index=True)
    message = Column(Text, nullable=False)
    status = Column(String(50), nullable=False, default="pending")  # pending, sent, failed
    error = Column(Text, nullable=True)
    direction = Column(String(10), default="outbound")  # outbound, inbound
    sent_at = Column(DateTime(timezone=True), server_default=func.now())

    def __repr__(self):
        return f"<NotificationLog {self.phone} - {self.status}>"
