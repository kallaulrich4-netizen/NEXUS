"""
Modèles du module Finance.

Trois briques qui couvrent la gestion budgétaire, le suivi des dépenses
et revenus, et les analyses de rentabilité demandés dans la vision :
Account (un portefeuille/compte), Transaction (chaque mouvement d'argent
réel saisi par l'utilisateur), Budget (une limite fixée sur une
catégorie et une période). Tous les calculs se basent exclusivement sur
les données réelles fournies par l'utilisateur, jamais sur des valeurs
suggérées ou inventées.
"""
import uuid
from datetime import datetime, date, timezone

from sqlalchemy import String, DateTime, Date, ForeignKey, Text, Numeric, CheckConstraint, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

TRANSACTION_TYPES = {"revenu", "depense"}

FINANCIAL_TIP_CATEGORIES = {
    "epargne", "budget", "investissement", "fiscalite", "dette",
    "retraite", "assurance", "entrepreneuriat", "autre",
}


def generate_uuid() -> str:
    return str(uuid.uuid4())


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Account(Base):
    """Un portefeuille/compte logique (espèces, banque, mobile money...)."""

    __tablename__ = "finance_accounts"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    owner_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), nullable=False, index=True)

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    account_type: Mapped[str] = mapped_column(String(50), default="general")  # especes, banque, mobile_money...
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="XOF")
    initial_balance: Mapped[float] = mapped_column(Numeric(14, 2), default=0)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    transactions: Mapped[list["Transaction"]] = relationship(back_populates="account", cascade="all, delete-orphan")


class Transaction(Base):
    """Un mouvement d'argent réel : un revenu ou une dépense."""

    __tablename__ = "finance_transactions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    owner_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), nullable=False, index=True)
    account_id: Mapped[str] = mapped_column(String(36), ForeignKey("finance_accounts.id"), nullable=False, index=True)

    transaction_type: Mapped[str] = mapped_column(String(20), nullable=False)  # revenu | depense
    category: Mapped[str] = mapped_column(String(100), nullable=False, index=True)  # texte libre
    amount: Mapped[float] = mapped_column(Numeric(14, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False)
    transaction_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    account: Mapped["Account"] = relationship(back_populates="transactions")

    __table_args__ = (
        CheckConstraint("amount > 0", name="ck_transaction_amount_positive"),
        Index("ix_finance_transactions_owner_date", "owner_id", "transaction_date"),
        Index("ix_finance_transactions_owner_category", "owner_id", "category"),
    )


class Budget(Base):
    """Une limite budgétaire fixée par l'utilisateur sur une catégorie et une période."""

    __tablename__ = "finance_budgets"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    owner_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), nullable=False, index=True)

    category: Mapped[str] = mapped_column(String(100), nullable=False)
    limit_amount: Mapped[float] = mapped_column(Numeric(14, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False)
    period_start: Mapped[date] = mapped_column(Date, nullable=False)
    period_end: Mapped[date] = mapped_column(Date, nullable=False)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    __table_args__ = (
        CheckConstraint("limit_amount > 0", name="ck_budget_limit_positive"),
        CheckConstraint("period_end >= period_start", name="ck_budget_period_valid"),
    )


class FinancialTip(Base):
    """
    Contenu éducatif général (épargne, budget, investissement, fiscalité...).

    Volontairement générique et non personnalisé : ceci n'est PAS un
    conseil financier individualisé (ce qui nécessiterait un agrément
    réglementaire dans la plupart des pays), mais de la littératie
    financière. Comme pour le module Droit, rien n'est publié sans
    validation (`is_reviewed` + `is_published`).
    """

    __tablename__ = "finance_tips"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    author_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), nullable=False, index=True)

    title: Mapped[str] = mapped_column(String(255), nullable=False)
    category: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    summary: Mapped[str] = mapped_column(String(500), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    language: Mapped[str] = mapped_column(String(10), default="fr")

    is_reviewed: Mapped[bool] = mapped_column(default=False)
    is_published: Mapped[bool] = mapped_column(default=False)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)
