"""
Modèle du journal d'activité, partagé par toute la plateforme.

Comme les notifications, ce n'est pas un module métier : c'est une
brique d'infrastructure transversale (traçabilité), utilisable par
n'importe quel module via `app.core.audit.log_action`.
"""
import uuid
from datetime import datetime, timezone

from sqlalchemy import String, DateTime, ForeignKey, Text, Index
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base

AUDIT_ACTIONS = {"connexion", "creation", "modification", "suppression", "autre"}


def generate_uuid() -> str:
    return str(uuid.uuid4())


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class AuditLogEntry(Base):
    __tablename__ = "audit_log"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    # Nullable : certains événements système (ex: échec de connexion avant identification) n'ont pas d'utilisateur connu.
    user_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("users.id"), nullable=True, index=True)

    action: Mapped[str] = mapped_column(String(30), nullable=False)
    module: Mapped[str] = mapped_column(String(50), nullable=False)  # ex: "auth", "agriculture", "paiement"
    resource_type: Mapped[str | None] = mapped_column(String(100), nullable=True)
    resource_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    description: Mapped[str] = mapped_column(Text, nullable=False)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)

    __table_args__ = (Index("ix_audit_log_user_date", "user_id", "created_at"),)
