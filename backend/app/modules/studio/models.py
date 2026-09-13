"""
Modèles du module Studio créatif — l'équivalent Nexus de Canva (design)
et CapCut (montage vidéo), fusionnés sous une seule marque.

Le contenu réel d'un design (calques, formes, textes, positions) et
d'un montage vidéo (clips, transitions, filtres appliqués) est stocké en
JSON dans `canvas_data` / `timeline_data`. C'est le standard de l'industrie
pour ce type d'éditeur (Canva, Figma, CapCut fonctionnent tous sur ce
principe) : la structure exacte est définie et interprétée par le
frontend (éditeur visuel), le backend la persiste et vérifie les droits
d'accès premium.

IMPORTANT — périmètre technique honnête : ce module gère la création,
la sauvegarde et les droits d'accès des projets de design et de montage.
Le RENDU final d'une vidéo (encodage réel du fichier .mp4 à partir de la
timeline) nécessite un pipeline de traitement média (ex: FFmpeg) tournant
sur un vrai serveur de production — voir `render.py` pour le point
d'intégration prévu à cet effet.
"""
import uuid
from datetime import datetime, timezone

from sqlalchemy import String, DateTime, ForeignKey, Text, Integer, Boolean, Index, CheckConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base

TEMPLATE_CATEGORIES = {
    "post_reseau_social", "story", "flyer", "affiche", "logo",
    "presentation", "carte_visite", "carte_etudiant", "banniere",
    "miniature_video", "autre",
}

FILTER_CATEGORIES = {"couleur", "cinematique", "vintage", "noir_et_blanc", "glow", "correction", "autre"}


def generate_uuid() -> str:
    return str(uuid.uuid4())


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Template(Base):
    """Un modèle de design de départ, façon Canva. Gratuit ou premium."""

    __tablename__ = "studio_templates"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    author_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), nullable=False, index=True)

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    category: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    width: Mapped[int] = mapped_column(Integer, nullable=False)
    height: Mapped[int] = mapped_column(Integer, nullable=False)
    canvas_data: Mapped[str] = mapped_column(Text, nullable=False)  # JSON : calques de départ

    is_premium: Mapped[bool] = mapped_column(Boolean, default=False)
    is_published: Mapped[bool] = mapped_column(Boolean, default=False)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class DesignProject(Base):
    """Un projet de design en cours d'édition par un utilisateur (façon Canva)."""

    __tablename__ = "studio_design_projects"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    owner_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), nullable=False, index=True)
    template_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("studio_templates.id"), nullable=True)

    title: Mapped[str] = mapped_column(String(255), nullable=False)
    category: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    width: Mapped[int] = mapped_column(Integer, nullable=False)
    height: Mapped[int] = mapped_column(Integer, nullable=False)
    canvas_data: Mapped[str] = mapped_column(Text, nullable=False)  # JSON : calques actuels

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    __table_args__ = (Index("ix_studio_design_owner_updated", "owner_id", "updated_at"),)


class Filter(Base):
    """Un filtre/effet du catalogue, façon CapCut. Gratuit ou premium."""

    __tablename__ = "studio_filters"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    category: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    is_premium: Mapped[bool] = mapped_column(Boolean, default=False)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class VideoProject(Base):
    """Un projet de montage vidéo (timeline de clips, filtres, transitions)."""

    __tablename__ = "studio_video_projects"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    owner_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), nullable=False, index=True)

    title: Mapped[str] = mapped_column(String(255), nullable=False)
    resolution: Mapped[str] = mapped_column(String(20), default="1080x1920")  # format vertical par défaut
    duration_seconds: Mapped[float] = mapped_column(default=0)
    timeline_data: Mapped[str] = mapped_column(Text, nullable=False)  # JSON : clips, filtres appliqués, transitions

    render_status: Mapped[str] = mapped_column(String(20), default="brouillon")  # brouillon | en_cours | pret | echoue
    rendered_file_path: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    render_error: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    __table_args__ = (Index("ix_studio_video_owner_updated", "owner_id", "updated_at"),)


class StudioMediaAsset(Base):
    """
    Un fichier média importé par l'utilisateur (image ou vidéo source),
    stocké localement (voir `app/core/media_storage.py`). Référencé par
    `media_id` dans les clips d'une timeline vidéo (`VideoProject.timeline_data`).
    """

    __tablename__ = "studio_media_assets"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    owner_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), nullable=False, index=True)

    original_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    stored_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    absolute_path: Mapped[str] = mapped_column(String(1000), nullable=False)
    media_type: Mapped[str] = mapped_column(String(10), nullable=False)  # "image" | "video"

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


AI_VIDEO_STYLES = {"2d", "3d", "ultra_realiste", "animation", "cinematique"}
AI_VIDEO_JOB_STATUSES = {"en_attente", "en_cours", "termine", "echoue"}


class AiVideoGenerationJob(Base):
    """
    Une demande de génération vidéo par IA à partir d'un prompt texte
    (façon Veo3/Runway/Pika). Toujours premium — voir `has_premium_access`.

    IMPORTANT — périmètre technique honnête : générer réellement une
    vidéo par IA depuis un prompt nécessite un modèle de fondation vidéo
    de pointe (Veo, Runway Gen-3, Pika...) accessible uniquement via
    l'API payante de son fournisseur. Ce modèle stocke la demande et son
    statut ; l'appel réel au fournisseur se fait via l'abstraction
    `ai_video_provider.py`, à brancher avec une vraie clé d'API en
    production. Sans cela, un job reste à "en_attente" indéfiniment —
    c'est volontaire, plutôt que de simuler un faux résultat.
    """

    __tablename__ = "studio_ai_video_jobs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    owner_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), nullable=False, index=True)

    prompt: Mapped[str] = mapped_column(Text, nullable=False)
    style: Mapped[str] = mapped_column(String(20), nullable=False)  # 2d | 3d | ultra_realiste | animation | cinematique
    duration_seconds: Mapped[int] = mapped_column(Integer, default=5)
    resolution: Mapped[str] = mapped_column(String(20), default="1920x1080")

    status: Mapped[str] = mapped_column(String(20), default="en_attente")
    result_url: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    __table_args__ = (
        CheckConstraint("duration_seconds > 0 AND duration_seconds <= 60", name="ck_ai_video_duration_range"),
        Index("ix_studio_ai_video_owner_created", "owner_id", "created_at"),
    )
