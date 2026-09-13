import json
from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, field_validator

from app.modules.devtools.models import PROJECT_STATUSES, TASK_STATUSES, TASK_PRIORITIES, API_METHODS


class ProjectCreate(BaseModel):
    name: str
    description: str
    project_type: str
    tech_stack: str | None = None
    repository_url: str | None = None

    @field_validator("name")
    @classmethod
    def name_valid(cls, value: str) -> str:
        cleaned = value.strip()
        if not (2 <= len(cleaned) <= 255):
            raise ValueError("Le nom du projet doit contenir entre 2 et 255 caractères.")
        return cleaned

    @field_validator("description")
    @classmethod
    def description_valid(cls, value: str) -> str:
        cleaned = value.strip()
        if len(cleaned) < 10:
            raise ValueError("La description doit contenir au moins 10 caractères.")
        return cleaned

    @field_validator("project_type")
    @classmethod
    def project_type_valid(cls, value: str) -> str:
        cleaned = value.strip().lower()
        if not (2 <= len(cleaned) <= 100):
            raise ValueError("Le type de projet doit contenir entre 2 et 100 caractères.")
        return cleaned


class ProjectUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    tech_stack: str | None = None
    repository_url: str | None = None


class ProjectStatusUpdate(BaseModel):
    status: str

    @field_validator("status")
    @classmethod
    def status_valid(cls, value: str) -> str:
        if value not in PROJECT_STATUSES:
            raise ValueError(f"Statut invalide. Statuts valides : {', '.join(sorted(PROJECT_STATUSES))}.")
        return value


class ProjectOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    owner_id: str
    name: str
    description: str
    project_type: str
    tech_stack: str | None
    repository_url: str | None
    status: str
    created_at: datetime
    updated_at: datetime


class TaskCreate(BaseModel):
    title: str
    description: str | None = None
    priority: str = "moyenne"
    due_date: date | None = None

    @field_validator("title")
    @classmethod
    def title_valid(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("Le titre de la tâche ne peut pas être vide.")
        return cleaned

    @field_validator("priority")
    @classmethod
    def priority_valid(cls, value: str) -> str:
        if value not in TASK_PRIORITIES:
            raise ValueError(f"Priorité invalide. Priorités valides : {', '.join(sorted(TASK_PRIORITIES))}.")
        return value


class TaskStatusUpdate(BaseModel):
    status: str

    @field_validator("status")
    @classmethod
    def status_valid(cls, value: str) -> str:
        if value not in TASK_STATUSES:
            raise ValueError(f"Statut invalide. Statuts valides : {', '.join(sorted(TASK_STATUSES))}.")
        return value


class TaskOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    project_id: str
    title: str
    description: str | None
    status: str
    priority: str
    due_date: date | None
    created_at: datetime
    updated_at: datetime


class CodeSnippetCreate(BaseModel):
    title: str
    language: str
    code: str
    description: str | None = None
    tags: str | None = None
    project_id: str | None = None

    @field_validator("title")
    @classmethod
    def title_valid(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("Le titre du snippet ne peut pas être vide.")
        return cleaned

    @field_validator("language")
    @classmethod
    def language_valid(cls, value: str) -> str:
        cleaned = value.strip().lower()
        if not cleaned:
            raise ValueError("Le langage ne peut pas être vide.")
        return cleaned

    @field_validator("code")
    @classmethod
    def code_valid(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Le code ne peut pas être vide.")
        if len(value) > 100_000:
            raise ValueError("Le snippet dépasse la taille maximale autorisée.")
        return value


class CodeSnippetOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    owner_id: str
    project_id: str | None
    title: str
    language: str
    code: str
    description: str | None
    tags: str | None
    created_at: datetime


class ApiEndpointCreate(BaseModel):
    method: str
    path: str
    description: str
    request_schema: str | None = None
    response_schema: str | None = None

    @field_validator("method")
    @classmethod
    def method_valid(cls, value: str) -> str:
        upper = value.upper()
        if upper not in API_METHODS:
            raise ValueError(f"Méthode invalide. Méthodes valides : {', '.join(sorted(API_METHODS))}.")
        return upper

    @field_validator("path")
    @classmethod
    def path_valid(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned.startswith("/"):
            raise ValueError("Le chemin de l'endpoint doit commencer par '/'.")
        return cleaned

    @field_validator("request_schema", "response_schema")
    @classmethod
    def schema_valid_json(cls, value: str | None) -> str | None:
        if value is None or value == "":
            return value
        try:
            json.loads(value)
        except json.JSONDecodeError:
            raise ValueError("Le schéma doit être une chaîne JSON valide.")
        return value


class ApiEndpointOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    project_id: str
    method: str
    path: str
    description: str
    request_schema: str | None
    response_schema: str | None
    created_at: datetime


class ProjectDashboard(BaseModel):
    project_id: str
    project_name: str
    total_tasks: int
    tasks_by_status: dict[str, int]
    overdue_tasks_count: int
