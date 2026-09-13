from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.modules.payments.models import Plan, Subscription, Payment
from app.modules.auth.models import User


class PlanNotFoundError(Exception):
    """Levée quand un plan n'existe pas ou n'est plus actif."""


class SubscriptionNotFoundError(Exception):
    """Levée quand un abonnement n'existe pas ou n'appartient pas à l'utilisateur."""


class PaymentNotFoundError(Exception):
    """Levée quand un paiement référencé par un webhook est introuvable."""


class PaymentAlreadyProcessedError(Exception):
    """Levée quand un webhook tente de confirmer un paiement déjà traité (évite le double-crédit)."""


def create_plan(db: Session, data) -> Plan:
    plan = Plan(is_active=True, **data.model_dump())
    db.add(plan)
    db.commit()
    db.refresh(plan)
    return plan


def list_active_plans(db: Session) -> list[Plan]:
    return db.query(Plan).filter(Plan.is_active.is_(True)).order_by(Plan.duration_days).all()


def get_plan(db: Session, plan_id: str) -> Plan:
    plan = db.query(Plan).filter(Plan.id == plan_id, Plan.is_active.is_(True)).first()
    if plan is None:
        raise PlanNotFoundError("Plan introuvable ou retiré de la vente.")
    return plan


def subscribe(db: Session, user_id: str, data, provider) -> tuple[Subscription, Payment]:
    """
    Crée un abonnement EN ATTENTE et déclenche la tentative de paiement.
    Aucun accès premium n'est accordé ici : voir `confirm_payment`,
    déclenché par le webhook du fournisseur une fois l'argent réellement
    encaissé. C'est ce qui protège contre un faux crédit d'abonnement.
    """
    plan = get_plan(db, data.plan_id)

    subscription = Subscription(user_id=user_id, plan_id=plan.id, status="en_attente_paiement")
    db.add(subscription)
    db.flush()

    payment = Payment(
        subscription_id=subscription.id,
        user_id=user_id,
        amount=plan.price_amount,
        currency=plan.currency,
        method=data.payment_method,
        status="en_attente",
    )
    db.add(payment)
    db.flush()

    result = provider.charge(
        amount=float(plan.price_amount),
        currency=plan.currency,
        method=data.payment_method,
        user_reference=user_id,
    )
    payment.status = result["status"]
    payment.provider_reference = result.get("provider_reference")
    payment.failure_reason = result.get("failure_reason")

    db.commit()
    db.refresh(subscription)
    db.refresh(payment)
    return subscription, payment


def get_subscription(db: Session, subscription_id: str, user_id: str) -> Subscription:
    subscription = (
        db.query(Subscription)
        .filter(Subscription.id == subscription_id, Subscription.user_id == user_id)
        .first()
    )
    if subscription is None:
        raise SubscriptionNotFoundError("Abonnement introuvable.")
    return subscription


def list_my_subscriptions(db: Session, user_id: str) -> list[Subscription]:
    return (
        db.query(Subscription)
        .filter(Subscription.user_id == user_id)
        .order_by(Subscription.created_at.desc())
        .all()
    )


def cancel_subscription(db: Session, subscription_id: str, user_id: str) -> Subscription:
    subscription = get_subscription(db, subscription_id, user_id)
    if subscription.status == "active":
        subscription.status = "annulee"
        db.commit()
        db.refresh(subscription)
    return subscription


def list_my_payments(db: Session, user_id: str) -> list[Payment]:
    """Historique complet des tentatives de paiement de l'utilisateur — utilisé par la page Paiement."""
    return (
        db.query(Payment)
        .filter(Payment.user_id == user_id)
        .order_by(Payment.created_at.desc())
        .all()
    )


def get_active_subscription(db: Session, user_id: str) -> Subscription | None:
    """Retourne l'abonnement actif de l'utilisateur, s'il y en a un — utilisé pour l'affichage de statut."""
    now = datetime.now(timezone.utc)
    return (
        db.query(Subscription)
        .filter(
            Subscription.user_id == user_id,
            Subscription.status == "active",
            Subscription.ends_at.isnot(None),
            Subscription.ends_at > now,
        )
        .order_by(Subscription.ends_at.desc())
        .first()
    )


def confirm_payment(db: Session, payload) -> Payment:
    """
    Traite la confirmation d'un paiement envoyée par le fournisseur réel
    (MTN, Orange, processeur carte) via webhook. C'est le SEUL endroit
    qui active réellement un abonnement et met à jour `user.premium_until`.
    """
    payment = db.query(Payment).filter(Payment.provider_reference == payload.provider_reference).first()
    if payment is None:
        raise PaymentNotFoundError("Paiement introuvable pour cette référence fournisseur.")

    if payment.status in {"reussi", "echoue", "rembourse"}:
        raise PaymentAlreadyProcessedError(
            "Ce paiement a déjà été traité ; le webhook est ignoré (anti double-crédit)."
        )

    payment.status = payload.status
    payment.failure_reason = payload.failure_reason

    if payload.status == "reussi":
        subscription = db.query(Subscription).filter(Subscription.id == payment.subscription_id).first()
        plan = db.query(Plan).filter(Plan.id == subscription.plan_id).first()

        now = datetime.now(timezone.utc)
        subscription.status = "active"
        subscription.starts_at = now
        subscription.ends_at = now + timedelta(days=plan.duration_days)

        user = db.query(User).filter(User.id == payment.user_id).first()
        current_premium_until = user.premium_until
        if current_premium_until and current_premium_until > now:
            user.premium_until = current_premium_until + timedelta(days=plan.duration_days)
        else:
            user.premium_until = subscription.ends_at
    else:
        subscription = db.query(Subscription).filter(Subscription.id == payment.subscription_id).first()
        subscription.status = "annulee"

    db.commit()
    db.refresh(payment)
    return payment
