"""
Modèles du module Cybersécurité.

Ce module couvre la gestion de la sécurité (suivi d'actifs, audits,
constats de vulnérabilités, conseils de sécurisation, gestion des
risques) — PAS des outils offensifs (scanners automatisés, générateurs
d'exploits). Conformément à la vision du projet, toute activité d'audit
suppose l'autorisation explicite du propriétaire du système
(`ownership_confirmed`), et le contenu produit reste au niveau du
constat et de la remédiation, jamais du code d'attaque prêt à l'emploi.
"""
import uuid
from datetime import datetime, date, timezone

from sqlalchemy import String, DateTime, Date, ForeignKey, Text, Boolean, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

ASSET_TYPES = {"site_web", "application_mobile", "application_desktop", "serveur", "reseau", "api", "base_de_donnees", "autre"}
AUDIT_STATUSES = {"demande", "planifie", "en_cours", "termine", "annule"}
FINDING_SEVERITIES = {"critique", "elevee", "moyenne", "faible", "info"}
FINDING_STATUSES = {"ouvert", "en_correction", "corrige", "risque_accepte"}
GUIDE_CATEGORIES = {
    "authentification", "chiffrement", "reseau", "applicatif", "cloud",
    "conformite", "sensibilisation", "gestion_des_risques", "autre",
}


def generate_uuid() -> str:
    return str(uuid.uuid4())


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class SecurityAsset(Base):
    """Un système appartenant à l'utilisateur, sur lequel il souhaite un suivi de sécurité."""

    __tablename__ = "cybersecurity_assets"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    owner_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), nullable=False, index=True)

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    asset_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    identifier: Mapped[str] = mapped_column(String(500), nullable=False)  # URL, IP, nom d'hôte...
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    audits: Mapped[list["SecurityAudit"]] = relationship(back_populates="asset", cascade="all, delete-orphan")


class SecurityAudit(Base):
    """
    Une demande d'audit sur un actif. `ownership_confirmed` DOIT être
    vrai : c'est l'attestation de l'utilisateur qu'il possède ou est
    autorisé à faire auditer ce système — condition non négociable,
    la même que sur toute plateforme d'audit ou de bug bounty sérieuse.
    """

    __tablename__ = "cybersecurity_audits"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    asset_id: Mapped[str] = mapped_column(String(36), ForeignKey("cybersecurity_assets.id"), nullable=False, index=True)
    requested_by: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), nullable=False, index=True)

    ownership_confirmed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    status: Mapped[str] = mapped_column(String(20), default="demande")
    scheduled_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    asset: Mapped["SecurityAsset"] = relationship(back_populates="audits")
    findings: Mapped[list["Finding"]] = relationship(back_populates="audit", cascade="all, delete-orphan")

    __table_args__ = (Index("ix_cybersecurity_audits_asset_status", "asset_id", "status"),)


class Finding(Base):
    """Un constat de vulnérabilité issu d'un audit, avec conseil de remédiation (jamais de code d'exploitation)."""

    __tablename__ = "cybersecurity_findings"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    audit_id: Mapped[str] = mapped_column(String(36), ForeignKey("cybersecurity_audits.id"), nullable=False, index=True)

    title: Mapped[str] = mapped_column(String(255), nullable=False)
    severity: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    remediation_advice: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="ouvert")

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    audit: Mapped["SecurityAudit"] = relationship(back_populates="findings")

    __table_args__ = (Index("ix_cybersecurity_findings_audit_severity", "audit_id", "severity"),)


class SecurityGuide(Base):
    """Contenu éducatif de sécurisation (bonnes pratiques), même principe que Droit/Finance : validé avant publication."""

    __tablename__ = "cybersecurity_guides"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    author_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), nullable=False, index=True)

    title: Mapped[str] = mapped_column(String(255), nullable=False)
    category: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    summary: Mapped[str] = mapped_column(String(500), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)

    is_reviewed: Mapped[bool] = mapped_column(Boolean, default=False)
    is_published: Mapped[bool] = mapped_column(Boolean, default=False)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)
