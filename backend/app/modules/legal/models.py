"""
Modèles du module Droit.

Principe fondamental de ce module : le droit varie radicalement d'un
pays à l'autre. Chaque ressource juridique est donc rattachée à un
`jurisdiction_country` explicite — jamais de contenu générique présenté
comme universel. Le contenu informatif est clairement distingué de la
mise en relation avec un vrai professionnel (via le module Cartographie,
catégorie "avocat"), qui reste la seule source de conseil juridique
opposable.
"""
import uuid
from datetime import datetime, timezone

from sqlalchemy import String, DateTime, ForeignKey, Text, Boolean, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

# Domaines du droit couverts, alignés sur la vision du document Nexus.
LEGAL_CATEGORIES = {
    "droit_civil", "droit_penal", "droit_commercial", "droit_des_societes",
    "droit_du_travail", "droit_de_la_famille", "divorce", "succession",
    "immobilier", "fiscalite", "contrats", "propriete_intellectuelle",
    "procedures_administratives", "droit_international", "autre",
}

CONSULTATION_STATUSES = {"en_attente", "acceptee", "refusee", "terminee", "annulee"}


def generate_uuid() -> str:
    return str(uuid.uuid4())


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class LegalResource(Base):
    """
    Un article/guide informatif rattaché à UNE juridiction précise.
    Rédigé ou validé par l'équipe Nexus (`is_reviewed`), jamais présenté
    comme un avis juridique personnalisé.
    """

    __tablename__ = "legal_resources"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    author_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), nullable=False, index=True)

    title: Mapped[str] = mapped_column(String(255), nullable=False)
    category: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    summary: Mapped[str] = mapped_column(String(500), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)

    jurisdiction_country: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    language: Mapped[str] = mapped_column(String(10), default="fr")

    # Un contenu juridique non relu par une personne qualifiée ne doit
    # jamais être traité comme fiable : distinction stricte entre
    # "soumis" et "publié après vérification".
    is_reviewed: Mapped[bool] = mapped_column(Boolean, default=False)
    is_published: Mapped[bool] = mapped_column(Boolean, default=False)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    __table_args__ = (
        Index("ix_legal_resources_country_category", "jurisdiction_country", "category"),
    )


class ConsultationRequest(Base):
    """
    Mise en relation entre un utilisateur et un professionnel du droit
    référencé dans le module Cartographie (catégorie "avocat").
    C'est ICI, et uniquement ici, que se noue un vrai conseil juridique
    personnalisé — jamais via `LegalResource`, qui reste informatif.
    """

    __tablename__ = "legal_consultation_requests"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    client_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), nullable=False, index=True)
    lawyer_listing_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("maps_listings.id"), nullable=False, index=True
    )

    category: Mapped[str] = mapped_column(String(50), nullable=False)
    subject: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="en_attente")

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    __table_args__ = (
        Index("ix_legal_consultation_client_status", "client_id", "status"),
    )
