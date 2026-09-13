"""
Modèle Utilisateur central de Nexus.

Un seul compte utilisateur donne accès à TOUS les modules (IA, réseau
social, marketplace, finance, droit, agriculture, etc.). Chaque module
référencera cette table via une clé étrangère `user_id`, ce qui garantit
l'interconnexion demandée entre les 15 modules.
"""
import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import String, Boolean, DateTime, Integer
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


def generate_uuid() -> str:
    return str(uuid.uuid4())


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)

    # Préférences transversales, utilisées par tous les modules
    preferred_language: Mapped[str] = mapped_column(String(10), default="fr")
    country: Mapped[str | None] = mapped_column(String(100), nullable=True)

    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False)

    # Protection contre les attaques par force brute (OWASP API2:2023 - Broken Authentication).
    # Corrige une faille très répandue : aucune limite de tentatives de connexion.
    failed_login_attempts: Mapped[int] = mapped_column(Integer, default=0)
    locked_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Fondation du système premium, utilisée par les modules payants
    # (Studio créatif, et d'autres à venir — jamais le Réseau social,
    # qui reste gratuit). `trial_ends_at` est fixé à l'inscription et
    # offre 24h d'accès complet. `premium_until` sera mis à jour par le
    # futur module de paiement (MTN Mobile Money, Orange Money, Visa...)
    # lors d'un abonnement réel ; NULL signifie aucun abonnement actif.
    trial_ends_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc) + timedelta(hours=24)
    )
    premium_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Statut super-administrateur : accès premium illimité à vie sur
    # toute la plateforme, réservé au(x) créateur(s) de Nexus. Ne peut
    # JAMAIS être défini par une requête utilisateur — voir
    # `service.py` : il n'est attribué qu'au compte dont l'email
    # correspond à `settings.initial_superuser_email`, configuré
    # uniquement côté serveur (variable d'environnement).
    is_superuser: Mapped[bool] = mapped_column(Boolean, default=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    def __repr__(self) -> str:
        return f"<User {self.email}>"
