"""
Modèle de notification, partagé par TOUTE la plateforme.

Ce n'est pas un module métier : c'est une brique d'infrastructure
transversale, au même titre que `rate_limit` ou `entitlements`. N'importe
quel module (agriculture, élevage, paiement...) peut créer des
notifications pour un utilisateur via `app.core.notifications.notify`,
sans avoir à connaître ni dupliquer ce modèle.
"""
import uuid
from datetime import datetime, timezone

from sqlalchemy import String, DateTime, Boolean, ForeignKey, Text, Index
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base

NOTIFICATION_CATEGORIES = {
    "info", "alerte", "rappel", "recommandation_ia", "echeance", "confirmation",
}


def generate_uuid() -> str:
    return str(uuid.uuid4())


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Notification(Base):
    __tablename__ = "notifications"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), nullable=False, index=True)

    category: Mapped[str] = mapped_column(String(30), nullable=False, default="info")
    module: Mapped[str | None] = mapped_column(String(50), nullable=True)  # ex: "agriculture", "paiement"
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    link: Mapped[str | None] = mapped_column(String(500), nullable=True)  # chemin frontend, ex: "/agriculture"

    is_read: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    __table_args__ = (Index("ix_notifications_user_read", "user_id", "is_read", "created_at"),)
