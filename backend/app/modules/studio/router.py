from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.database import get_db
from app.core.entitlements import has_premium_access
from app.core.media_storage import UnsupportedMediaTypeError, MediaTooLargeError
from app.core.rate_limit import rate_limit
from app.modules.auth.router import get_current_user
from app.modules.auth.models import User
from app.modules.studio import service
from app.modules.studio.ai_video_provider import get_ai_video_provider
from app.modules.studio.render import get_render_provider
from app.modules.studio.schemas import (
    TemplateCreate, TemplateOut, TemplateDetailOut,
    DesignProjectCreate, DesignProjectUpdate, DesignProjectOut,
    FilterOut,
    VideoProjectCreate, VideoProjectUpdate, VideoProjectOut,
    MediaAssetOut,
    AiVideoGenerationRequest, AiVideoGenerationJobOut,
)

router = APIRouter(prefix="/studio", tags=["Studio créatif"])
_settings = get_settings()


@router.get("/account/premium-status", response_model=dict)
def get_premium_status(current_user: User = Depends(get_current_user)):
    """Indique si l'utilisateur a actuellement accès aux fonctionnalités premium (essai ou abonnement)."""
    return {
        "has_premium_access": has_premium_access(current_user),
        "trial_ends_at": current_user.trial_ends_at,
        "premium_until": current_user.premium_until,
    }


# --- Modèles graphiques (Templates) ---

@router.post(
    "/templates",
    response_model=TemplateOut,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(rate_limit(max_requests=10, window_seconds=60))],
)
def submit_template(
    data: TemplateCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return service.submit_template(db, current_user.id, data)


@router.get("/templates/search", response_model=list[TemplateOut])
def search_templates(
    category: str | None = Query(None),
    premium_only: bool | None = Query(None),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
):
    return service.search_templates(db, category=category, premium_only=premium_only, limit=limit, offset=offset)


@router.get("/templates/{template_id}", response_model=TemplateDetailOut)
def get_template(template_id: str, db: Session = Depends(get_db)):
    try:
        return service.get_template(db, template_id)
    except service.TemplateNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))


