"""
Routes HTTP des notifications. Cross-module par nature : ce n'est pas
rattaché à un module métier particulier, donc le routeur vit dans
`app.core` et est monté directement dans `main.py`, exactement comme
les autres briques transversales.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core import notifications as service
from app.modules.auth.router import get_current_user
from app.modules.auth.models import User
from pydantic import BaseModel, ConfigDict
from datetime import datetime

router = APIRouter(prefix="/notifications", tags=["Notifications"])


class NotificationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    category: str
    module: str | None
    title: str
    message: str
    link: str | None
    is_read: bool
    created_at: datetime


@router.get("", response_model=list[NotificationOut])
def list_my_notifications(
    unread_only: bool = False,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return service.list_notifications(db, current_user.id, unread_only=unread_only)


@router.get("/unread-count")
def get_unread_count(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return {"unread_count": service.unread_count(db, current_user.id)}


@router.post("/{notification_id}/read", response_model=NotificationOut)
def mark_notification_read(
    notification_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        return service.mark_read(db, notification_id, current_user.id)
    except service.NotificationNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))


@router.post("/read-all")
def mark_all_notifications_read(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    updated = service.mark_all_read(db, current_user.id)
    return {"updated": updated}
