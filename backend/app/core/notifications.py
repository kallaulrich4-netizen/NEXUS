"""
Service de notifications, réutilisable par tous les modules de Nexus.

Usage typique depuis n'importe quel module :
    from app.core.notifications import notify
    notify(db, user_id=user.id, category="confirmation", module="paiement",
           title="Paiement confirmé", message="Votre abonnement est actif.",
           link="/payments")

Ce service ne fait QUE créer/lire des notifications : il ne décide jamais
lui-même quand notifier (cette décision reste dans chaque module, au plus
près de sa propre logique métier).
"""
from sqlalchemy.orm import Session

from app.core.notification_models import Notification


class NotificationNotFoundError(Exception):
    """Levée quand une notification n'existe pas ou n'appartient pas à l'utilisateur."""


def notify(
    db: Session,
    user_id: str,
    title: str,
    message: str,
    category: str = "info",
    module: str | None = None,
    link: str | None = None,
) -> Notification:
    notification = Notification(
        user_id=user_id, category=category, module=module, title=title, message=message, link=link,
    )
    db.add(notification)
    db.commit()
    db.refresh(notification)
    return notification


def list_notifications(db: Session, user_id: str, unread_only: bool = False, limit: int = 50) -> list[Notification]:
    query = db.query(Notification).filter(Notification.user_id == user_id)
    if unread_only:
        query = query.filter(Notification.is_read.is_(False))
    return query.order_by(Notification.created_at.desc()).limit(limit).all()


def unread_count(db: Session, user_id: str) -> int:
    return (
        db.query(Notification)
        .filter(Notification.user_id == user_id, Notification.is_read.is_(False))
        .count()
    )


def mark_read(db: Session, notification_id: str, user_id: str) -> Notification:
    notification = (
        db.query(Notification)
        .filter(Notification.id == notification_id, Notification.user_id == user_id)
        .first()
    )
    if notification is None:
        raise NotificationNotFoundError("Notification introuvable.")
    notification.is_read = True
    db.commit()
    db.refresh(notification)
    return notification


def mark_all_read(db: Session, user_id: str) -> int:
    updated = (
        db.query(Notification)
        .filter(Notification.user_id == user_id, Notification.is_read.is_(False))
        .update({"is_read": True})
    )
    db.commit()
    return updated
