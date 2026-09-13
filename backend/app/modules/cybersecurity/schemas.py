from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, field_validator

from app.modules.cybersecurity.models import (
    ASSET_TYPES, AUDIT_STATUSES, FINDING_SEVERITIES, FINDING_STATUSES, GUIDE_CATEGORIES,
)


class SecurityAssetCreate(BaseModel):
    name: str
    asset_type: str
    identifier: str
    description: str | None = None

    @field_validator("name")
    @classmethod
    def name_valid(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("Le nom de l'actif ne peut pas être vide.")
        return cleaned

    @field_validator("asset_type")
    @classmethod
    def asset_type_valid(cls, value: str) -> str:
        if value not in ASSET_TYPES:
            raise ValueError(f"Type d'actif invalide. Types valides : {', '.join(sorted(ASSET_TYPES))}.")
        return value

    @field_validator("identifier")
    @classmethod
    def identifier_valid(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("L'identifiant (URL, IP, nom d'hôte) ne peut pas être vide.")
        return cleaned


class SecurityAssetOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    owner_id: str
    name: str
    asset_type: str
    identifier: str
    description: str | None
    created_at: datetime


class SecurityAuditCreate(BaseModel):
    ownership_confirmed: bool
    scheduled_date: date | None = None

    @field_validator("ownership_confirmed")
    @classmethod
    def ownership_must_be_confirmed(cls, value: bool) -> bool:
        if not value:
            raise ValueError(
                "Vous devez confirmer être propriétaire de ce système ou disposer d'une autorisation "
                "explicite de son propriétaire pour demander un audit."
            )
        return value


class SecurityAuditStatusUpdate(BaseModel):
    status: str
    summary: str | None = None

    @field_validator("status")
    @classmethod
    def status_valid(cls, value: str) -> str:
        if value not in AUDIT_STATUSES:
            raise ValueError(f"Statut invalide. Statuts valides : {', '.join(sorted(AUDIT_STATUSES))}.")
        return value


class SecurityAuditOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    asset_id: str
    requested_by: str
    ownership_confirmed: bool
    status: str
    scheduled_date: date | None
    summary: str | None
    created_at: datetime
    updated_at: datetime


class FindingCreate(BaseModel):
    title: str
    severity: str
    description: str
    remediation_advice: str

    @field_validator("title")
    @classmethod
    def title_valid(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("Le titre du constat ne peut pas être vide.")
        return cleaned

    @field_validator("severity")
    @classmethod
    def severity_valid(cls, value: str) -> str:
        if value not in FINDING_SEVERITIES:
            raise ValueError(f"Sévérité invalide. Valeurs valides : {', '.join(sorted(FINDING_SEVERITIES))}.")
        return value

    @field_validator("description")
    @classmethod
    def description_valid(cls, value: str) -> str:
        cleaned = value.strip()
        if len(cleaned) < 10:
            raise ValueError("La description doit contenir au moins 10 caractères.")
        return cleaned

    @field_validator("remediation_advice")
    @classmethod
    def remediation_valid(cls, value: str) -> str:
        cleaned = value.strip()
        if len(cleaned) < 10:
            raise ValueError("Le conseil de remédiation doit contenir au moins 10 caractères.")
        return cleaned


class FindingStatusUpdate(BaseModel):
    status: str

    @field_validator("status")
    @classmethod
    def status_valid(cls, value: str) -> str:
        if value not in FINDING_STATUSES:
            raise ValueError(f"Statut invalide. Statuts valides : {', '.join(sorted(FINDING_STATUSES))}.")
        return value


class FindingOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    audit_id: str
    title: str
    severity: str
    description: str
    remediation_advice: str
    status: str
    created_at: datetime
    updated_at: datetime


class SecurityGuideCreate(BaseModel):
    title: str
    category: str
    summary: str
    content: str

    @field_validator("title")
    @classmethod
    def title_valid(cls, value: str) -> str:
        cleaned = value.strip()
        if not (5 <= len(cleaned) <= 255):
            raise ValueError("Le titre doit contenir entre 5 et 255 caractères.")
        return cleaned

    @field_validator("category")
    @classmethod
    def category_valid(cls, value: str) -> str:
        if value not in GUIDE_CATEGORIES:
            raise ValueError(f"Catégorie invalide. Catégories valides : {', '.join(sorted(GUIDE_CATEGORIES))}.")
        return value

    @field_validator("summary")
    @classmethod
    def summary_valid(cls, value: str) -> str:
        cleaned = value.strip()
        if not (10 <= len(cleaned) <= 500):
            raise ValueError("Le résumé doit contenir entre 10 et 500 caractères.")
        return cleaned

    @field_validator("content")
    @classmethod
    def content_valid(cls, value: str) -> str:
        cleaned = value.strip()
        if len(cleaned) < 50:
            raise ValueError("Le contenu doit contenir au moins 50 caractères.")
        return cleaned


class SecurityGuideOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    author_id: str
    title: str
    category: str
    summary: str
    content: str
    is_reviewed: bool
    is_published: bool
    created_at: datetime
    updated_at: datetime


class SecurityGuideListOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    title: str
    category: str
    summary: str
    created_at: datetime


class RiskDashboard(BaseModel):
    asset_id: str
    asset_name: str
    total_findings: int
    open_findings_by_severity: dict[str, int]
    critical_open_count: int
