from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.rate_limit import rate_limit
from app.modules.auth.router import get_current_user
from app.modules.auth.models import User
from app.modules.devops import service
from app.modules.devops.schemas import (
    CloudResourceCreate, CloudResourceOut, CloudResourceStatusUpdate,
    DeploymentCreate, DeploymentOut, DeploymentStatusUpdate,
    MonitoringAlertCreate, MonitoringAlertOut, MonitoringAlertStatusUpdate,
    InfrastructureDashboard,
    BackupCreate, BackupOut, SystemHealth,
)

router = APIRouter(prefix="/devops", tags=["DevOps/Cloud"])


@router.post(
    "/resources",
    response_model=CloudResourceOut,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(rate_limit(max_requests=20, window_seconds=60))],
)
def create_resource(
    data: CloudResourceCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return service.create_resource(db, current_user.id, data)


@router.get("/resources", response_model=list[CloudResourceOut])
def list_resources(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return service.list_resources(db, current_user.id)


@router.get("/resources/{resource_id}", response_model=CloudResourceOut)
def get_resource(
    resource_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        return service.get_resource(db, resource_id, current_user.id)
    except service.ResourceNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))


@router.patch("/resources/{resource_id}/status", response_model=CloudResourceOut)
def update_resource_status(
    resource_id: str,
    data: CloudResourceStatusUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        return service.update_resource_status(db, resource_id, current_user.id, data.status)
    except service.ResourceNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))


@router.delete("/resources/{resource_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_resource(
    resource_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        service.delete_resource(db, resource_id, current_user.id)
    except service.ResourceNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))


@router.get("/dashboard", response_model=InfrastructureDashboard)
def get_infrastructure_dashboard(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return service.get_infrastructure_dashboard(db, current_user.id)


@router.post(
    "/resources/{resource_id}/deployments",
    response_model=DeploymentOut,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(rate_limit(max_requests=30, window_seconds=60))],
)
def create_deployment(
    resource_id: str,
    data: DeploymentCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        return service.create_deployment(db, resource_id, current_user.id, data)
    except service.ResourceNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))


@router.get("/resources/{resource_id}/deployments", response_model=list[DeploymentOut])
def list_deployments(
    resource_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        return service.list_deployments(db, resource_id, current_user.id)
    except service.ResourceNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))


@router.patch("/deployments/{deployment_id}/status", response_model=DeploymentOut)
def update_deployment_status(
    deployment_id: str,
    data: DeploymentStatusUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        return service.update_deployment_status(db, deployment_id, current_user.id, data.status)
    except service.DeploymentNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    except service.InvalidDeploymentTransitionError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))


@router.post(
    "/deployments/{deployment_id}/rollback",
    response_model=DeploymentOut,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(rate_limit(max_requests=20, window_seconds=60))],
)
def rollback_deployment(
    deployment_id: str,
    data: DeploymentCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Crée un déploiement de rollback ; marque automatiquement l'ancien comme annulé."""
    try:
        return service.create_rollback_deployment(db, deployment_id, current_user.id, data)
    except service.DeploymentNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))


@router.post(
    "/resources/{resource_id}/alerts",
    response_model=MonitoringAlertOut,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(rate_limit(max_requests=60, window_seconds=60))],
)
def trigger_alert(
    resource_id: str,
    data: MonitoringAlertCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        return service.trigger_alert(db, resource_id, current_user.id, data)
    except service.ResourceNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))


@router.get("/resources/{resource_id}/alerts", response_model=list[MonitoringAlertOut])
def list_alerts(
    resource_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        return service.list_alerts(db, resource_id, current_user.id)
    except service.ResourceNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))


@router.patch("/alerts/{alert_id}/status", response_model=MonitoringAlertOut)
def update_alert_status(
    alert_id: str,
    data: MonitoringAlertStatusUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        return service.update_alert_status(db, alert_id, current_user.id, data.status)
    except service.AlertNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))


# --- Sauvegardes ---

@router.post(
    "/backups",
    response_model=BackupOut,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(rate_limit(max_requests=10, window_seconds=60))],
)
def schedule_backup(
    data: BackupCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return service.schedule_backup(db, current_user.id, data)


@router.get("/backups", response_model=list[BackupOut])
def list_backups(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return service.list_backups(db, current_user.id)


@router.post("/backups/{backup_id}/run", response_model=BackupOut)
def run_backup(
    backup_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        return service.run_backup(db, backup_id, current_user.id)
    except service.BackupNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))


# --- Monitoring système ---

@router.get("/system-health", response_model=SystemHealth)
def get_system_health(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Accessible à tout utilisateur authentifié : ne révèle aucune donnée sensible, utile pour un indicateur de statut global."""
    return service.get_system_health(db)
