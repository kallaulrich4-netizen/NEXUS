"""
Modèles du module Élevage.

`species` est un champ TEXTE LIBRE, volontairement non limité à une liste
fixe : bovins, ovins, caprins, porcins, volailles, lapins, poissons,
abeilles, chevaux, autruches, cailles, dindes, escargots, espèces
exotiques ou toute autre espèce future sont TOUTES prises en charge sans
exception, sans qu'il soit nécessaire de modifier le code. Une liste de
suggestions est fournie pour guider l'interface utilisateur, mais elle
ne restreint jamais la saisie.
"""
import uuid
from datetime import datetime, date, timezone

from sqlalchemy import String, DateTime, Date, ForeignKey, Text, Float, Integer, CheckConstraint, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

# Suggestions pour l'interface utilisateur uniquement — la liste n'est
# JAMAIS utilisée pour valider ou rejeter une saisie côté serveur.
SUGGESTED_SPECIES = [
    "bovins", "ovins", "caprins", "porcins", "volailles", "lapins",
    "poissons", "abeilles", "chevaux", "autruches", "cailles", "dindes",
    "escargots", "canards", "oies", "dindons", "buffles", "chameaux",
    "animaux_exotiques",
]

HEALTH_EVENT_TYPES = {
    "vaccination", "traitement", "naissance", "deces", "sevrage",
    "insemination", "controle_veterinaire", "autre",
}

# --- Élevage V2 : fiche individuelle ---
ANIMAL_SEXES = {"male", "femelle", "inconnu"}
ANIMAL_STATUSES = {"vivant", "vendu", "decede", "reforme"}
ANIMAL_HEALTH_RECORD_TYPES = {
    "vaccination", "traitement", "controle_veterinaire", "autre",
}
REPRODUCTION_EVENT_TYPES = {
    "chaleurs", "insemination", "saillie", "gestation_confirmee",
    "mise_bas", "avortement",
}


def generate_uuid() -> str:
    return str(uuid.uuid4())


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Herd(Base):
    """
    Un troupeau/cheptel/lot d'animaux appartenant à un utilisateur.
    Le terme couvre aussi bien un troupeau de bovins qu'une ruche
    d'abeilles ou un bassin de poissons — c'est la même structure.
    """

    __tablename__ = "livestock_herds"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    owner_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), nullable=False, index=True)

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    species: Mapped[str] = mapped_column(String(100), nullable=False, index=True)  # texte libre, voir docstring
    breed: Mapped[str | None] = mapped_column(String(100), nullable=True)  # race, ex: "Ndama", "Holstein"

    current_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    country: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    region: Mapped[str | None] = mapped_column(String(100), nullable=True)
    latitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    longitude: Mapped[float | None] = mapped_column(Float, nullable=True)

    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    health_events: Mapped[list["HealthEvent"]] = relationship(back_populates="herd", cascade="all, delete-orphan")
    production_records: Mapped[list["ProductionRecord"]] = relationship(
        back_populates="herd", cascade="all, delete-orphan"
    )

    __table_args__ = (CheckConstraint("current_count >= 0", name="ck_herd_count_non_negative"),)


class HealthEvent(Base):
    """
    Un événement sanitaire ou démographique affectant le cheptel :
    vaccination, traitement, naissance, décès, sevrage, insémination...
    Chaque événement peut ajuster `current_count` sur le troupeau.
    """

    __tablename__ = "livestock_health_events"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    herd_id: Mapped[str] = mapped_column(String(36), ForeignKey("livestock_herds.id"), nullable=False, index=True)

    event_type: Mapped[str] = mapped_column(String(50), nullable=False)
    event_date: Mapped[date] = mapped_column(Date, nullable=False)
    # Variation du cheptel liée à cet événement : positive (naissance),
    # négative (décès, vente), ou nulle (simple soin sans impact d'effectif).
    count_change: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    cost_amount: Mapped[float | None] = mapped_column(Float, nullable=True)
    cost_currency: Mapped[str | None] = mapped_column(String(3), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    herd: Mapped["Herd"] = relationship(back_populates="health_events")

    __table_args__ = (
        CheckConstraint("cost_amount IS NULL OR cost_amount >= 0", name="ck_health_event_cost_non_negative"),
        Index("ix_livestock_health_events_herd_date", "herd_id", "event_date"),
    )


class ProductionRecord(Base):
    """
    Une production issue du cheptel : lait, œufs, laine, miel, viande...
    `product_type` est également en texte libre pour la même raison que
    `species` — couvrir toutes les productions possibles sans exception.
    """

    __tablename__ = "livestock_production_records"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    herd_id: Mapped[str] = mapped_column(String(36), ForeignKey("livestock_herds.id"), nullable=False, index=True)

    product_type: Mapped[str] = mapped_column(String(100), nullable=False, index=True)  # ex: lait, oeufs, laine, miel
    quantity: Mapped[float] = mapped_column(Float, nullable=False)
    unit: Mapped[str] = mapped_column(String(20), nullable=False)  # litres, kg, unités...
    record_date: Mapped[date] = mapped_column(Date, nullable=False)

    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    herd: Mapped["Herd"] = relationship(back_populates="production_records")

    __table_args__ = (
        CheckConstraint("quantity >= 0", name="ck_production_quantity_non_negative"),
        Index("ix_livestock_production_herd_date", "herd_id", "record_date"),
    )


# ============================================================================
# ÉLEVAGE V2 — Fiche individuelle par animal
#
# Toutes les tables ci-dessous sont ADDITIVES et OPTIONNELLES : un
# troupeau (Herd) continue de fonctionner exactement comme avant s'il
# n'a aucun animal individuel rattaché — utile pour la volaille, les
# abeilles, les poissons, où le suivi de masse reste plus pertinent.
# ============================================================================


class Animal(Base):
    """
    Fiche individuelle d'un animal appartenant à un troupeau : identité,
    âge, race, poids courant, statut, et filiation (parent_id) pour la
    volaille... pardon, pour le bétail et autres espèces suivies
    individuellement.
    """

    __tablename__ = "livestock_animals"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    herd_id: Mapped[str] = mapped_column(String(36), ForeignKey("livestock_herds.id"), nullable=False, index=True)
    parent_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("livestock_animals.id"), nullable=True)

    tag: Mapped[str] = mapped_column(String(100), nullable=False)  # identifiant/nom/numéro de boucle
    breed: Mapped[str | None] = mapped_column(String(100), nullable=True)
    sex: Mapped[str] = mapped_column(String(20), nullable=False, default="inconnu")
    birth_date: Mapped[date | None] = mapped_column(Date, nullable=True)

    current_weight_kg: Mapped[float | None] = mapped_column(Float, nullable=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="vivant")

    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    herd: Mapped["Herd"] = relationship()
    parent: Mapped["Animal | None"] = relationship(remote_side=[id])
    health_records: Mapped[list["AnimalHealthRecord"]] = relationship(
        back_populates="animal", cascade="all, delete-orphan"
    )
    weight_records: Mapped[list["WeightRecord"]] = relationship(
        back_populates="animal", cascade="all, delete-orphan"
    )
    reproduction_records: Mapped[list["ReproductionRecord"]] = relationship(
        back_populates="animal", cascade="all, delete-orphan", foreign_keys="ReproductionRecord.animal_id"
    )

    __table_args__ = (
        CheckConstraint("current_weight_kg IS NULL OR current_weight_kg >= 0", name="ck_animal_weight_non_negative"),
        Index("ix_livestock_animals_herd_tag", "herd_id", "tag"),
    )


