"""
Modèles du module Agriculture.

Structure en trois niveaux, reflétant la réalité du terrain :
Field (parcelle) -> CropCycle (une culture plantée sur cette parcelle,
sur une période donnée) -> Activity (chaque intervention : irrigation,
fertilisation, traitement...). C'est ce qui permet le suivi des cultures,
les rendements et les analyses demandés dans la vision.
"""
import uuid
from datetime import datetime, date, timezone

from sqlalchemy import String, DateTime, Date, ForeignKey, Text, Float, CheckConstraint, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

CROP_CYCLE_STATUSES = {"planifie", "en_croissance", "recolte", "echoue"}
ACTIVITY_TYPES = {
    "semis", "irrigation", "fertilisation", "traitement_phytosanitaire",
    "desherbage", "recolte", "labour", "autre",
}

# --- Agriculture V2 ---
CALENDAR_TASK_TYPES = {
    "fertilisation", "traitement_phytosanitaire", "irrigation",
    "desherbage", "recolte", "controle_sol", "autre",
}
CALENDAR_TASK_STATUSES = {"prevue", "faite", "reportee", "annulee"}
DIAGNOSIS_STATUSES = {"en_analyse", "traite"}


def generate_uuid() -> str:
    return str(uuid.uuid4())


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Field(Base):
    """Une parcelle agricole appartenant à un utilisateur."""

    __tablename__ = "agri_fields"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    owner_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), nullable=False, index=True)

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    area_hectares: Mapped[float] = mapped_column(Float, nullable=False)
    soil_type: Mapped[str | None] = mapped_column(String(100), nullable=True)

    latitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    longitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    country: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    region: Mapped[str | None] = mapped_column(String(100), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    crop_cycles: Mapped[list["CropCycle"]] = relationship(back_populates="field", cascade="all, delete-orphan")

    __table_args__ = (CheckConstraint("area_hectares > 0", name="ck_field_area_positive"),)


class CropCycle(Base):
    """Une culture plantée sur une parcelle, sur une période donnée."""

    __tablename__ = "agri_crop_cycles"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    field_id: Mapped[str] = mapped_column(String(36), ForeignKey("agri_fields.id"), nullable=False, index=True)

    crop_name: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(20), default="planifie")

    planting_date: Mapped[date] = mapped_column(Date, nullable=False)
    expected_harvest_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    actual_harvest_date: Mapped[date | None] = mapped_column(Date, nullable=True)

    yield_amount: Mapped[float | None] = mapped_column(Float, nullable=True)
    yield_unit: Mapped[str | None] = mapped_column(String(20), nullable=True)  # kg, tonnes, sacs...

    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    field: Mapped["Field"] = relationship(back_populates="crop_cycles")
    activities: Mapped[list["Activity"]] = relationship(back_populates="crop_cycle", cascade="all, delete-orphan")

    __table_args__ = (
        CheckConstraint("yield_amount IS NULL OR yield_amount >= 0", name="ck_cropcycle_yield_non_negative"),
        Index("ix_agri_crop_cycles_field_status", "field_id", "status"),
    )


