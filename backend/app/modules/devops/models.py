"""
Modèles du module DevOps/Cloud.

`resource_type` et `provider` sont des champs texte libre — serveur,
conteneur Docker, cluster Kubernetes, base de données managée, bucket de
stockage, load balancer, ou tout autre type de ressource, chez AWS, GCP,
Azure, un hébergeur local ou tout autre fournisseur, sont tous couverts
sans exception, même principe que `species` (Élevage) et `sector`
(Gestion d'entreprise).
"""
import uuid
from datetime import datetime, timezone

from sqlalchemy import String, DateTime, ForeignKey, Text, CheckConstraint, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

RESOURCE_STATUSES = {"actif", "arrete", "maintenance", "supprime"}
DEPLOYMENT_ENVIRONMENTS = {"developpement", "staging", "production"}
DEPLOYMENT_STATUSES = {"en_attente", "en_cours", "reussi", "echoue", "annule", "annule_par_rollback"}
ALERT_SEVERITIES = {"info", "avertissement", "critique"}
ALERT_STATUSES = {"ouverte", "acquittee", "resolue"}
BACKUP_TYPES = {"complete", "incrementale"}
BACKUP_STATUSES = {"planifiee", "en_cours", "reussie", "echouee"}


def generate_uuid() -> str:
    return str(uuid.uuid4())


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class CloudResource(Base):
    __tablename__ = "devops_cloud_resources"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    owner_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), nullable=False, index=True)

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    resource_type: Mapped[str] = mapped_column(String(100), nullable=False, index=True)  # texte libre
    provider: Mapped[str] = mapped_column(String(100), nullable=False, index=True)  # texte libre
    region: Mapped[str | None] = mapped_column(String(100), nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="actif")
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    deployments: Mapped[list["Deployment"]] = relationship(back_populates="resource", cascade="all, delete-orphan")
    alerts: Mapped[list["MonitoringAlert"]] = relationship(back_populates="resource", cascade="all, delete-orphan")


class Deployment(Base):
    """Un déploiement (issu d'un pipeline CI/CD ou manuel) sur une ressource donnée."""

    __tablename__ = "devops_deployments"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    resource_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("devops_cloud_resources.id"), nullable=False, index=True
    )

    version_tag: Mapped[str] = mapped_column(String(100), nullable=False)  # ex: "v1.4.2", commit SHA...
    environment: Mapped[str] = mapped_column(String(20), nullable=False)
    status: Mapped[str] = mapped_column(String(30), default="en_attente")
    commit_reference: Mapped[str | None] = mapped_column(String(100), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Auto-référence : si ce déploiement est un rollback, pointe vers le déploiement problématique annulé.
    rollback_of_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("devops_deployments.id"), nullable=True
    )

    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    resource: Mapped["CloudResource"] = relationship(back_populates="deployments")

    __table_args__ = (
        Index("ix_devops_deployments_resource_env", "resource_id", "environment"),
    )


class MonitoringAlert(Base):
    """Une alerte de supervision déclenchée sur une ressource (constat, pas un agent de monitoring réel)."""

    __tablename__ = "devops_monitoring_alerts"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    resource_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("devops_cloud_resources.id"), nullable=False, index=True
    )

    severity: Mapped[str] = mapped_column(String(20), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="ouverte")

    triggered_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    resource: Mapped["CloudResource"] = relationship(back_populates="alerts")

    __table_args__ = (Index("ix_devops_alerts_resource_status", "resource_id", "status"),)


class BackupRecord(Base):
    """
    Enregistrement d'une sauvegarde : planification, statut et historique.
    Dans cet environnement, l'exécution reste un point d'extension —
    `run_backup` (voir service.py) est l'endroit où brancher une commande
    réelle (ex: `pg_dump`, export S3...) en production ; la structure de
    suivi (planification, statut, historique) est, elle, déjà complète.
    """

    __tablename__ = "devops_backup_records"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    owner_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), nullable=False, index=True)

    backup_type: Mapped[str] = mapped_column(String(20), nullable=False, default="complete")
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="planifiee")
    scheduled_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    executed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    file_reference: Mapped[str | None] = mapped_column(String(500), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    __table_args__ = (Index("ix_devops_backups_owner_date", "owner_id", "scheduled_at"),)