class AnimalHealthRecord(Base):
    """Historique médical individuel d'un animal (distinct de HealthEvent, qui reste au niveau du troupeau)."""

    __tablename__ = "livestock_animal_health_records"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    animal_id: Mapped[str] = mapped_column(String(36), ForeignKey("livestock_animals.id"), nullable=False, index=True)

    record_type: Mapped[str] = mapped_column(String(50), nullable=False)
    record_date: Mapped[date] = mapped_column(Date, nullable=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    cost_amount: Mapped[float | None] = mapped_column(Float, nullable=True)
    cost_currency: Mapped[str | None] = mapped_column(String(3), nullable=True)
    next_due_date: Mapped[date | None] = mapped_column(Date, nullable=True)  # ex: rappel de vaccin

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    animal: Mapped["Animal"] = relationship(back_populates="health_records")

    __table_args__ = (
        CheckConstraint("cost_amount IS NULL OR cost_amount >= 0", name="ck_animal_health_cost_non_negative"),
        Index("ix_livestock_animal_health_animal_date", "animal_id", "record_date"),
    )


class WeightRecord(Base):
    """Un relevé de poids ponctuel, pour tracer une courbe de croissance."""

    __tablename__ = "livestock_weight_records"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    animal_id: Mapped[str] = mapped_column(String(36), ForeignKey("livestock_animals.id"), nullable=False, index=True)

    weight_kg: Mapped[float] = mapped_column(Float, nullable=False)
    measured_at: Mapped[date] = mapped_column(Date, nullable=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    animal: Mapped["Animal"] = relationship(back_populates="weight_records")

    __table_args__ = (
        CheckConstraint("weight_kg >= 0", name="ck_weight_record_non_negative"),
        Index("ix_livestock_weight_animal_date", "animal_id", "measured_at"),
    )


class ReproductionRecord(Base):
    """
    Un événement de reproduction pour une femelle : chaleurs, insémination
    ou saillie, confirmation de gestation, mise bas ou avortement.
    `offspring_animal_id` peut référencer la fiche du petit créée à la
    mise bas, pour retrouver la filiation dans les deux sens.
    """

    __tablename__ = "livestock_reproduction_records"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    animal_id: Mapped[str] = mapped_column(String(36), ForeignKey("livestock_animals.id"), nullable=False, index=True)
    offspring_animal_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("livestock_animals.id"), nullable=True
    )

    event_type: Mapped[str] = mapped_column(String(30), nullable=False)
    event_date: Mapped[date] = mapped_column(Date, nullable=False)
    expected_birth_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    animal: Mapped["Animal"] = relationship(back_populates="reproduction_records", foreign_keys=[animal_id])
    offspring: Mapped["Animal | None"] = relationship(foreign_keys=[offspring_animal_id])

    __table_args__ = (Index("ix_livestock_reproduction_animal_date", "animal_id", "event_date"),)


class FeedPlan(Base):
    """
    Plan alimentaire recommandé pour un troupeau : besoins nutritionnels
    et quantités estimées, calculés selon l'espèce et l'effectif (voir
    livestock/feed_service.py), avec un coût journalier indicatif.
    """

    __tablename__ = "livestock_feed_plans"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    herd_id: Mapped[str] = mapped_column(String(36), ForeignKey("livestock_herds.id"), nullable=False, index=True)

    feed_type: Mapped[str] = mapped_column(String(100), nullable=False)
    daily_quantity_kg: Mapped[float] = mapped_column(Float, nullable=False)
    estimated_daily_cost: Mapped[float] = mapped_column(Float, nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="XOF")
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    herd: Mapped["Herd"] = relationship()

    __table_args__ = (
        CheckConstraint("daily_quantity_kg >= 0", name="ck_feed_plan_quantity_non_negative"),
        CheckConstraint("estimated_daily_cost >= 0", name="ck_feed_plan_cost_non_negative"),
        Index("ix_livestock_feed_plans_herd", "herd_id", "created_at"),
    )
