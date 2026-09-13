import json

from sqlalchemy.orm import Session

from app.core import media_storage
from app.core.entitlements import has_premium_access
from app.modules.auth.models import User
from app.modules.studio.models import Template, DesignProject, Filter, VideoProject, AiVideoGenerationJob, StudioMediaAsset
from app.modules.studio.render import RenderError


class TemplateNotFoundError(Exception):
    """Levée quand un modèle n'existe pas ou n'est pas publié."""


class PremiumRequiredError(Exception):
    """Levée quand une fonctionnalité premium est utilisée sans accès actif."""


class ProjectNotFoundError(Exception):
    """Levée quand un projet (design ou vidéo) n'existe pas ou n'appartient pas à l'utilisateur."""


class FilterNotFoundError(Exception):
    """Levée quand un filtre référencé dans une timeline n'existe pas."""


class RenderInputError(Exception):
    """La timeline ou les fichiers référencés sont invalides pour le rendu."""


# --- Modèles (templates) ---

def submit_template(db: Session, author_id: str, data) -> Template:
    template = Template(author_id=author_id, is_published=False, **data.model_dump())
    db.add(template)
    db.commit()
    db.refresh(template)
    return template


def search_templates(
    db: Session, category: str | None = None, premium_only: bool | None = None, limit: int = 20, offset: int = 0
) -> list[Template]:
    q = db.query(Template).filter(Template.is_published.is_(True))
    if category:
        q = q.filter(Template.category == category)
    if premium_only is not None:
        q = q.filter(Template.is_premium.is_(premium_only))
    return q.order_by(Template.created_at.desc()).offset(offset).limit(limit).all()


def get_template(db: Session, template_id: str) -> Template:
    template = db.query(Template).filter(Template.id == template_id, Template.is_published.is_(True)).first()
    if template is None:
        raise TemplateNotFoundError("Modèle introuvable ou non publié.")
    return template


class NotAuthorizedError(Exception):
    """Levée quand un utilisateur non autorisé tente une action réservée (ex: publication)."""


def publish_template(db: Session, template_id: str, requesting_user: object) -> Template:
    """
    Publie un modèle, le rendant visible dans les recherches publiques.
    Réservé au super-administrateur (voir app/core/entitlements.py) : un
    modèle non relu ne doit jamais atteindre les utilisateurs finaux.
    """
    if not getattr(requesting_user, "is_superuser", False):
        raise NotAuthorizedError("Seul un super-administrateur peut publier un modèle.")

    template = db.query(Template).filter(Template.id == template_id).first()
    if template is None:
        raise TemplateNotFoundError("Modèle introuvable.")
    template.is_published = True
    db.commit()
    db.refresh(template)
    return template


# --- Projets de design ---

def create_design_project(db: Session, owner: User, data) -> DesignProject:
    canvas_data = data.canvas_data
    template_id = data.template_id

    if template_id:
        template = get_template(db, template_id)
        if template.is_premium and not has_premium_access(owner):
            raise PremiumRequiredError(
                "Ce modèle est réservé aux comptes premium ou en période d'essai active."
            )
        # Si le projet part d'un modèle et qu'aucun contenu n'est fourni,
        # on démarre depuis le contenu du modèle.
        if canvas_data in ("{}", ""):
            canvas_data = template.canvas_data

    project = DesignProject(
        owner_id=owner.id,
        template_id=template_id,
        title=data.title,
        category=data.category,
        width=data.width,
        height=data.height,
        canvas_data=canvas_data,
    )
    db.add(project)
    db.commit()
    db.refresh(project)
    return project


def get_design_project(db: Session, project_id: str, owner_id: str) -> DesignProject:
    project = (
        db.query(DesignProject)
        .filter(DesignProject.id == project_id, DesignProject.owner_id == owner_id)
        .first()
    )
    if project is None:
        raise ProjectNotFoundError("Projet de design introuvable.")
    return project


def list_design_projects(db: Session, owner_id: str) -> list[DesignProject]:
    return (
        db.query(DesignProject)
        .filter(DesignProject.owner_id == owner_id)
        .order_by(DesignProject.updated_at.desc())
        .all()
    )


def update_design_project(db: Session, project_id: str, owner_id: str, data) -> DesignProject:
    project = get_design_project(db, project_id, owner_id)
    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(project, key, value)
    db.commit()
    db.refresh(project)
    return project


def delete_design_project(db: Session, project_id: str, owner_id: str) -> None:
    project = get_design_project(db, project_id, owner_id)
    db.delete(project)
    db.commit()


# --- Filtres (catalogue façon CapCut) ---

def create_filter(db: Session, name: str, category: str, is_premium: bool) -> Filter:
    filter_obj = Filter(name=name, category=category, is_premium=is_premium)
    db.add(filter_obj)
    db.commit()
    db.refresh(filter_obj)
    return filter_obj


