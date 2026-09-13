from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, field_validator

VALID_CURRENCIES = {"XOF", "XAF", "EUR", "USD", "GBP", "CAD", "MAD", "NGN", "GHS", "CNY"}
VALID_SHIPPING_SCOPES = {"local", "national", "international"}
VALID_ORDER_STATUSES = {"pending", "confirmed", "shipped", "delivered", "cancelled"}


class ProductCreate(BaseModel):
    title: str
    description: str
    price_amount: Decimal
    currency: str = "XOF"
    stock_quantity: int = 0
    category: str
    country: str
    city: str | None = None
    shipping_scope: str = "local"

    @field_validator("title")
    @classmethod
    def title_valid(cls, value: str) -> str:
        cleaned = value.strip()
        if not (3 <= len(cleaned) <= 255):
            raise ValueError("Le titre doit contenir entre 3 et 255 caractères.")
        return cleaned

    @field_validator("description")
    @classmethod
    def description_valid(cls, value: str) -> str:
        cleaned = value.strip()
        if len(cleaned) < 10:
            raise ValueError("La description doit contenir au moins 10 caractères.")
        if len(cleaned) > 10000:
            raise ValueError("La description dépasse la longueur maximale autorisée.")
        return cleaned

    @field_validator("price_amount")
    @classmethod
    def price_non_negative(cls, value: Decimal) -> Decimal:
        if value < 0:
            raise ValueError("Le prix ne peut pas être négatif.")
        return value

    @field_validator("stock_quantity")
    @classmethod
    def stock_non_negative(cls, value: int) -> int:
        if value < 0:
            raise ValueError("Le stock ne peut pas être négatif.")
        return value

    @field_validator("currency")
    @classmethod
    def currency_valid(cls, value: str) -> str:
        upper = value.upper()
        if upper not in VALID_CURRENCIES:
            raise ValueError(f"Devise non prise en charge. Devises valides : {', '.join(sorted(VALID_CURRENCIES))}.")
        return upper

    @field_validator("shipping_scope")
    @classmethod
    def scope_valid(cls, value: str) -> str:
        if value not in VALID_SHIPPING_SCOPES:
            raise ValueError(f"La portée doit être l'une de : {', '.join(VALID_SHIPPING_SCOPES)}.")
        return value


class ProductUpdate(BaseModel):
    title: str | None = None
    description: str | None = None
    price_amount: Decimal | None = None
    stock_quantity: int | None = None
    is_active: bool | None = None


class ProductOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    seller_id: str
    title: str
    description: str
    price_amount: Decimal
    currency: str
    stock_quantity: int
    category: str
    country: str
    city: str | None
    shipping_scope: str
    is_active: bool
    created_at: datetime
    updated_at: datetime


class OrderItemRequest(BaseModel):
    product_id: str
    quantity: int

    @field_validator("quantity")
    @classmethod
    def quantity_positive(cls, value: int) -> int:
        if value <= 0:
            raise ValueError("La quantité doit être supérieure à zéro.")
        return value


class OrderCreate(BaseModel):
    items: list[OrderItemRequest]
    shipping_country: str
    shipping_city: str | None = None
    shipping_address: str

    @field_validator("items")
    @classmethod
    def items_not_empty(cls, value: list[OrderItemRequest]) -> list[OrderItemRequest]:
        if not value:
            raise ValueError("La commande doit contenir au moins un article.")
        if len(value) > 100:
            raise ValueError("Trop d'articles dans une seule commande.")
        return value

    @field_validator("shipping_address")
    @classmethod
    def address_valid(cls, value: str) -> str:
        cleaned = value.strip()
        if len(cleaned) < 5:
            raise ValueError("L'adresse de livraison est trop courte.")
        return cleaned


class OrderItemOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    product_id: str
    seller_id: str
    product_title_snapshot: str
    unit_price_snapshot: Decimal
    quantity: int


class OrderOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    buyer_id: str
    status: str
    total_amount: Decimal
    currency: str
    shipping_country: str
    shipping_city: str | None
    shipping_address: str
    created_at: datetime
    updated_at: datetime
    items: list[OrderItemOut] = []


class OrderStatusUpdate(BaseModel):
    status: str

    @field_validator("status")
    @classmethod
    def status_valid(cls, value: str) -> str:
        if value not in VALID_ORDER_STATUSES:
            raise ValueError(f"Statut invalide. Statuts valides : {', '.join(VALID_ORDER_STATUSES)}.")
        return value
