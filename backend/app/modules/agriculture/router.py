from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.rate_limit import rate_limit
from app.core import notifications, audit
from app.core.exports import export_document
from app.modules.auth.router import get_current_user
from app.modules.auth.models import User
from app.modules.agriculture import service
from app.modules.agriculture.schemas import (
    FieldCreate, FieldUpdate, FieldOut,
    CropCycleCreate, CropCycleHarvest, CropCycleOut,
    ActivityCreate, ActivityOut,
    FieldYieldSummary,
    CropRecommendationRequest, CropRecommendationOut,
    CalendarTaskOut, CalendarTaskUpdate,
    DiseaseDiagnosisRequest, DiseaseDiagnosisOut,
    FinancialProjectionRequest, FinancialProjectionOut,
    FarmDashboard,
)
from app.modules.ai_assistant.provider import AIProvider, get_ai_provider

router = APIRouter(prefix="/agriculture", tags=["Agriculture"])


# --- Parcelles ---

@router.post(
    "/fields",
    response_model=FieldOut,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(rate_limit(max_requests=20, window_seconds=60))],
)
def create_field(
    data: FieldCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    field = service.create_field(db, current_user.id, data)
    audit.log_action(
        db, user_id=current_user.id, action="creation", module="agriculture",
        description=f"Création de la parcelle « {field.name} ».",
        resource_type="agri_field", resource_id=field.id,
    )
    return field


@router.get("/fields", response_model=list[FieldOut])
def list_fields(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return service.list_fields(db, current_user.id)


@router.get("/fields/{field_id}", response_model=FieldOut)
def get_field(
    field_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        return service.get_field(db, field_id, current_user.id)
    except service.FieldNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))


@router.patch("/fields/{field_id}", response_model=FieldOut)
def update_field(
    field_id: str,
    data: FieldUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        return service.update_field(db, field_id, current_user.id, data)
    except service.FieldNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))


@router.delete("/fields/{field_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_field(
    field_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        service.delete_field(db, field_id, current_user.id)
    except service.FieldNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))


@router.get("/fields/{field_id}/yield-summary", response_model=FieldYieldSummary)
def get_yield_summary(
    field_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        return service.get_field_yield_summary(db, field_id, current_user.id)
    except service.FieldNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))


# --- Cycles de culture ---

@router.post(
    "/fields/{field_id}/crop-cycles",
    response_model=CropCycleOut,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(rate_limit(max_requests=20, window_seconds=60))],
)
def create_crop_cycle(
    field_id: str,
    data: CropCycleCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        return service.create_crop_cycle(db, field_id, current_user.id, data)
    except service.FieldNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))


@router.get("/fields/{field_id}/crop-cycles", response_model=list[CropCycleOut])
def list_crop_cycles(
    field_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        return service.list_crop_cycles(db, field_id, current_user.id)
    except service.FieldNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))


@router.get("/crop-cycles/{cycle_id}", response_model=CropCycleOut)
def get_crop_cycle(
    cycle_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        return service.get_crop_cycle(db, cycle_id, current_user.id)
    except service.CropCycleNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))


@router.post("/crop-cycles/{cycle_id}/start-growing", response_model=CropCycleOut)
def start_growing(
    cycle_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        return service.mark_growing(db, cycle_id, current_user.id)
    except service.CropCycleNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    except service.InvalidCycleStateError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))


@router.post("/crop-cycles/{cycle_id}/harvest", response_model=CropCycleOut)
def record_harvest(
    cycle_id: str,
    data: CropCycleHarvest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        return service.record_harvest(db, cycle_id, current_user.id, data)
    except service.CropCycleNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    except service.InvalidCycleStateError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))


@router.post("/crop-cycles/{cycle_id}/mark-failed", response_model=CropCycleOut)
def mark_failed(
    cycle_id: str,
    notes: str | None = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        return service.mark_failed(db, cycle_id, current_user.id, notes)
    except service.CropCycleNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    except service.InvalidCycleStateError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))


# --- Activités ---

@router.post(
    "/crop-cycles/{cycle_id}/activities",
    response_model=ActivityOut,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(rate_limit(max_requests=30, window_seconds=60))],
)
def add_activity(
    cycle_id: str,
    data: ActivityCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        return service.add_activity(db, cycle_id, current_user.id, data)
    except service.CropCycleNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))


