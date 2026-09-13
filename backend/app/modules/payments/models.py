"""
Modèles du module Paiement.

Trois niveaux : Plan (un tarif défini par vous, ex: "Journalier 100 FCFA"),
Subscription (l'abonnement actif ou passé d'un utilisateur), Payment
(chaque tentative de transaction réelle, réussie ou non). Cette
séparation permet de rejouer un paiement échoué sans perdre l'historique,
et de gérer plusieurs moyens de paiement (MTN Mobile Money, Orange
Money, Visa/Mastercard...) de façon uniforme.

Conformément à la demande initiale : AUCUNE route de ce module ne
s'applique au Réseau social, qui reste entièrement gratuit pour tous.
"""
import uuid
from datetime import datetime, timezone

from sqlalchemy import String, DateTime, ForeignKey, Integer, Numeric, Boolean, CheckConstraint, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

PAYMENT_METHODS = {"mtn_mobile_money", "orange_money", "visa", "mastercard", "autre"}
PAYMENT_STATUSES = {"en_attente", "reussi", "echoue", "rembourse"}
SUBSCRIPTION_STATUSES = {"en_attente_paiement", "active", "expiree", "annulee"}


def generate_uuid() -> str:
    return str(uuid.uuid4())


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Plan(Base):
    """Un tarif d'abonnement défini par l'opérateur de la plateforme (vous)."""

    __tablename__ = "payment_plans"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)

    name: Mapped[str] = mapped_column(String(100), nullable=False)
    duration_days: Mapped[int] = mapped_column(Integer, nullable=False)
    price_amount: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="XOF")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    __table_args__ = (
        CheckConstraint("duration_days > 0", name="ck_plan_duration_positive"),
        CheckConstraint("price_amount >= 0", name="ck_plan_price_non_negative"),
    )


class Subscription(Base):
    """L'abonnement d'un utilisateur — actif, expiré, ou annulé."""

    __tablename__ = "payment_subscriptions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), nullable=False, index=True)
    plan_id: Mapped[str] = mapped_column(String(36), ForeignKey("payment_plans.id"), nullable=False)

    status: Mapped[str] = mapped_column(String(20), default="en_attente_paiement")
    # NULL tant que le paiement n'est pas confirmé : on ne fixe les dates
    # réelles qu'à la confirmation, pour ne jamais faire courir un
    # abonnement avant que l'argent soit réellement encaissé.
    starts_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    ends_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    payments: Mapped[list["Payment"]] = relationship(back_populates="subscription", cascade="all, delete-orphan")

    __table_args__ = (Index("ix_payment_subscriptions_user_status", "user_id", "status"),)


class Payment(Base):
    """Une tentative de transaction réelle, réussie ou non, rattachée à un abonnement."""

    __tablename__ = "payment_payments"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    subscription_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("payment_subscriptions.id"), nullable=False, index=True
    )
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), nullable=False, index=True)

    amount: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False)
    method: Mapped[str] = mapped_column(String(30), nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="en_attente")

    provider_reference: Mapped[str | None] = mapped_column(String(255), nullable=True)
    failure_reason: Mapped[str | None] = mapped_column(String(500), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    subscription: Mapped["Subscription"] = relationship(back_populates="payments")

    __table_args__ = (
        CheckConstraint("amount >= 0", name="ck_payment_amount_non_negative"),
        Index("ix_payment_payments_user_status", "user_id", "status"),
    )
