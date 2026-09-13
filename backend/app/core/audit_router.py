"""
Routes HTTP du journal d'activité. Comme les notifications, brique
transversale montée directement dans `main.py`.
"""
from datetime import datetime

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from pydantic import BaseModel, ConfigDict

from app.core.database import get_db
from app.core import audit as service
from app.modules.auth.router import get_current_user, require_superuser
from app.modules.auth.models import User

router = APIRouter(prefix="/activity-log", tags=["Journal d'activité"])


class AuditLogEntryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    user_id: str | None
    action: str
    module: str
    resource_type: str | None
    resource_id: str | None
    description: str
    created_at: datetime


@router.get("/mine", response_model=list[AuditLogEntryOut])
def get_my_activity(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return service.list_my_activity(db, current_user.id)


@router.get("/all", response_model=list[AuditLogEntryOut])
def get_all_activity(
    admin: User = Depends(require_superuser),
    db: Session = Depends(get_db),
):
    """Vue d'ensemble de toute l'activité de la plateforme — réservée aux administrateurs."""
    return service.list_all_activity(db)