def list_filters(db: Session, category: str | None = None) -> list[Filter]:
    q = db.query(Filter)
    if category:
        q = q.filter(Filter.category == category)
    return q.order_by(Filter.category, Filter.name).all()


def _extract_filter_ids(timeline_data: str) -> set[str]:
    """Extrait tous les identifiants de filtre référencés dans une timeline."""
    try:
        parsed = json.loads(timeline_data)
    except json.JSONDecodeError:
        return set()
    filter_ids = set()
    for clip in parsed.get("clips", []):
        if isinstance(clip, dict) and clip.get("filter_id"):
            filter_ids.add(clip["filter_id"])
    return filter_ids


def _check_timeline_premium_filters(db: Session, timeline_data: str, owner: User) -> None:
    filter_ids = _extract_filter_ids(timeline_data)
    if not filter_ids:
        return
    filters = db.query(Filter).filter(Filter.id.in_(filter_ids)).all()
    found_ids = {f.id for f in filters}
    missing = filter_ids - found_ids
    if missing:
        raise FilterNotFoundError(f"Filtre(s) introuvable(s) : {', '.join(missing)}.")

    uses_premium_filter = any(f.is_premium for f in filters)
    if uses_premium_filter and not has_premium_access(owner):
        raise PremiumRequiredError(
            "Un ou plusieurs filtres utilisés sont réservés aux comptes premium ou en période d'essai active."
        )


# --- Projets vidéo ---

def create_video_project(db: Session, owner: User, data) -> VideoProject:
    _check_timeline_premium_filters(db, data.timeline_data, owner)

    project = VideoProject(
        owner_id=owner.id,
        title=data.title,
        resolution=data.resolution,
        timeline_data=data.timeline_data,
        render_status="brouillon",
    )
    db.add(project)
    db.commit()
    db.refresh(project)
    return project


def get_video_project(db: Session, project_id: str, owner_id: str) -> VideoProject:
    project = (
        db.query(VideoProject)
        .filter(VideoProject.id == project_id, VideoProject.owner_id == owner_id)
        .first()
    )
    if project is None:
        raise ProjectNotFoundError("Projet vidéo introuvable.")
    return project


def list_video_projects(db: Session, owner_id: str) -> list[VideoProject]:
    return (
        db.query(VideoProject)
        .filter(VideoProject.owner_id == owner_id)
        .order_by(VideoProject.updated_at.desc())
        .all()
    )


def update_video_project(db: Session, project_id: str, owner_id: str, owner: User, data) -> VideoProject:
    project = get_video_project(db, project_id, owner_id)
    updates = data.model_dump(exclude_unset=True)

    if "timeline_data" in updates:
        _check_timeline_premium_filters(db, updates["timeline_data"], owner)

    for key, value in updates.items():
        setattr(project, key, value)
    db.commit()
    db.refresh(project)
    return project


def delete_video_project(db: Session, project_id: str, owner_id: str) -> None:
    project = get_video_project(db, project_id, owner_id)
    if project.rendered_file_path:
        media_storage.delete_file(project.rendered_file_path)
    db.delete(project)
    db.commit()


# --- Médias importés (images/vidéos sources pour le montage) ---

def save_media_upload(db: Session, owner: User, upload, storage_path: str, max_upload_mb: int) -> StudioMediaAsset:
    stored_filename, absolute_path, media_type = media_storage.save_upload(
        storage_path, owner.id, upload, max_upload_mb * 1024 * 1024
    )
    asset = StudioMediaAsset(
        owner_id=owner.id,
        original_filename=upload.filename or stored_filename,
        stored_filename=stored_filename,
        absolute_path=absolute_path,
        media_type=media_type,
    )
    db.add(asset)
    db.commit()
    db.refresh(asset)
    return asset


def list_media_assets(db: Session, owner_id: str) -> list[StudioMediaAsset]:
    return (
        db.query(StudioMediaAsset)
        .filter(StudioMediaAsset.owner_id == owner_id)
        .order_by(StudioMediaAsset.created_at.desc())
        .all()
    )


def delete_media_asset(db: Session, asset_id: str, owner_id: str) -> None:
    asset = (
        db.query(StudioMediaAsset)
        .filter(StudioMediaAsset.id == asset_id, StudioMediaAsset.owner_id == owner_id)
        .first()
    )
    if asset is None:
        raise ProjectNotFoundError("Fichier média introuvable.")
    media_storage.delete_file(asset.absolute_path)
    db.delete(asset)
    db.commit()


# --- Rendu vidéo réel (montage façon CapCut/InShot, via FFmpeg) ---

