from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.rate_limit import rate_limit
from app.core import notifications, audit
from app.core.exports import export_document
from app.modules.auth.router import get_current_user
from app.modules.auth.models import User
from app.modules.livestock import service
from app.modules.livestock.models import SUGGESTED_SPECIES
from app.modules.livestock.schemas import (
    HerdCreate, HerdUpdate, HerdOut,
    HealthEventCreate, HealthEventOut,
    ProductionRecordCreate, ProductionRecordOut,
    HerdSummary,
    AnimalCreate, AnimalUpdate, AnimalOut,
    AnimalHealthRecordCreate, AnimalHealthRecordOut,
    WeightRecordCreate, GrowthSummary,
    ReproductionRecordCreate, ReproductionRecordOut, BirthDeclaration,
    FeedPlanRequest, FeedPlanOut,
    HerdEconomics,
)

router = APIRouter(prefix="/livestock", tags=["Élevage"])


@router.get("/species/suggestions", response_model=list[str])
def get_species_suggestions():
    """
    Liste de suggestions pour guider l'interface (auto-complétion).
    N'importe quelle autre espèce reste acceptée à la création d'un troupeau.
    """
    return SUGGESTED_SPECIES


@router.post(
    "/herds",
    response_model=HerdOut,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(rate_limit(max_requests=20, window_seconds=60))],
)
def create_herd(
    data: HerdCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    herd = service.create_herd(db, current_user.id, data)
    audit.log_action(
        db, user_id=current_user.id, action="creation", module="elevage",
        description=f"Création du troupeau « {herd.name} ».",
        resource_type="livestock_herd", resource_id=herd.id,
    )
    return herd


@router.get("/herds", response_model=list[HerdOut])
def list_herds(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return service.list_herds(db, current_user.id)


@router.get("/herds/{herd_id}", response_model=HerdOut)
def get_herd(
    herd_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        return service.get_herd(db, herd_id, current_user.id)
    except service.HerdNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))


@router.patch("/herds/{herd_id}", response_model=HerdOut)
def update_herd(
    herd_id: str,
    data: HerdUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        return service.update_herd(db, herd_id, current_user.id, data)
    except service.HerdNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))


@router.delete("/herds/{herd_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_herd(
    herd_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        service.delete_herd(db, herd_id, current_user.id)
    except service.HerdNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))


@router.get("/herds/{herd_id}/summary", response_model=HerdSummary)
def get_herd_summary(
    herd_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        return service.get_herd_summary(db, herd_id, current_user.id)
    except service.HerdNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))


@router.post(
    "/herds/{herd_id}/health-events",
    response_model=HealthEventOut,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(rate_limit(max_requests=30, window_seconds=60))],
)
def add_health_event(
    herd_id: str,
    data: HealthEventCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        return service.add_health_event(db, herd_id, current_user.id, data)
    except service.HerdNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))


@router.get("/herds/{herd_id}/health-events", response_model=list[HealthEventOut])
def list_health_events(
    herd_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        return service.list_health_events(db, herd_id, current_user.id)
    except service.HerdNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))


@router.post(
    "/herds/{herd_id}/production-records",
    response_model=ProductionRecordOut,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(rate_limit(max_requests=30, window_seconds=60))],
)
def add_production_record(
    herd_id: str,
    data: ProductionRecordCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        return service.add_production_record(db, herd_id, current_user.id, data)
    except service.HerdNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))


@router.get("/herds/{herd_id}/production-records", response_model=list[ProductionRecordOut])
def list_production_records(
    herd_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        return service.list_production_records(db, herd_id, current_user.id)
    except service.HerdNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))


# --- Élevage V2 : fiche individuelle ---

@router.post(
    "/herds/{herd_id}/animals",
    response_model=AnimalOut,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(rate_limit(max_requests=30, window_seconds=60))],
)
def create_animal(
    herd_id: str,
    data: AnimalCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        return service.create_animal(db, herd_id, current_user.id, data)
    except service.HerdNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    except service.AnimalNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))


@router.get("/herds/{herd_id}/animals", response_model=list[AnimalOut])
def list_animals(
    herd_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        return service.list_animals(db, herd_id, current_user.id)
    except service.HerdNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))


@router.get("/animals/{animal_id}", response_model=AnimalOut)
def get_animal(
    animal_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        return service.get_animal(db, animal_id, current_user.id)
    except service.AnimalNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))


