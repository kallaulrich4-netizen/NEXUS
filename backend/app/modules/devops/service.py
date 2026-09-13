from collections import defaultdict
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.modules.devops.models import CloudResource, Deployment, MonitoringAlert, BackupRecord


class ResourceNotFoundError(Exception):
    """Levée quand une ressource cloud n'existe pas ou n'appartient pas à l'utilisateur."""


class DeploymentNotFoundError(Exception):
    """Levée quand un déploiement n'existe pas ou n'appartient pas à une ressource de l'utilisateur."""


class AlertNotFoundError(Exception):
    """Levée quand une alerte n'existe pas ou n'appartient pas à une ressource de l'utilisateur."""


class InvalidDeploymentTransitionError(Exception):
    """Levée quand un changement de statut de déploiement n'est pas cohérent."""


# --- Ressources cloud ---

def create_resource(db: Session, owner_id: str, data) -> CloudResource:
    resource = CloudResource(owner_id=owner_id, status="actif", **data.model_dump())
    db.add(resource)
    db.commit()
    db.refresh(resource)
    return resource


def get_resource(db: Session, resource_id: str, owner_id: str) -> CloudResource:
    resource = (
        db.query(CloudResource)
        .filter(CloudResource.id == resource_id, CloudResource.owner_id == owner_id)
        .first()
    )
    if resource is None:
        raise ResourceNotFoundError("Ressource cloud introuvable.")
    return resource


def list_resources(db: Session, owner_id: str) -> list[CloudResource]:
    return (
        db.query(CloudResource)
        .filter(CloudResource.owner_id == owner_id)
        .order_by(CloudResource.created_at.desc())
        .all()
    )


def update_resource_status(db: Session, resource_id: str, owner_id: str, new_status: str) -> CloudResource:
    resource = get_resource(db, resource_id, owner_id)
    resource.status = new_status
    db.commit()
    db.refresh(resource)
    return resource


def delete_resource(db: Session, resource_id: str, owner_id: str) -> None:
    resource = get_resource(db, resource_id, owner_id)
    db.delete(resource)
    db.commit()


# --- Déploiements ---

def create_deployment(db: Session, resource_id: str, owner_id: str, data) -> Deployment:
    get_resource(db, resource_id, owner_id)
    deployment = Deployment(resource_id=resource_id, status="en_attente", **data.model_dump())
    db.add(deployment)
    db.commit()
    db.refresh(deployment)
    return deployment


def _get_deployment_for_owner(db: Session, deployment_id: str, owner_id: str) -> Deployment:
    deployment = (
        db.query(Deployment)
        .join(CloudResource)
        .filter(Deployment.id == deployment_id, CloudResource.owner_id == owner_id)
        .first()
    )
    if deployment is None:
        raise DeploymentNotFoundError("Déploiement introuvable.")
    return deployment


def list_deployments(db: Session, resource_id: str, owner_id: str) -> list[Deployment]:
    get_resource(db, resource_id, owner_id)
    return (
        db.query(Deployment)
        .filter(Deployment.resource_id == resource_id)
        .order_by(Deployment.started_at.desc())
        .all()
    )


_VALID_DEPLOYMENT_TRANSITIONS = {
    "en_attente": {"en_cours", "annule"},
    "en_cours": {"reussi", "echoue"},
    "reussi": {"annule_par_rollback"},
    "echoue": set(),
    "annule": set(),
    "annule_par_rollback": set(),
}


def update_deployment_status(db: Session, deployment_id: str, owner_id: str, new_status: str) -> Deployment:
    deployment = _get_deployment_for_owner(db, deployment_id, owner_id)
    if new_status not in _VALID_DEPLOYMENT_TRANSITIONS.get(deployment.status, set()):
        raise InvalidDeploymentTransitionError(
            f"Transition de statut invalide : « {deployment.status} » -> « {new_status} »."
        )
    deployment.status = new_status
    if new_status in {"reussi", "echoue", "annule", "annule_par_rollback"}:
        deployment.finished_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(deployment)
    return deployment


def create_rollback_deployment(db: Session, deployment_id: str, owner_id: str, data) -> Deployment:
    """Crée un nouveau déploiement de rollback, et marque l'ancien comme annulé par ce rollback."""
    failing_deployment = _get_deployment_for_owner(db, deployment_id, owner_id)

    rollback = Deployment(
        resource_id=failing_deployment.resource_id,
        status="en_attente",
        rollback_of_id=failing_deployment.id,
        **data.model_dump(),
    )
    db.add(rollback)

    if failing_deployment.status not in {"annule", "annule_par_rollback"}:
        failing_deployment.status = "annule_par_rollback"
        failing_deployment.finished_at = datetime.now(timezone.utc)

    db.commit()
    db.refresh(rollback)
    return rollback


# --- Alertes de supervision ---

def trigger_alert(db: Session, resource_id: str, owner_id: str, data) -> MonitoringAlert:
    get_resource(db, resource_id, owner_id)
    alert = MonitoringAlert(resource_id=resource_id, status="ouverte", **data.model_dump())
    db.add(alert)
    db.commit()
    db.refresh(alert)
    return alert


def _get_alert_for_owner(db: Session, alert_id: str, owner_id: str) -> MonitoringAlert:
    alert = (
        db.query(MonitoringAlert)
        .join(CloudResource)
        .filter(MonitoringAlert.id == alert_id, CloudResource.owner_id == owner_id)
        .first()
    )
    if alert is None:
        raise AlertNotFoundError("Alerte introuvable.")
    return alert


