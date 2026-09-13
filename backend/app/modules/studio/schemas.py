import json
from datetime import datetime

from pydantic import BaseModel, ConfigDict, field_validator, computed_field

from app.modules.studio.models import TEMPLATE_CATEGORIES, FILTER_CATEGORIES, AI_VIDEO_STYLES

MAX_CANVAS_DATA_CHARS = 500_000  # ~500 Ko de JSON, largement suffisant pour un design riche
MAX_DIMENSION_PX = 10_000


def _validate_json_field(value: str, field_label: str) -> str:
    if len(value) > MAX_CANVAS_DATA_CHARS:
        raise ValueError(f"{field_label} dépasse la taille maximale autorisée.")
    try:
        json.loads(value)
    except (json.JSONDecodeError, TypeError):
        raise ValueError(f"{field_label} doit être une chaîne JSON valide.")
    return value


class TemplateCreate(BaseModel):
    name: str
    category: str
    width: int
    height: int
    canvas_data: str  # JSON sérialisé
    is_premium: bool = False

    @field_validator("category")
    @classmethod
    def category_valid(cls, value: str) -> str:
        if value not in TEMPLATE_CATEGORIES:
            raise ValueError(f"Catégorie invalide. Catégories valides : {', '.join(sorted(TEMPLATE_CATEGORIES))}.")
        return value

    @field_validator("width", "height")
    @classmethod
    def dimension_valid(cls, value: int) -> int:
        if not (1 <= value <= MAX_DIMENSION_PX):
            raise ValueError(f"Les dimensions doivent être comprises entre 1 et {MAX_DIMENSION_PX} pixels.")
        return value

    @field_validator("canvas_data")
    @classmethod
    def canvas_data_valid(cls, value: str) -> str:
        return _validate_json_field(value, "Le contenu du modèle")


class TemplateOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    author_id: str
    name: str
    category: str
    width: int
    height: int
    is_premium: bool
    is_published: bool
    created_at: datetime


class TemplateDetailOut(TemplateOut):
    canvas_data: str


class DesignProjectCreate(BaseModel):
    title: str
    category: str
    width: int
    height: int
    template_id: str | None = None
    canvas_data: str = "{}"

    @field_validator("title")
    @classmethod
    def title_valid(cls, value: str) -> str:
        cleaned = value.strip()
        if not (1 <= len(cleaned) <= 255):
            raise ValueError("Le titre doit contenir entre 1 et 255 caractères.")
        return cleaned

    @field_validator("category")
    @classmethod
    def category_valid(cls, value: str) -> str:
        if value not in TEMPLATE_CATEGORIES:
            raise ValueError(f"Catégorie invalide. Catégories valides : {', '.join(sorted(TEMPLATE_CATEGORIES))}.")
        return value

    @field_validator("width", "height")
    @classmethod
    def dimension_valid(cls, value: int) -> int:
        if not (1 <= value <= MAX_DIMENSION_PX):
            raise ValueError(f"Les dimensions doivent être comprises entre 1 et {MAX_DIMENSION_PX} pixels.")
        return value

    @field_validator("canvas_data")
    @classmethod
    def canvas_data_valid(cls, value: str) -> str:
        return _validate_json_field(value, "Le contenu du design")


class DesignProjectUpdate(BaseModel):
    title: str | None = None
    canvas_data: str | None = None

    @field_validator("canvas_data")
    @classmethod
    def canvas_data_valid(cls, value: str | None) -> str | None:
        if value is None:
            return value
        return _validate_json_field(value, "Le contenu du design")


class DesignProjectOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    owner_id: str
    template_id: str | None
    title: str
    category: str
    width: int
    height: int
    canvas_data: str
    created_at: datetime
    updated_at: datetime


class FilterOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    category: str
    is_premium: bool


class VideoProjectCreate(BaseModel):
    title: str
    resolution: str = "1080x1920"
    timeline_data: str = "{\"clips\": []}"

    @field_validator("title")
    @classmethod
    def title_valid(cls, value: str) -> str:
        cleaned = value.strip()
        if not (1 <= len(cleaned) <= 255):
            raise ValueError("Le titre doit contenir entre 1 et 255 caractères.")
        return cleaned

    @field_validator("timeline_data")
    @classmethod
    def timeline_data_valid(cls, value: str) -> str:
        return _validate_json_field(value, "La timeline vidéo")


class VideoProjectUpdate(BaseModel):
    title: str | None = None
    timeline_data: str | None = None
    duration_seconds: float | None = None

    @field_validator("timeline_data")
    @classmethod
    def timeline_data_valid(cls, value: str | None) -> str | None:
        if value is None:
            return value
        return _validate_json_field(value, "La timeline vidéo")

    @field_validator("duration_seconds")
    @classmethod
    def duration_non_negative(cls, value: float | None) -> float | None:
        if value is not None and value < 0:
            raise ValueError("La durée ne peut pas être négative.")
        return value


class VideoProjectOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    owner_id: str
    title: str
    resolution: str
    duration_seconds: float
    timeline_data: str
    render_status: str
    render_error: str | None = None
    created_at: datetime
    updated_at: datetime

    @computed_field
    @property
    def download_available(self) -> bool:
        # Ne jamais exposer le chemin serveur réel : uniquement s'il est
        # prêt. Le téléchargement se fait via GET /studio/videos/{id}/download.
        return self.render_status == "pret"


class MediaAssetOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    original_filename: str
    media_type: str
    created_at: datetime


class AiVideoGenerationRequest(BaseModel):
    prompt: str
    style: str = "2d"
    duration_seconds: int = 5
    resolution: str = "1920x1080"

    @field_validator("prompt")
    @classmethod
    def prompt_valid(cls, value: str) -> str:
        cleaned = value.strip()
        if not (10 <= len(cleaned) <= 2000):
            raise ValueError("Le prompt doit contenir entre 10 et 2000 caractères.")
        return cleaned

    @field_validator("style")
    @classmethod
    def style_valid(cls, value: str) -> str:
        if value not in AI_VIDEO_STYLES:
            raise ValueError(f"Style invalide. Styles valides : {', '.join(sorted(AI_VIDEO_STYLES))}.")
        return value

    @field_validator("duration_seconds")
    @classmethod
    def duration_valid(cls, value: int) -> int:
        if not (1 <= value <= 60):
            raise ValueError("La durée doit être comprise entre 1 et 60 secondes.")
        return value


class AiVideoGenerationJobOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    owner_id: str
    prompt: str
    style: str
    duration_seconds: int
    resolution: str
    status: str
    result_url: str | None
    error_message: str | None
    created_at: datetime
    updated_at: datetime