@router.get("/crop-cycles/{cycle_id}/activities", response_model=list[ActivityOut])
def list_activities(
    cycle_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        return service.list_activities(db, cycle_id, current_user.id)
    except service.CropCycleNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))


# --- Agriculture V2 : recommandations de culture ---

@router.post(
    "/fields/{field_id}/recommendations",
    response_model=list[CropRecommendationOut],
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(rate_limit(max_requests=10, window_seconds=60))],
)
def create_crop_recommendations(
    field_id: str,
    data: CropRecommendationRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    provider: AIProvider = Depends(get_ai_provider),
):
    try:
        return service.generate_crop_recommendations(
            db, field_id, current_user.id, data, provider, current_user.preferred_language
        )
    except service.FieldNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))


@router.get("/fields/{field_id}/recommendations", response_model=list[CropRecommendationOut])
def list_crop_recommendations(
    field_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        return service.list_crop_recommendations(db, field_id, current_user.id)
    except service.FieldNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))


# --- Agriculture V2 : calendrier automatique ---

@router.post("/crop-cycles/{cycle_id}/calendar", response_model=list[CalendarTaskOut])
def generate_calendar(
    cycle_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        return service.generate_calendar(db, cycle_id, current_user.id)
    except service.CropCycleNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))


@router.get("/crop-cycles/{cycle_id}/calendar", response_model=list[CalendarTaskOut])
def list_calendar(
    cycle_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        return service.list_calendar_tasks(db, cycle_id, current_user.id)
    except service.CropCycleNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))


@router.patch("/calendar-tasks/{task_id}", response_model=CalendarTaskOut)
def update_calendar_task(
    task_id: str,
    data: CalendarTaskUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        return service.update_calendar_task(db, task_id, current_user.id, data)
    except service.CalendarTaskNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))


# --- Agriculture V2 : diagnostic des maladies ---

@router.post(
    "/crop-cycles/{cycle_id}/diagnose",
    response_model=DiseaseDiagnosisOut,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(rate_limit(max_requests=10, window_seconds=60))],
)
def diagnose_disease(
    cycle_id: str,
    data: DiseaseDiagnosisRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    provider: AIProvider = Depends(get_ai_provider),
):
    try:
        diagnosis = service.create_disease_diagnosis(
            db, cycle_id, current_user.id, data, provider, current_user.preferred_language
        )
    except service.CropCycleNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))

    notifications.notify(
        db, user_id=current_user.id, category="recommandation_ia", module="agriculture",
        title="Diagnostic disponible", link="/agriculture",
        message="Le diagnostic de votre cycle de culture est prêt : consultez les actions recommandées.",
    )
    return diagnosis


@router.get("/crop-cycles/{cycle_id}/diagnoses", response_model=list[DiseaseDiagnosisOut])
def list_diagnoses(
    cycle_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        return service.list_disease_diagnoses(db, cycle_id, current_user.id)
    except service.CropCycleNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))


# --- Agriculture V2 : projection économique ---

@router.post(
    "/fields/{field_id}/financial-projection",
    response_model=FinancialProjectionOut,
    status_code=status.HTTP_201_CREATED,
)
def create_financial_projection(
    field_id: str,
    data: FinancialProjectionRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        return service.generate_financial_projection(db, field_id, current_user.id, data)
    except service.FieldNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))


@router.get("/fields/{field_id}/financial-projection", response_model=FinancialProjectionOut | None)
def get_financial_projection(
    field_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        return service.get_latest_financial_projection(db, field_id, current_user.id)
    except service.FieldNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))


# --- Agriculture V2 : tableau de bord consolidé ---

@router.get("/dashboard", response_model=FarmDashboard)
def get_dashboard(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return service.get_farm_dashboard(db, current_user.id)


@router.get("/fields/{field_id}/report")
def get_field_report(
    field_id: str,
    file_format: str = "pdf",
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Génère un rapport de culture pour une parcelle, dans le format
    demandé (pdf, docx, xlsx, csv) — voir `app.core.exports` pour le
    service partagé de génération de documents.
    """
    try:
        document = service.build_field_report(db, field_id, current_user.id)
    except service.FieldNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))

    try:
        content, mime_type, extension = export_document(document, file_format)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))

    return Response(
        content=content,
        media_type=mime_type,
        headers={"Content-Disposition": f"attachment; filename=rapport-culture-{field_id}.{extension}"},
    )
