from datetime import datetime

from pydantic import BaseModel, ConfigDict, field_validator

from app.modules.payments.models import PAYMENT_METHODS


class PlanCreate(BaseModel):
    name: str
    duration_days: int
    price_amount: float
    currency: str = "XOF"

    @field_validator("name")
    @classmethod
    def name_valid(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("Le nom du plan ne peut pas être vide.")
        return cleaned

    @field_validator("duration_days")
    @classmethod
    def duration_positive(cls, value: int) -> int:
        if value <= 0:
            raise ValueError("La durée doit être supérieure à zéro jour.")
        return value

    @field_validator("price_amount")
    @classmethod
    def price_non_negative(cls, value: float) -> float:
        if value < 0:
            raise ValueError("Le prix ne peut pas être négatif.")
        return value


class PlanOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    duration_days: int
    price_amount: float
    currency: str
    is_active: bool


class SubscribeRequest(BaseModel):
    plan_id: str
    payment_method: str

    @field_validator("payment_method")
    @classmethod
    def method_valid(cls, value: str) -> str:
        if value not in PAYMENT_METHODS:
            raise ValueError(f"Moyen de paiement invalide. Valeurs valides : {', '.join(sorted(PAYMENT_METHODS))}.")
        return value


class PaymentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    subscription_id: str
    amount: float
    currency: str
    method: str
    status: str
    provider_reference: str | None
    failure_reason: str | None
    created_at: datetime


class SubscriptionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    user_id: str
    plan_id: str
    status: str
    starts_at: datetime | None
    ends_at: datetime | None


class SubscribeResponse(BaseModel):
    subscription: SubscriptionOut
    payment: PaymentOut


class WebhookPayload(BaseModel):
    """
    Format générique attendu du webhook de confirmation. En production,
    chaque fournisseur (MTN, Orange, processeur carte) a son propre
    format exact : prévoyez un endpoint de conversion par fournisseur
    vers ce format avant de réutiliser la même logique de confirmation.
    """
    provider_reference: str
    status: str  # "reussi" ou "echoue"
    failure_reason: str | None = None

    @field_validator("status")
    @classmethod
    def status_valid(cls, value: str) -> str:
        if value not in {"reussi", "echoue"}:
            raise ValueError("Le statut du webhook doit être 'reussi' ou 'echoue'.")
        return value
