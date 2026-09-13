from datetime import datetime

from pydantic import BaseModel, ConfigDict, field_validator

from app.modules.devops.models import (
    RESOURCE_STATUSES, DEPLOYMENT_ENVIRONMENTS, DEPLOYMENT_STATUSES,
    ALERT_SEVERITIES, ALERT_STATUSES, BACKUP_TYPES, BACKUP_STATUSES,
)


class CloudResourceCreate(BaseModel):
    name: str
    resource_type: str
    provider: str
    region: str | None = None
    notes: str | None = None

    @field_validator("name")
    @classmethod
    def name_valid(cls, value: str) -> str:
        cleaned = value.strip()
        if not (2 <= len(cleaned) <= 255):
            raise ValueError("Le nom de la ressource doit contenir entre 2 et 255 caractères.")
        return cleaned

    @field_validator("resource_type", "provider")
    @classmethod
    def free_text_valid(cls, value: str) -> str:
        cleaned = value.strip().lower()
        if not cleaned:
            raise ValueError("Ce champ ne peut pas être vide.")
        return cleaned


class CloudResourceStatusUpdate(BaseModel):
    status: str

    @field_validator("status")
    @classmethod
    def status_valid(cls, value: str) -> str:
        if value not in RESOURCE_STATUSES:
            raise ValueError(f"Statut invalide. Statuts valides : {', '.join(sorted(RESOURCE_STATUSES))}.")
        return value


class CloudResourceOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    owner_id: str
    name: str
    resource_type: str
    provider: str
    region: str | None
    status: str
    notes: str | None
    created_at: datetime
    updated_at: datetime


class DeploymentCreate(BaseModel):
    version_tag: str
    environment: str
    commit_reference: str | None = None
    notes: str | None = None

    @field_validator("version_tag")
    @classmethod
    def version_valid(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("Le tag de version ne peut pas être vide.")
        return cleaned

    @field_validator("environment")
    @classmethod
    def environment_valid(cls, value: str) -> str:
        if value not in DEPLOYMENT_ENVIRONMENTS:
            raise ValueError(
                f"Environnement invalide. Environnements valides : {', '.join(sorted(DEPLOYMENT_ENVIRONMENTS))}."
            )
        return value


class DeploymentStatusUpdate(BaseModel):
    status: str

    @field_validator("status")
    @classmethod
    def status_valid(cls, value: str) -> str:
        if value not in DEPLOYMENT_STATUSES:
            raise ValueError(f"Statut invalide. Statuts valides : {', '.join(sorted(DEPLOYMENT_STATUSES))}.")
        return value


class DeploymentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    resource_id: str
    version_tag: str
    environment: str
    status: str
    commit_reference: str | None
    notes: str | None
    rollback_of_id: str | None
    started_at: datetime
    finished_at: datetime | None


class MonitoringAlertCreate(BaseModel):
    severity: str
    message: str

    @field_validator("severity")
    @classmethod
    def severity_valid(cls, value: str) -> str:
        if value not in ALERT_SEVERITIES:
            raise ValueError(f"Sévérité invalide. Valeurs valides : {', '.join(sorted(ALERT_SEVERITIES))}.")
        return value

    @field_validator("message")
    @classmethod
    def message_valid(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("Le message d'alerte ne peut pas être vide.")
        return cleaned


class MonitoringAlertStatusUpdate(BaseModel):
    status: str

    @field_validator("status")
    @classmethod
    def status_valid(cls, value: str) -> str:
        if value not in ALERT_STATUSES:
            raise ValueError(f"Statut invalide. Statuts valides : {', '.join(sorted(ALERT_STATUSES))}.")
        return value


class MonitoringAlertOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    resource_id: str
    severity: str
    message: str
    status: str
    triggered_at: datetime
    resolved_at: datetime | None


class InfrastructureDashboard(BaseModel):
    total_resources: int
    resources_by_status: dict[str, int]
    open_alerts_by_severity: dict[str, int]
    last_deployment_status_by_environment: dict[str, str]


# --- Sauvegardes ---

class BackupCreate(BaseModel):
    backup_type: str = "complete"
    notes: str | None = None

    @field_validator("backup_type")
    @classmethod
    def backup_type_valid(cls, value: str) -> str:
        if value not in BACKUP_TYPES:
            raise ValueError(f"Type de sauvegarde invalide. Valeurs valides : {', '.join(sorted(BACKUP_TYPES))}.")
        return value


class BackupOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    backup_type: str
    status: str
    scheduled_at: datetime
    executed_at: datetime | None
    file_reference: str | None
    notes: str | None
    created_at: datetime


# --- Monitoring système ---

class SystemHealth(BaseModel):
    status: str  # "operationnel", "degrade", "indisponible"
    uptime_seconds: float
    cpu_percent: float | None
    memory_percent: float | None
    disk_percent: float | None
    database_reachable: bool
    metrics_source: str  # "psutil" ou "estimation" — transparence sur la précision des chiffres
