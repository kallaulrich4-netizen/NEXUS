from datetime import datetime

from pydantic import BaseModel, ConfigDict, field_validator

from app.modules.legal.models import LEGAL_CATEGORIES, CONSULTATION_STATUSES


class LegalResourceCreate(BaseModel):
    title: str
    category: str
    summary: str
    content: str
    jurisdiction_country: str
    language: str = "fr"

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
        if value not in LEGAL_CATEGORIES:
            raise ValueError(f"Catégorie invalide. Catégories valides : {', '.join(sorted(LEGAL_CATEGORIES))}.")
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


class LegalResourceOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    author_id: str
    title: str
    category: str
    summary: str
    content: str
    jurisdiction_country: str
    language: str
    is_reviewed: bool
    is_published: bool
    created_at: datetime
    updated_at: datetime


class LegalResourceListOut(BaseModel):
    """Version allégée pour les listes de recherche : sans le contenu complet."""
    model_config = ConfigDict(from_attributes=True)

    id: str
    title: str
    category: str
    summary: str
    jurisdiction_country: str
    language: str
    is_reviewed: bool
    created_at: datetime


class ConsultationRequestCreate(BaseModel):
    lawyer_listing_id: str
    category: str
    subject: str
    description: str

    @field_validator("category")
    @classmethod
    def category_valid(cls, value: str) -> str:
        if value not in LEGAL_CATEGORIES:
            raise ValueError(f"Catégorie invalide. Catégories valides : {', '.join(sorted(LEGAL_CATEGORIES))}.")
        return value

    @field_validator("subject")
    @classmethod
    def subject_valid(cls, value: str) -> str:
        cleaned = value.strip()
        if not (5 <= len(cleaned) <= 255):
            raise ValueError("L'objet doit contenir entre 5 et 255 caractères.")
        return cleaned

    @field_validator("description")
    @classmethod
    def description_valid(cls, value: str) -> str:
        cleaned = value.strip()
        if len(cleaned) < 20:
            raise ValueError("La description doit contenir au moins 20 caractères pour être utile à l'avocat.")
        return cleaned


class ConsultationStatusUpdate(BaseModel):
    status: str

    @field_validator("status")
    @classmethod
    def status_valid(cls, value: str) -> str:
        if value not in CONSULTATION_STATUSES:
            raise ValueError(f"Statut invalide. Statuts valides : {', '.join(CONSULTATION_STATUSES)}.")
        return value


class ConsultationRequestOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    client_id: str
    lawyer_listing_id: str
    category: str
    subject: str
    description: str
    status: str
    created_at: datetime
    updated_at: datetime
