from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.rate_limit import rate_limit
from app.core import notifications, audit
from app.modules.auth.router import get_current_user, require_superuser
from app.modules.auth.models import User
from app.modules.payments import service
from app.modules.payments.provider import get_payment_provider
from app.modules.payments.schemas import (
    PlanCreate, PlanOut,
    SubscribeRequest, SubscribeResponse,
    SubscriptionOut, PaymentOut,
    WebhookPayload,
)

router = APIRouter(prefix="/payments", tags=["Paiement"])


# --- Plans ---

@router.post(
    "/plans",
    response_model=PlanOut,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(rate_limit(max_requests=10, window_seconds=60))],
)
def create_plan(
    data: PlanCreate,
    current_user: User = Depends(require_superuser),
    db: Session = Depends(get_db),
):
    """
    Création de plan tarifaire, réservée au super-administrateur (corrigé
    lors de l'audit de juillet 2026 : cette route était ouverte à tout
    utilisateur authentifié, ce qui aurait permis à n'importe quel compte
    de créer des plans tarifaires arbitraires).
    """
    return service.create_plan(db, data)


@router.get("/plans", response_model=list[PlanOut])
def list_plans(db: Session = Depends(get_db)):
    return service.list_active_plans(db)


# --- Abonnement ---

@router.post(
    "/subscribe",
    response_model=SubscribeResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(rate_limit(max_requests=10, window_seconds=60))],
)
def subscribe(
    data: SubscribeRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Déclenche un abonnement. Aucun accès premium n'est accordé
    immédiatement : le statut reste "en_attente_paiement" jusqu'à la
    confirmation réelle du fournisseur (voir /payments/webhook).
    """
    try:
        provider = get_payment_provider(data.payment_method)
        subscription, payment = service.subscribe(db, current_user.id, data, provider)
        audit.log_action(
            db, user_id=current_user.id, action="creation", module="paiement",
            description=f"Tentative d'abonnement via {data.payment_method}.",
            resource_type="subscription", resource_id=subscription.id,
        )
        return {"subscription": subscription, "payment": payment}
    except service.PlanNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))


@router.get("/subscriptions/mine", response_model=list[SubscriptionOut])
def list_my_subscriptions(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return service.list_my_subscriptions(db, current_user.id)


@router.get("/subscriptions/mine/active", response_model=SubscriptionOut | None)
def get_my_active_subscription(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Abonnement actif de l'utilisateur connecté, ou null s'il n'en a aucun — utilisé par la page Paiement."""
    return service.get_active_subscription(db, current_user.id)


@router.get("/payments/mine", response_model=list[PaymentOut])
def list_my_payments(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Historique complet des transactions de l'utilisateur connecté — utilisé par la page Paiement."""
    return service.list_my_payments(db, current_user.id)


@router.get("/subscriptions/{subscription_id}", response_model=SubscriptionOut)
def get_subscription(
    subscription_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        return service.get_subscription(db, subscription_id, current_user.id)
    except service.SubscriptionNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))


@router.post("/subscriptions/{subscription_id}/cancel", response_model=SubscriptionOut)
def cancel_subscription(
    subscription_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        return service.cancel_subscription(db, subscription_id, current_user.id)
    except service.SubscriptionNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))


# --- Webhook de confirmation (appelé par le fournisseur réel, pas par l'utilisateur) ---

@router.post(
    "/webhook",
    response_model=PaymentOut,
    dependencies=[Depends(rate_limit(max_requests=120, window_seconds=60))],
)
def payment_webhook(payload: WebhookPayload, db: Session = Depends(get_db)):
    """
    Point d'entrée du webhook de confirmation. En production, sécurisez
    impérativement cette route (vérification de signature propre à
    chaque fournisseur — MTN, Orange et les processeurs carte fournissent
    tous un mécanisme de signature de webhook) avant de faire confiance
    à son contenu : n'importe qui peut sinon prétendre avoir payé.
    """
    try:
        payment = service.confirm_payment(db, payload)
    except service.PaymentNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    except service.PaymentAlreadyProcessedError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))

    if payment.status == "reussi":
        notifications.notify(
            db, user_id=payment.user_id, category="confirmation", module="paiement",
            title="Paiement confirmé", link="/payments",
            message=f"Votre paiement de {payment.amount} {payment.currency} a été confirmé. Votre abonnement est actif.",
        )
    elif payment.status == "echoue":
        notifications.notify(
            db, user_id=payment.user_id, category="alerte", module="paiement",
            title="Paiement échoué", link="/payments",
            message="Votre tentative de paiement a échoué. Vous pouvez réessayer depuis la page Paiement.",
        )
    return payment