def list_alerts(db: Session, resource_id: str, owner_id: str) -> list[MonitoringAlert]:
    get_resource(db, resource_id, owner_id)
    return (
        db.query(MonitoringAlert)
        .filter(MonitoringAlert.resource_id == resource_id)
        .order_by(MonitoringAlert.triggered_at.desc())
        .all()
    )


def update_alert_status(db: Session, alert_id: str, owner_id: str, new_status: str) -> MonitoringAlert:
    alert = _get_alert_for_owner(db, alert_id, owner_id)
    alert.status = new_status
    if new_status == "resolue":
        alert.resolved_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(alert)
    return alert


# --- Tableau de bord infrastructure ---

def get_infrastructure_dashboard(db: Session, owner_id: str) -> dict:
    resources = db.query(CloudResource).filter(CloudResource.owner_id == owner_id).all()
    resource_ids = [r.id for r in resources]

    resources_by_status: dict[str, int] = defaultdict(int)
    for r in resources:
        resources_by_status[r.status] += 1

    open_alerts_by_severity: dict[str, int] = defaultdict(int)
    if resource_ids:
        alerts = (
            db.query(MonitoringAlert)
            .filter(MonitoringAlert.resource_id.in_(resource_ids), MonitoringAlert.status != "resolue")
            .all()
        )
        for alert in alerts:
            open_alerts_by_severity[alert.severity] += 1

    last_status_by_env: dict[str, str] = {}
    if resource_ids:
        deployments = (
            db.query(Deployment)
            .filter(Deployment.resource_id.in_(resource_ids))
            .order_by(Deployment.started_at.desc())
            .all()
        )
        for deployment in deployments:
            if deployment.environment not in last_status_by_env:
                last_status_by_env[deployment.environment] = deployment.status

    return {
        "total_resources": len(resources),
        "resources_by_status": dict(resources_by_status),
        "open_alerts_by_severity": dict(open_alerts_by_severity),
        "last_deployment_status_by_environment": last_status_by_env,
    }


# --- Sauvegardes ---

class BackupNotFoundError(Exception):
    """Levée quand une sauvegarde n'existe pas ou n'appartient pas à l'utilisateur."""


def schedule_backup(db: Session, owner_id: str, data) -> BackupRecord:
    backup = BackupRecord(owner_id=owner_id, backup_type=data.backup_type, notes=data.notes, status="planifiee")
    db.add(backup)
    db.commit()
    db.refresh(backup)
    return backup


def list_backups(db: Session, owner_id: str) -> list[BackupRecord]:
    return (
        db.query(BackupRecord)
        .filter(BackupRecord.owner_id == owner_id)
        .order_by(BackupRecord.scheduled_at.desc())
        .all()
    )


def run_backup(db: Session, backup_id: str, owner_id: str) -> BackupRecord:
    """
    Exécute (ou simule, selon l'environnement) la sauvegarde planifiée.

    Point d'extension pour la production : remplacez le bloc `# --- exécution réelle ---`
    ci-dessous par une commande réelle (ex: `pg_dump` vers un stockage
    objet), en conservant la mise à jour de `status`/`executed_at`/
    `file_reference` telle quelle pour que le reste de la plateforme
    (historique, interface) continue de fonctionner sans changement.
    """
    backup = (
        db.query(BackupRecord)
        .filter(BackupRecord.id == backup_id, BackupRecord.owner_id == owner_id)
        .first()
    )
    if backup is None:
        raise BackupNotFoundError("Sauvegarde introuvable.")

    backup.status = "en_cours"
    db.commit()

    # --- exécution réelle (à brancher en production) ---
    backup.status = "reussie"
    backup.executed_at = datetime.now(timezone.utc)
    backup.file_reference = f"backups/{backup.owner_id}/{backup.id}.dump"
    # --- fin du point d'extension ---

    db.commit()
    db.refresh(backup)
    return backup


# --- Monitoring système ---

def get_system_health(db: Session) -> dict:
    """
    Indicateurs de santé de la plateforme. Utilise `psutil` s'il est
    installé (voir requirements.txt) pour des métriques réelles ;
    dégrade proprement vers une estimation minimale sinon, plutôt que de
    faire échouer l'endpoint — un tableau de bord de monitoring ne doit
    jamais être le composant qui tombe en panne.
    """
    import time
    from sqlalchemy import text

    database_reachable = True
    try:
        db.execute(text("SELECT 1"))
    except Exception:
        database_reachable = False

    try:
        import psutil

        cpu_percent = psutil.cpu_percent(interval=0.1)
        memory_percent = psutil.virtual_memory().percent
        disk_percent = psutil.disk_usage("/").percent
        uptime_seconds = time.time() - psutil.boot_time()
        metrics_source = "psutil"
    except ImportError:
        cpu_percent = None
        memory_percent = None
        disk_percent = None
        uptime_seconds = time.process_time()
        metrics_source = "estimation"

    if not database_reachable:
        status = "indisponible"
    elif cpu_percent is not None and (cpu_percent > 90 or (memory_percent or 0) > 90):
        status = "degrade"
    else:
        status = "operationnel"

    return {
        "status": status,
        "uptime_seconds": uptime_seconds,
        "cpu_percent": cpu_percent,
        "memory_percent": memory_percent,
        "disk_percent": disk_percent,
        "database_reachable": database_reachable,
        "metrics_source": metrics_source,
    }