def _resolve_clips_for_render(db: Session, owner_id: str, timeline_data: str) -> list[dict]:
    """
    Transforme les clips tels que stockés (media_id, filter_id) en clips
    prêts pour le moteur de rendu (source_path résolu sur le disque,
    filter_category résolue) — render.py ne touche jamais à la base de
    données, uniquement à des chemins de fichiers déjà résolus.
    """
    parsed = json.loads(timeline_data)
    clips = parsed.get("clips", [])
    if not clips:
        raise RenderInputError("La timeline ne contient aucun clip à assembler.")

    media_ids = {c["media_id"] for c in clips if isinstance(c, dict) and c.get("media_id")}
    filter_ids = {c["filter_id"] for c in clips if isinstance(c, dict) and c.get("filter_id")}

    assets_by_id = {}
    if media_ids:
        assets = (
            db.query(StudioMediaAsset)
            .filter(StudioMediaAsset.id.in_(media_ids), StudioMediaAsset.owner_id == owner_id)
            .all()
        )
        assets_by_id = {a.id: a for a in assets}
        missing = media_ids - assets_by_id.keys()
        if missing:
            raise RenderInputError(f"Fichier(s) média introuvable(s) : {', '.join(missing)}.")

    filters_by_id = {}
    if filter_ids:
        filters = db.query(Filter).filter(Filter.id.in_(filter_ids)).all()
        filters_by_id = {f.id: f for f in filters}

    resolved = []
    for clip in clips:
        resolved_clip = dict(clip)
        if clip.get("media_id"):
            resolved_clip["source_path"] = assets_by_id[clip["media_id"]].absolute_path
        if clip.get("filter_id") and clip["filter_id"] in filters_by_id:
            resolved_clip["filter_category"] = filters_by_id[clip["filter_id"]].category
        resolved.append(resolved_clip)
    return resolved


def render_video_project(db: Session, project_id: str, owner_id: str, render_provider, storage_path: str) -> VideoProject:
    """
    Lance le rendu réel d'un projet vidéo, de façon synchrone (pas de file
    d'attente de tâches en V1 — voir chapitre 12 du manuel pour la
    recommandation de passer par une tâche asynchrone si les vidéos ou le
    volume d'utilisateurs grandissent). Met à jour render_status à chaque
    étape pour que le frontend puisse afficher une progression simple.
    """
    project = get_video_project(db, project_id, owner_id)
    project.render_status = "en_cours"
    project.render_error = None
    db.commit()

    try:
        clips = _resolve_clips_for_render(db, owner_id, project.timeline_data)
        output_dir = media_storage.renders_dir(storage_path)
        output_path = str(output_dir / f"{project.id}.mp4")

        render_provider.render(clips, project.resolution, output_path)

        project.rendered_file_path = output_path
        project.render_status = "pret"
    except (RenderInputError, RenderError) as exc:
        project.render_status = "echoue"
        project.render_error = str(exc)
    except Exception as exc:  # filet de sécurité : ne jamais planter la requête HTTP
        project.render_status = "echoue"
        project.render_error = "Erreur inattendue pendant le rendu."

    db.commit()
    db.refresh(project)
    return project


# --- Génération vidéo par IA (façon Veo3) ---

def create_ai_video_job(db: Session, owner: User, data, provider) -> AiVideoGenerationJob:
    """
    Toujours réservé au premium : la génération vidéo par IA a un coût de
    calcul réel côté fournisseur, contrairement aux autres fonctionnalités
    du Studio qui peuvent rester gratuites.
    """
    if not has_premium_access(owner):
        raise PremiumRequiredError(
            "La génération vidéo par IA est réservée aux comptes premium ou en période d'essai active."
        )

    job = AiVideoGenerationJob(
        owner_id=owner.id,
        prompt=data.prompt,
        style=data.style,
        duration_seconds=data.duration_seconds,
        resolution=data.resolution,
        status="en_attente",
    )
    db.add(job)
    db.commit()
    db.refresh(job)

    result = provider.submit(data.prompt, data.style, data.duration_seconds, data.resolution)
    job.status = result["status"]
    job.result_url = result.get("result_url")
    job.error_message = result.get("error_message")
    db.commit()
    db.refresh(job)
    return job


def get_ai_video_job(db: Session, job_id: str, owner_id: str) -> AiVideoGenerationJob:
    job = (
        db.query(AiVideoGenerationJob)
        .filter(AiVideoGenerationJob.id == job_id, AiVideoGenerationJob.owner_id == owner_id)
        .first()
    )
    if job is None:
        raise ProjectNotFoundError("Job de génération vidéo introuvable.")
    return job


def list_ai_video_jobs(db: Session, owner_id: str) -> list[AiVideoGenerationJob]:
    return (
        db.query(AiVideoGenerationJob)
        .filter(AiVideoGenerationJob.owner_id == owner_id)
        .order_by(AiVideoGenerationJob.created_at.desc())
        .all()
    )
