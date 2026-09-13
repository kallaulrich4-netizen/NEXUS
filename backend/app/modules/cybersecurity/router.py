from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.rate_limit import rate_limit
from app.modules.auth.router import get_current_user
from app.modules.auth.models import User
from app.modules.cybersecurity import service
from app.modules.cybersecurity.schemas import (
    SecurityAssetCreate, SecurityAssetOut,
    SecurityAuditCreate, SecurityAuditOut, SecurityAuditStatusUpdate,
    FindingCreate, FindingOut, FindingStatusUpdate,
    SecurityGuideCreate, SecurityGuideOut, SecurityGuideListOut,
    RiskDashboard,
)

router = APIRouter(prefix="/cybersecurity", tags=["Cybersécurité"])


# --- Actifs ---

@router.post(
    "/assets",
    response_model=SecurityAssetOut,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(rate_limit(max_requests=20, window_seconds=60))],
)
def create_asset(
    data: SecurityAssetCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return service.create_asset(db, current_user.id, data)


@router.get("/assets", response_model=list[SecurityAssetOut])
def list_assets(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return service.list_assets(db, current_user.id)


@router.delete("/assets/{asset_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_asset(
    asset_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        service.delete_asset(db, asset_id, current_user.id)
    except service.AssetNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))


@router.get("/assets/{asset_id}/risk-dashboard", response_model=RiskDashboard)
def get_risk_dashboard(
    asset_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        return service.get_risk_dashboard(db, asset_id, current_user.id)
    except service.AssetNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))


# --- Audits ---

@router.post(
    "/assets/{asset_id}/audits",
    response_model=SecurityAuditOut,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(rate_limit(max_requests=10, window_seconds=60))],
)
def request_audit(
    asset_id: str,
    data: SecurityAuditCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """La confirmation de propriété (`ownership_confirmed`) est obligatoire pour toute demande d'audit."""
    try:
        return service.request_audit(db, asset_id, current_user.id, data)
    except service.AssetNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))


@router.get("/assets/{asset_id}/audits", response_model=list[SecurityAuditOut])
def list_audits(
    asset_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        return service.list_audits(db, asset_id, current_user.id)
    except service.AssetNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))


@router.get("/audits/{audit_id}", response_model=SecurityAuditOut)
def get_audit(
    audit_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        return service.get_audit(db, audit_id, current_user.id)
    except service.AuditNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))


@router.patch("/audits/{audit_id}/status", response_model=SecurityAuditOut)
def update_audit_status(
    audit_id: str,
    data: SecurityAuditStatusUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        return service.update_audit_status(db, audit_id, current_user.id, data.status, data.summary)
    except service.AuditNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))


# --- Constats de vulnérabilité ---

@router.post(
    "/audits/{audit_id}/findings",
    response_model=FindingOut,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(rate_limit(max_requests=30, window_seconds=60))],
)
def add_finding(
    audit_id: str,
    data: FindingCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        return service.add_finding(db, audit_id, current_user.id, data)
    except service.AuditNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))


@router.get("/audits/{audit_id}/findings", response_model=list[FindingOut])
def list_findings(
    audit_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        return service.list_findings(db, audit_id, current_user.id)
    except service.AuditNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))


@router.patch("/findings/{finding_id}/status", response_model=FindingOut)
def update_finding_status(
    finding_id: str,
    data: FindingStatusUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        return service.update_finding_status(db, finding_id, current_user.id, data.status)
    except service.FindingNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))


# --- Guides de sécurisation ---

@router.post(
    "/guides",
    response_model=SecurityGuideOut,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(rate_limit(max_requests=10, window_seconds=60))],
)
def submit_guide(
    data: SecurityGuideCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return service.submit_guide(db, current_user.id, data)


@router.get("/guides/search", response_model=list[SecurityGuideListOut])
def search_guides(
    category: str | None = Query(None),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
):
    return service.search_published_guides(db, category=category, limit=limit, offset=offset)


@router.get("/guides/{guide_id}", response_model=SecurityGuideOut)
def get_guide(guide_id: str, db: Session = Depends(get_db)):
    try:
        return service.get_published_guide(db, guide_id)
    except service.GuideNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