@router.patch("/animals/{animal_id}", response_model=AnimalOut)
def update_animal(
    animal_id: str,
    data: AnimalUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        return service.update_animal(db, animal_id, current_user.id, data)
    except service.AnimalNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))


@router.post(
    "/animals/{animal_id}/health-records",
    response_model=AnimalHealthRecordOut,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(rate_limit(max_requests=30, window_seconds=60))],
)
def add_animal_health_record(
    animal_id: str,
    data: AnimalHealthRecordCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        return service.add_animal_health_record(db, animal_id, current_user.id, data)
    except service.AnimalNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))


@router.get("/animals/{animal_id}/health-records", response_model=list[AnimalHealthRecordOut])
def list_animal_health_records(
    animal_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        return service.list_animal_health_records(db, animal_id, current_user.id)
    except service.AnimalNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))


@router.post(
    "/animals/{animal_id}/weight-records",
    response_model=GrowthSummary,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(rate_limit(max_requests=30, window_seconds=60))],
)
def add_weight_record(
    animal_id: str,
    data: WeightRecordCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        service.add_weight_record(db, animal_id, current_user.id, data)
        return service.get_growth_summary(db, animal_id, current_user.id)
    except service.AnimalNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))


@router.get("/animals/{animal_id}/growth-summary", response_model=GrowthSummary)
def get_growth_summary(
    animal_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        return service.get_growth_summary(db, animal_id, current_user.id)
    except service.AnimalNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))


@router.post(
    "/animals/{animal_id}/reproduction-records",
    response_model=ReproductionRecordOut,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(rate_limit(max_requests=30, window_seconds=60))],
)
def add_reproduction_record(
    animal_id: str,
    data: ReproductionRecordCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        return service.add_reproduction_record(db, animal_id, current_user.id, data)
    except service.AnimalNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))


@router.get("/animals/{animal_id}/reproduction-records", response_model=list[ReproductionRecordOut])
def list_reproduction_records(
    animal_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        return service.list_reproduction_records(db, animal_id, current_user.id)
    except service.AnimalNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))


@router.post(
    "/animals/{animal_id}/declare-birth",
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(rate_limit(max_requests=20, window_seconds=60))],
)
def declare_birth(
    animal_id: str,
    data: BirthDeclaration,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        result = service.declare_birth(db, animal_id, current_user.id, data)
    except service.AnimalNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))

    notifications.notify(
        db, user_id=current_user.id, category="confirmation", module="elevage",
        title="Naissance enregistrée", link="/livestock",
        message=f"{data.offspring_count} nouvelle(s) fiche(s) animal ont été créées suite à la mise bas.",
    )
    return {
        "reproduction_record": ReproductionRecordOut.model_validate(result["reproduction_record"]),
        "offspring": [AnimalOut.model_validate(a) for a in result["offspring"]],
    }


# --- Élevage V2 : plan alimentaire ---

@router.post(
    "/herds/{herd_id}/feed-plan",
    response_model=FeedPlanOut,
    status_code=status.HTTP_201_CREATED,
)
def generate_feed_plan(
    herd_id: str,
    data: FeedPlanRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        return service.generate_feed_plan(db, herd_id, current_user.id, data)
    except service.HerdNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))


@router.get("/herds/{herd_id}/feed-plan", response_model=FeedPlanOut | None)
def get_feed_plan(
    herd_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        return service.get_latest_feed_plan(db, herd_id, current_user.id)
    except service.HerdNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))


# --- Élevage V2 : analyse économique ---

@router.get("/herds/{herd_id}/economics", response_model=HerdEconomics)
def get_herd_economics(
    herd_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        return service.get_herd_economics(db, herd_id, current_user.id)
    except service.HerdNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))


@router.get("/animals/{animal_id}/report")
def get_animal_report(
    animal_id: str,
    file_format: str = "pdf",
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Génère la fiche/carnet de suivi de l'animal (identité, carnet
    sanitaire, croissance, reproduction), dans le format demandé (pdf,
    docx, xlsx, csv) — réutilise le service partagé `app.core.exports`.
    """
    try:
        document = service.build_animal_report(db, animal_id, current_user.id)
    except service.AnimalNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))

    try:
        content, mime_type, extension = export_document(document, file_format)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))

    return Response(
        content=content,
        media_type=mime_type,
        headers={"Content-Disposition": f"attachment; filename=fiche-animal-{animal_id}.{extension}"},
    )
