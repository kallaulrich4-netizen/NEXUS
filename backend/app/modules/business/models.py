"""
Modèles du module Gestion d'entreprise.

`sector` est un champ texte libre (commerce, agriculture, élevage, BTP,
industrie, transport, santé, éducation, logistique, hôtellerie,
restauration, administration, ou tout autre secteur) — même principe
que `species` dans le module Élevage : aucun secteur d'activité n'est
exclu par construction.
"""
import uuid
from datetime import datetime, date, timezone

from sqlalchemy import String, DateTime, Date, ForeignKey, Text, Numeric, Integer, CheckConstraint, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

EMPLOYEE_STATUSES = {"actif", "conge", "suspendu", "termine"}
INVOICE_STATUSES = {"brouillon", "envoyee", "payee", "en_retard", "annulee"}


def generate_uuid() -> str:
    return str(uuid.uuid4())


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Company(Base):
    """Une entreprise gérée par un utilisateur Nexus (PME comme grande entreprise)."""

    __tablename__ = "business_companies"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    owner_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), nullable=False, index=True)

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    sector: Mapped[str] = mapped_column(String(100), nullable=False, index=True)  # texte libre
    registration_number: Mapped[str | None] = mapped_column(String(100), nullable=True)
    country: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    city: Mapped[str | None] = mapped_column(String(100), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    employees: Mapped[list["Employee"]] = relationship(back_populates="company", cascade="all, delete-orphan")
    clients: Mapped[list["BusinessClient"]] = relationship(back_populates="company", cascade="all, delete-orphan")
    invoices: Mapped[list["Invoice"]] = relationship(back_populates="company", cascade="all, delete-orphan")


class Employee(Base):
    __tablename__ = "business_employees"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    company_id: Mapped[str] = mapped_column(String(36), ForeignKey("business_companies.id"), nullable=False, index=True)

    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(150), nullable=False)
    monthly_salary: Mapped[float | None] = mapped_column(Numeric(14, 2), nullable=True)
    currency: Mapped[str | None] = mapped_column(String(3), nullable=True)
    hire_date: Mapped[date] = mapped_column(Date, nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="actif")

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    company: Mapped["Company"] = relationship(back_populates="employees")

    __table_args__ = (
        CheckConstraint("monthly_salary IS NULL OR monthly_salary >= 0", name="ck_employee_salary_non_negative"),
    )


class BusinessClient(Base):
    """Un client de l'entreprise (distinct des clients de la Marketplace grand public)."""

    __tablename__ = "business_clients"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    company_id: Mapped[str] = mapped_column(String(36), ForeignKey("business_companies.id"), nullable=False, index=True)

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(30), nullable=True)
    address: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    company: Mapped["Company"] = relationship(back_populates="clients")
    invoices: Mapped[list["Invoice"]] = relationship(back_populates="client")


class Invoice(Base):
    __tablename__ = "business_invoices"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    company_id: Mapped[str] = mapped_column(String(36), ForeignKey("business_companies.id"), nullable=False, index=True)
    client_id: Mapped[str] = mapped_column(String(36), ForeignKey("business_clients.id"), nullable=False, index=True)

    invoice_number: Mapped[str] = mapped_column(String(50), nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="brouillon")
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="XOF")
    issue_date: Mapped[date] = mapped_column(Date, nullable=False)
    due_date: Mapped[date] = mapped_column(Date, nullable=False)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    company: Mapped["Company"] = relationship(back_populates="invoices")
    client: Mapped["BusinessClient"] = relationship(back_populates="invoices")
    items: Mapped[list["InvoiceItem"]] = relationship(back_populates="invoice", cascade="all, delete-orphan")

    __table_args__ = (
        Index("ix_business_invoices_company_status", "company_id", "status"),
        Index("ix_business_invoices_company_number", "company_id", "invoice_number", unique=True),
    )


class InvoiceItem(Base):
    __tablename__ = "business_invoice_items"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    invoice_id: Mapped[str] = mapped_column(String(36), ForeignKey("business_invoices.id"), nullable=False, index=True)

    description: Mapped[str] = mapped_column(String(500), nullable=False)
    quantity: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False, default=1)
    unit_price: Mapped[float] = mapped_column(Numeric(14, 2), nullable=False)

    invoice: Mapped["Invoice"] = relationship(back_populates="items")

    __table_args__ = (
        CheckConstraint("quantity > 0", name="ck_invoice_item_quantity_positive"),
        CheckConstraint("unit_price >= 0", name="ck_invoice_item_price_non_negative"),
    )