class Activity(Base):
    """Une intervention effectuée sur un cycle de culture (irrigation, traitement, etc.)."""

    __tablename__ = "agri_activities"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    crop_cycle_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("agri_crop_cycles.id"), nullable=False, index=True
    )

    activity_type: Mapped[str] = mapped_column(String(50), nullable=False)
    activity_date: Mapped[date] = mapped_column(Date, nullable=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    cost_amount: Mapped[float | None] = mapped_column(Float, nullable=True)
    cost_currency: Mapped[str | None] = mapped_column(String(3), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    crop_cycle: Mapped["CropCycle"] = relationship(back_populates="activities")

    __table_args__ = (CheckConstraint("cost_amount IS NULL OR cost_amount >= 0", name="ck_activity_cost_non_negative"),)


# ============================================================================
# AGRICULTURE V2 — Assistant agronome numérique
#
# Toutes les tables ci-dessous sont ADDITIVES : elles se rattachent aux
# tables existantes (Field, CropCycle) via clé étrangère, sans modifier
# leur schéma ni leur comportement. Un agriculteur qui n'utilise jamais
# ces fonctionnalités continue de fonctionner exactement comme avant.
# ============================================================================


class CropRecommendation(Base):
    """
    Une suggestion de culture générée pour une parcelle, tenant compte du
    sol, du climat, de la saison et du budget déclarés. Alimentée par
    Nexus AI (voir agriculture/ai_service.py) — jamais par un appel direct
    à un fournisseur d'IA externe, conformément à l'abstraction AIProvider
    déjà en place pour le module Nexus AI.
    """

    __tablename__ = "agri_crop_recommendations"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    field_id: Mapped[str] = mapped_column(String(36), ForeignKey("agri_fields.id"), nullable=False, index=True)

    crop_name: Mapped[str] = mapped_column(String(100), nullable=False)
    score: Mapped[float] = mapped_column(Float, nullable=False)  # 0 à 100, confiance de la recommandation
    rationale: Mapped[str] = mapped_column(Text, nullable=False)  # justification en langage naturel

    season: Mapped[str | None] = mapped_column(String(50), nullable=True)
    budget_amount: Mapped[float | None] = mapped_column(Float, nullable=True)
    budget_currency: Mapped[str | None] = mapped_column(String(3), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    field: Mapped["Field"] = relationship()

    __table_args__ = (
        CheckConstraint("score >= 0 AND score <= 100", name="ck_recommendation_score_range"),
        Index("ix_agri_crop_recommendations_field", "field_id", "created_at"),
    )


class CalendarTask(Base):
    """
    Une tâche du calendrier agricole automatique, générée quand un cycle
    de culture démarre (voir agriculture/calendar_service.py). Chaque
    tâche a une date prévue et un statut, indépendamment des Activity
    déjà enregistrées : une tâche planifiée devient une Activity réelle
    une fois effectuée, mais reste tracée ici pour le suivi des retards.
    """

    __tablename__ = "agri_calendar_tasks"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    crop_cycle_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("agri_crop_cycles.id"), nullable=False, index=True
    )

    task_type: Mapped[str] = mapped_column(String(50), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    due_date: Mapped[date] = mapped_column(Date, nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="prevue")
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    crop_cycle: Mapped["CropCycle"] = relationship()

    __table_args__ = (Index("ix_agri_calendar_tasks_cycle_due", "crop_cycle_id", "due_date"),)


class DiseaseDiagnosis(Base):
    """
    Un diagnostic de maladie soumis par l'agriculteur : symptômes décrits
    (et, à terme, une photo dont la référence de fichier est stockée ici),
    analysés par Nexus AI. `photo_reference` reste un simple identifiant
    de fichier (ex: nom d'objet de stockage) — Nexus ne stocke jamais de
    binaire d'image directement dans cette table.
    """

    __tablename__ = "agri_disease_diagnoses"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    crop_cycle_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("agri_crop_cycles.id"), nullable=False, index=True
    )

    symptoms_description: Mapped[str] = mapped_column(Text, nullable=False)
    photo_reference: Mapped[str | None] = mapped_column(String(500), nullable=True)

    diagnosis_text: Mapped[str] = mapped_column(Text, nullable=False)
    recommended_actions: Mapped[str] = mapped_column(Text, nullable=False)
    confidence: Mapped[float | None] = mapped_column(Float, nullable=True)  # 0 à 100

    status: Mapped[str] = mapped_column(String(20), default="en_analyse")

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    crop_cycle: Mapped["CropCycle"] = relationship()

    __table_args__ = (
        CheckConstraint("confidence IS NULL OR (confidence >= 0 AND confidence <= 100)", name="ck_diagnosis_confidence_range"),
        Index("ix_agri_disease_diagnoses_cycle", "crop_cycle_id", "created_at"),
    )


class FinancialProjection(Base):
    """
    Une projection économique prévisionnelle pour une parcelle : coûts
    déjà engagés + coûts restants estimés (déduits du calendrier),
    comparés à un revenu estimé (rendement prévu × prix de marché).
    Complète get_field_yield_summary (constaté a posteriori) avec une
    vision prévisionnelle, avant même la récolte.
    """

    __tablename__ = "agri_financial_projections"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    field_id: Mapped[str] = mapped_column(String(36), ForeignKey("agri_fields.id"), nullable=False, index=True)
    crop_cycle_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("agri_crop_cycles.id"), nullable=True, index=True
    )

    estimated_cost_total: Mapped[float] = mapped_column(Float, nullable=False)
    estimated_revenue_total: Mapped[float] = mapped_column(Float, nullable=False)
    estimated_profit: Mapped[float] = mapped_column(Float, nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="XOF")

    assumptions: Mapped[str | None] = mapped_column(Text, nullable=True)  # hypothèses utilisées (prix marché, etc.)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    field: Mapped["Field"] = relationship()

    __table_args__ = (
        CheckConstraint("estimated_cost_total >= 0", name="ck_projection_cost_non_negative"),
        CheckConstraint("estimated_revenue_total >= 0", name="ck_projection_revenue_non_negative"),
        Index("ix_agri_financial_projections_field", "field_id", "created_at"),
    )
