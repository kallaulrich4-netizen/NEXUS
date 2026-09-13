from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.rate_limit import rate_limit
from app.modules.auth.router import get_current_user
from app.modules.auth.models import User
from app.modules.legal import service
from app.modules.legal.schemas import (
    LegalResourceCreate, LegalResourceOut, LegalResourceListOut,
    ConsultationRequestCreate, ConsultationRequestOut, ConsultationStatusUpdate,
)

router = APIRouter(prefix="/legal", tags=["Droit"])


# --- Ressources juridiques ---

@router.post(
    "/resources",
    response_model=LegalResourceOut,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(rate_limit(max_requests=10, window_seconds=60))],
)
def submit_resource(
    data: LegalResourceCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Soumet un contenu juridique. Reste invisible du public tant qu'il n'a
    pas été revu et publié (voir README, section Droit, pour le processus
    de validation attendu avant mise en production).
    """
    return service.submit_resource(db, current_user.id, data)


@router.get("/resources/search", response_model=list[LegalResourceListOut])
def search_resources(
    category: str | None = Query(None),
    country: str | None = Query(None),
    q: str | None = Query(None),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
):
    return service.search_published_resources(
        db, category=category, country=country, query_text=q, limit=limit, offset=offset
    )


@router.get("/resources/mine", response_model=list[LegalResourceOut])
def list_my_resources(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return service.list_my_resources(db, current_user.id)


@router.get("/resources/{resource_id}", response_model=LegalResourceOut)
def get_resource(resource_id: str, db: Session = Depends(get_db)):
    try:
        return service.get_published_resource(db, resource_id)
    except service.ResourceNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))


# --- Mises en relation avec un avocat ---

@router.post(
    "/consultations",
    response_model=ConsultationRequestOut,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(rate_limit(max_requests=10, window_seconds=60))],
)
def create_consultation_request(
    data: ConsultationRequestCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        return service.create_consultation_request(db, current_user.id, data)
    except service.LawyerListingNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))


@router.get("/consultations/mine", response_model=list[ConsultationRequestOut])
def list_my_consultations(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return service.list_my_consultation_requests(db, current_user.id)


@router.get("/consultations/incoming", response_model=list[ConsultationRequestOut])
def list_incoming_consultations(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Demandes reçues en tant qu'avocat référencé dans le module Cartographie."""
    return service.list_incoming_consultation_requests(db, current_user.id)


@router.get("/consultations/{request_id}", response_model=ConsultationRequestOut)
def get_consultation(
    request_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        return service.get_consultation_request(db, request_id, current_user.id)
    except service.ConsultationNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    except service.NotConsultationPartyError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc))


@router.patch("/consultations/{request_id}/status", response_model=ConsultationRequestOut)
def update_consultation_status(
    request_id: str,
    data: ConsultationStatusUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        return service.update_consultation_status(db, request_id, current_user.id, data.status)
    except service.ConsultationNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    except service.NotConsultationPartyError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc))
    except service.InvalidConsultationTransitionError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