@router.post("/templates/{template_id}/publish", response_model=TemplateOut)
def publish_template(
    template_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Réservé au super-administrateur — voir INITIAL_SUPERUSER_EMAIL dans le README."""
    try:
        return service.publish_template(db, template_id, current_user)
    except service.NotAuthorizedError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc))
    except service.TemplateNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))


# --- Projets de design ---

@router.post(
    "/design-projects",
    response_model=DesignProjectOut,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(rate_limit(max_requests=30, window_seconds=60))],
)
def create_design_project(
    data: DesignProjectCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        return service.create_design_project(db, current_user, data)
    except service.TemplateNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    except service.PremiumRequiredError as exc:
        raise HTTPException(status_code=status.HTTP_402_PAYMENT_REQUIRED, detail=str(exc))


@router.get("/design-projects", response_model=list[DesignProjectOut])
def list_design_projects(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return service.list_design_projects(db, current_user.id)


@router.get("/design-projects/{project_id}", response_model=DesignProjectOut)
def get_design_project(
    project_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        return service.get_design_project(db, project_id, current_user.id)
    except service.ProjectNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))


@router.patch("/design-projects/{project_id}", response_model=DesignProjectOut)
def update_design_project(
    project_id: str,
    data: DesignProjectUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        return service.update_design_project(db, project_id, current_user.id, data)
    except service.ProjectNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))


@router.delete("/design-projects/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_design_project(
    project_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        service.delete_design_project(db, project_id, current_user.id)
    except service.ProjectNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))


# --- Filtres (catalogue vidéo façon CapCut) ---

@router.post(
    "/filters",
    response_model=FilterOut,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(rate_limit(max_requests=10, window_seconds=60))],
)
def create_filter(
    name: str,
    category: str,
    is_premium: bool = False,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return service.create_filter(db, name, category, is_premium)


@router.get("/filters", response_model=list[FilterOut])
def list_filters(category: str | None = Query(None), db: Session = Depends(get_db)):
    return service.list_filters(db, category=category)


# --- Projets vidéo ---

@router.post(
    "/video-projects",
    response_model=VideoProjectOut,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(rate_limit(max_requests=20, window_seconds=60))],
)
def create_video_project(
    data: VideoProjectCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        return service.create_video_project(db, current_user, data)
    except service.PremiumRequiredError as exc:
        raise HTTPException(status_code=status.HTTP_402_PAYMENT_REQUIRED, detail=str(exc))
    except service.FilterNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))


@router.get("/video-projects", response_model=list[VideoProjectOut])
def list_video_projects(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return service.list_video_projects(db, current_user.id)


@router.get("/video-projects/{project_id}", response_model=VideoProjectOut)
def get_video_project(
    project_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        return service.get_video_project(db, project_id, current_user.id)
    except service.ProjectNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))


@router.patch("/video-projects/{project_id}", response_model=VideoProjectOut)
def update_video_project(
    project_id: str,
    data: VideoProjectUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        return service.update_video_project(db, project_id, current_user.id, current_user, data)
    except service.ProjectNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    except service.PremiumRequiredError as exc:
        raise HTTPException(status_code=status.HTTP_402_PAYMENT_REQUIRED, detail=str(exc))
    except service.FilterNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))


@router.delete("/video-projects/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_video_project(
    project_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        service.delete_video_project(db, project_id, current_user.id)
    except service.ProjectNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))


# --- Fichiers médias (images/vidéos importées pour le montage) ---

@router.post(
    "/media",
    response_model=MediaAssetOut,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(rate_limit(max_requests=20, window_seconds=60))],
)
def upload_media(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Importer une image ou une vidéo source pour l'utiliser dans un montage."""
    try:
        return service.save_media_upload(
            db, current_user, file, _settings.media_storage_path, _settings.media_max_upload_mb
        )
    except UnsupportedMediaTypeError as exc:
        raise HTTPException(status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE, detail=str(exc))
    except MediaTooLargeError as exc:
        raise HTTPException(status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail=str(exc))


@router.get("/media", response_model=list[MediaAssetOut])
def list_media(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return service.list_media_assets(db, current_user.id)


@router.delete("/media/{asset_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_media(
    asset_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        service.delete_media_asset(db, asset_id, current_user.id)
    except service.ProjectNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))


# --- Rendu réel du montage (FFmpeg, gratuit, tourne sur votre serveur) ---

@router.post(
    "/video-projects/{project_id}/render",
    response_model=VideoProjectOut,
    dependencies=[Depends(rate_limit(max_requests=10, window_seconds=60))],
)
def render_video_project(
    project_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    render_provider=Depends(get_render_provider),
):
    """
    Lance le montage réel (assemblage des clips, filtres façon CapCut/
    InShot, incrustations de texte) et produit un vrai fichier vidéo,
    téléchargeable ensuite via GET /video-projects/{id}/download.
    Traitement synchrone : la requête répond une fois le rendu terminé
    (ou échoué) — pour une timeline longue, cela peut prendre du temps ;
    voir chapitre 12 du manuel pour la recommandation de passer par une
    tâche d'arrière-plan si vos vidéos ou votre volume d'utilisateurs
    grandissent.
    """
    try:
        return service.render_video_project(
            db, project_id, current_user.id, render_provider, _settings.media_storage_path
        )
    except service.ProjectNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))


@router.get("/video-projects/{project_id}/download")
def download_video_project(
    project_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Télécharge le fichier vidéo rendu — arrive directement dans les téléchargements du navigateur."""
    try:
        project = service.get_video_project(db, project_id, current_user.id)
    except service.ProjectNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))

    if project.render_status != "pret" or not project.rendered_file_path:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Cette vidéo n'est pas encore prête. Lancez d'abord son rendu.",
        )

    safe_filename = "".join(c for c in project.title if c.isalnum() or c in " -_").strip() or "nexus-video"
    return FileResponse(
        project.rendered_file_path,
        media_type="video/mp4",
        filename=f"{safe_filename}.mp4",
    )


# --- Génération vidéo par IA (façon Veo3 — 2D, 3D, ultra-réaliste) ---

@router.post(
    "/ai-video-jobs",
    response_model=AiVideoGenerationJobOut,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(rate_limit(max_requests=5, window_seconds=60))],
)
def create_ai_video_job(
    data: AiVideoGenerationRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    provider=Depends(get_ai_video_provider),
):
    """
    Soumet un prompt pour générer une vidéo par IA (2D, 3D, ultra-réaliste,
    animation, cinématique). Fonctionnalité premium. Voir la docstring de
    `ai_video_provider.py` : sans fournisseur réel branché en production
    (Veo, Runway, Pika...), le job reste en attente plutôt que de
    simuler un faux résultat.
    """
    try:
        return service.create_ai_video_job(db, current_user, data, provider)
    except service.PremiumRequiredError as exc:
        raise HTTPException(status_code=status.HTTP_402_PAYMENT_REQUIRED, detail=str(exc))


@router.get("/ai-video-jobs", response_model=list[AiVideoGenerationJobOut])
def list_ai_video_jobs(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return service.list_ai_video_jobs(db, current_user.id)


@router.get("/ai-video-jobs/{job_id}", response_model=AiVideoGenerationJobOut)
def get_ai_video_job(
    job_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        return service.get_ai_video_job(db, job_id, current_user.id)
    except service.ProjectNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
