"""
Modèles du module Marketplace.

`Product.seller_id` et `Order.buyer_id` pointent vers `users.id` : le
même compte Nexus sert donc aussi bien à vendre qu'à acheter, comme
décrit dans la vision (achat local, vente locale, import/export).
"""
import uuid
from datetime import datetime, timezone

from sqlalchemy import String, DateTime, ForeignKey, Text, Integer, Numeric, Index, CheckConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


def generate_uuid() -> str:
    return str(uuid.uuid4())


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Product(Base):
    __tablename__ = "marketplace_products"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    seller_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), nullable=False, index=True)

    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    price_amount: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="XOF")  # code ISO 4217
    stock_quantity: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    category: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    country: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    city: Mapped[str | None] = mapped_column(String(100), nullable=True)
    # Portée de vente déclarée par le vendeur : permet de proposer en priorité
    # le local tout en gardant accès à l'international, comme demandé.
    shipping_scope: Mapped[str] = mapped_column(String(20), default="local")  # local | national | international

    is_active: Mapped[bool] = mapped_column(default=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    __table_args__ = (
        CheckConstraint("price_amount >= 0", name="ck_product_price_non_negative"),
        CheckConstraint("stock_quantity >= 0", name="ck_product_stock_non_negative"),
        Index("ix_marketplace_products_country_category", "country", "category"),
    )


class Order(Base):
    __tablename__ = "marketplace_orders"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    buyer_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), nullable=False, index=True)

    status: Mapped[str] = mapped_column(String(20), default="pending")
    # pending -> confirmed -> shipped -> delivered  (ou cancelled à tout moment avant expédition)

    total_amount: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False)

    shipping_country: Mapped[str] = mapped_column(String(100), nullable=False)
    shipping_city: Mapped[str | None] = mapped_column(String(100), nullable=True)
    shipping_address: Mapped[str] = mapped_column(Text, nullable=False)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    items: Mapped[list["OrderItem"]] = relationship(back_populates="order", cascade="all, delete-orphan")


class OrderItem(Base):
    __tablename__ = "marketplace_order_items"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    order_id: Mapped[str] = mapped_column(String(36), ForeignKey("marketplace_orders.id"), nullable=False, index=True)
    product_id: Mapped[str] = mapped_column(String(36), ForeignKey("marketplace_products.id"), nullable=False)
    seller_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), nullable=False, index=True)

    # Copie figée au moment de l'achat : si le vendeur change le prix plus
    # tard, les commandes passées ne doivent JAMAIS être affectées.
    product_title_snapshot: Mapped[str] = mapped_column(String(255), nullable=False)
    unit_price_snapshot: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)

    order: Mapped["Order"] = relationship(back_populates="items")

    __table_args__ = (CheckConstraint("quantity > 0", name="ck_order_item_quantity_positive"),)
