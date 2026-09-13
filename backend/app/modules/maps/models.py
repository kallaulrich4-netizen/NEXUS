"""
Modèles du module Cartographie intelligente (Maps).

`Listing.owner_id` pointe vers `users.id` : un professionnel (agriculteur,
avocat, médecin, hôtel...) crée sa propre fiche avec le même compte
Nexus qu'il utilise pour le reste de la plateforme.
"""
import uuid
from datetime import datetime, timezone

from sqlalchemy import String, DateTime, ForeignKey, Text, Float, UniqueConstraint, CheckConstraint, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

# Catégories couvertes, alignées sur la vision du document Nexus.
LISTING_CATEGORIES = {
    "ferme", "exploitation_agricole", "veterinaire", "avocat", "medecin",
    "ecole", "hopital", "hotel", "restaurant", "commerce", "entreprise",
    "artisan", "administration", "garage", "prestataire_service",
}


def generate_uuid() -> str:
    return str(uuid.uuid4())


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Listing(Base):
    __tablename__ = "maps_listings"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    owner_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), nullable=False, index=True)

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    category: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    description: Mapped[str] = mapped_column(Text, nullable=False)

    # Coordonnées GPS : indispensables pour la recherche par proximité.
    latitude: Mapped[float] = mapped_column(Float, nullable=False)
    longitude: Mapped[float] = mapped_column(Float, nullable=False)

    address: Mapped[str] = mapped_column(String(500), nullable=False)
    city: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    country: Mapped[str] = mapped_column(String(100), nullable=False, index=True)

    phone: Mapped[str | None] = mapped_column(String(30), nullable=True)
    email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    website: Mapped[str | None] = mapped_column(String(500), nullable=True)

    is_verified: Mapped[bool] = mapped_column(default=False)  # vérifié par une modération Nexus
    is_active: Mapped[bool] = mapped_column(default=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    reviews: Mapped[list["Review"]] = relationship(back_populates="listing", cascade="all, delete-orphan")

    __table_args__ = (
        CheckConstraint("latitude >= -90 AND latitude <= 90", name="ck_listing_lat_range"),
        CheckConstraint("longitude >= -180 AND longitude <= 180", name="ck_listing_lng_range"),
        Index("ix_maps_listings_country_category", "country", "category"),
    )


class Review(Base):
    __tablename__ = "maps_reviews"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    listing_id: Mapped[str] = mapped_column(String(36), ForeignKey("maps_listings.id"), nullable=False, index=True)
    author_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), nullable=False, index=True)

    rating: Mapped[int] = mapped_column(nullable=False)  # 1 à 5
    comment: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    listing: Mapped["Listing"] = relationship(back_populates="reviews")

    __table_args__ = (
        CheckConstraint("rating >= 1 AND rating <= 5", name="ck_review_rating_range"),
        UniqueConstraint("listing_id", "author_id", name="uq_review_listing_author"),
    )
