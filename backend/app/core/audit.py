"""
Service de journalisation, réutilisable par tous les modules de Nexus.

Usage typique :
    from app.core.audit import log_action
    log_action(db, user_id=user.id, action="creation", module="agriculture",
               description="Création de la parcelle 'Parcelle Nord'.",
               resource_type="agri_field", resource_id=field.id)
"""
from sqlalchemy.orm import Session

from app.core.audit_models import AuditLogEntry


def log_action(
    db: Session,
    user_id: str | None,
    action: str,
    module: str,
    description: str,
    resource_type: str | None = None,
    resource_id: str | None = None,
) -> AuditLogEntry:
    entry = AuditLogEntry(
        user_id=user_id, action=action, module=module, description=description,
        resource_type=resource_type, resource_id=resource_id,
    )
    db.add(entry)
    db.commit()
    db.refresh(entry)
    return entry


def list_my_activity(db: Session, user_id: str, limit: int = 100) -> list[AuditLogEntry]:
    return (
        db.query(AuditLogEntry)
        .filter(AuditLogEntry.user_id == user_id)
        .order_by(AuditLogEntry.created_at.desc())
        .limit(limit)
        .all()
    )


def list_all_activity(db: Session, limit: int = 200) -> list[AuditLogEntry]:
    """Réservé aux administrateurs — voir la dépendance `require_superuser` du module auth."""
    return db.query(AuditLogEntry).order_by(AuditLogEntry.created_at.desc()).limit(limit).all()
