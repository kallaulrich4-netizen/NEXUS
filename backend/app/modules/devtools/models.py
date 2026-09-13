"""
Modèles du module Développement logiciel.

Ce module gère la partie GESTION DE PROJET pour les développeurs (projets,
tâches, bibliothèque de code réutilisable, documentation d'API) — pas la
génération de code elle-même, qui relève du module Nexus AI (voir
`app/modules/ai_assistant`). Un développeur bloqué peut utiliser Nexus AI
pour générer ou déboguer du code, puis organiser son travail ici. C'est le
même principe de non-duplication déjà appliqué entre Éducation et Nexus AI.

`project_type` est un champ texte libre : application web, mobile,
logiciel desktop, API, microservice, script, ou tout autre type de
projet logiciel sont couverts sans exception.
"""
import uuid
from datetime import datetime, date, timezone

from sqlalchemy import String, DateTime, Date, ForeignKey, Text, CheckConstraint, Index, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

PROJECT_STATUSES = {"planification", "developpement", "test", "production", "archive"}
TASK_STATUSES = {"a_faire", "en_cours", "en_revue", "termine", "bloque"}
TASK_PRIORITIES = {"basse", "moyenne", "haute", "critique"}
API_METHODS = {"GET", "POST", "PUT", "PATCH", "DELETE"}


def generate_uuid() -> str:
    return str(uuid.uuid4())


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Project(Base):
    __tablename__ = "devtools_projects"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    owner_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), nullable=False, index=True)

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    project_type: Mapped[str] = mapped_column(String(100), nullable=False, index=True)  # texte libre
    tech_stack: Mapped[str | None] = mapped_column(String(500), nullable=True)  # ex: "Python, FastAPI, PostgreSQL"
    repository_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="planification")

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    tasks: Mapped[list["Task"]] = relationship(back_populates="project", cascade="all, delete-orphan")
    endpoints: Mapped[list["ApiEndpointDoc"]] = relationship(back_populates="project", cascade="all, delete-orphan")


class Task(Base):
    __tablename__ = "devtools_tasks"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    project_id: Mapped[str] = mapped_column(String(36), ForeignKey("devtools_projects.id"), nullable=False, index=True)

    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="a_faire")
    priority: Mapped[str] = mapped_column(String(20), default="moyenne")
    due_date: Mapped[date | None] = mapped_column(Date, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    project: Mapped["Project"] = relationship(back_populates="tasks")

    __table_args__ = (Index("ix_devtools_tasks_project_status", "project_id", "status"),)


class CodeSnippet(Base):
    """Bibliothèque personnelle de code réutilisable."""

    __tablename__ = "devtools_code_snippets"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    owner_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), nullable=False, index=True)
    project_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("devtools_projects.id"), nullable=True)

    title: Mapped[str] = mapped_column(String(255), nullable=False)
    language: Mapped[str] = mapped_column(String(50), nullable=False, index=True)  # texte libre : python, js, sql...
    code: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    tags: Mapped[str | None] = mapped_column(String(500), nullable=True)  # séparés par des virgules

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    __table_args__ = (Index("ix_devtools_snippets_owner_language", "owner_id", "language"),)


class ApiEndpointDoc(Base):
    """Documentation d'un endpoint d'API, rattachée à un projet."""

    __tablename__ = "devtools_api_endpoints"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    project_id: Mapped[str] = mapped_column(String(36), ForeignKey("devtools_projects.id"), nullable=False, index=True)

    method: Mapped[str] = mapped_column(String(10), nullable=False)
    path: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    request_schema: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON en texte
    response_schema: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON en texte

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    project: Mapped["Project"] = relationship(back_populates="endpoints")

    __table_args__ = (UniqueConstraint("project_id", "method", "path", name="uq_endpoint_project_method_path"),)
