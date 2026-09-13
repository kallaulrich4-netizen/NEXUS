from sqlalchemy.orm import Session

from app.modules.marketplace.models import Product, Order, OrderItem


class ProductNotFoundError(Exception):
    """Levée quand un produit n'existe pas ou n'est plus actif."""


class NotSellerError(Exception):
    """Levée quand un utilisateur tente de modifier le produit d'un autre vendeur."""


class InsufficientStockError(Exception):
    """Levée quand la quantité demandée dépasse le stock disponible."""


class OrderNotFoundError(Exception):
    """Levée quand une commande n'existe pas ou n'appartient pas à l'utilisateur."""


class InvalidOrderTransitionError(Exception):
    """Levée quand un changement de statut de commande n'est pas autorisé."""


def create_product(db: Session, seller_id: str, data) -> Product:
    product = Product(seller_id=seller_id, **data.model_dump())
    db.add(product)
    db.commit()
    db.refresh(product)
    return product


def get_product(db: Session, product_id: str) -> Product:
    product = db.query(Product).filter(Product.id == product_id).first()
    if product is None:
        raise ProductNotFoundError("Produit introuvable.")
    return product


def update_product(db: Session, product_id: str, seller_id: str, data) -> Product:
    product = get_product(db, product_id)
    if product.seller_id != seller_id:
        raise NotSellerError("Vous ne pouvez modifier que vos propres produits.")

    updates = data.model_dump(exclude_unset=True)
    for field, value in updates.items():
        setattr(product, field, value)

    db.commit()
    db.refresh(product)
    return product


def delete_product(db: Session, product_id: str, seller_id: str) -> None:
    product = get_product(db, product_id)
    if product.seller_id != seller_id:
        raise NotSellerError("Vous ne pouvez supprimer que vos propres produits.")
    db.delete(product)
    db.commit()


def search_products(
    db: Session,
    country: str | None = None,
    category: str | None = None,
    query_text: str | None = None,
    limit: int = 20,
    offset: int = 0,
    viewer_country: str | None = None,
) -> list[Product]:
    """
    Recherche de produits. Si `viewer_country` est fourni sans filtre pays
    explicite, les produits du pays de l'utilisateur remontent en premier
    (priorité au local), sans jamais exclure l'international — conforme
    à la vision "achat local en priorité, accès international conservé".
    """
    q = db.query(Product).filter(Product.is_active.is_(True))

    if country:
        q = q.filter(Product.country == country)
    if category:
        q = q.filter(Product.category == category)
    if query_text:
        like_pattern = f"%{query_text.strip()}%"
        q = q.filter(Product.title.ilike(like_pattern) | Product.description.ilike(like_pattern))

    if not country and viewer_country:
        # SQLite et PostgreSQL supportent tous deux CASE WHEN via SQLAlchemy.
        from sqlalchemy import case

        priority = case((Product.country == viewer_country, 0), else_=1)
        q = q.order_by(priority, Product.created_at.desc())
    else:
        q = q.order_by(Product.created_at.desc())

    return q.offset(offset).limit(limit).all()


def create_order(db: Session, buyer_id: str, data) -> Order:
    """
    Crée une commande multi-vendeurs à partir d'une liste d'articles.

    Protection anti-survente : le stock est vérifié ET décrémenté dans la
    même transaction, avant le commit final. En PostgreSQL en production,
    ajoutez `.with_for_update()` sur la requête produit pour verrouiller
    la ligne pendant la transaction et empêcher deux achats simultanés de
    survendre le même dernier exemplaire (SQLite ne supporte pas ce verrou
    au niveau ligne).
    """
    order_items: list[OrderItem] = []
    total_amount = 0

    try:
        for item in data.items:
            product = db.query(Product).filter(Product.id == item.product_id).first()
            if product is None or not product.is_active:
                raise ProductNotFoundError(f"Produit {item.product_id} introuvable ou indisponible.")
            if product.stock_quantity < item.quantity:
                raise InsufficientStockError(
                    f"Stock insuffisant pour « {product.title} » "
                    f"(disponible : {product.stock_quantity}, demandé : {item.quantity})."
                )

            product.stock_quantity -= item.quantity
            unit_price = product.price_amount
            total_amount += float(unit_price) * item.quantity

            order_items.append(
                OrderItem(
                    product_id=product.id,
                    seller_id=product.seller_id,
                    product_title_snapshot=product.title,
                    unit_price_snapshot=unit_price,
                    quantity=item.quantity,
                )
            )

        currency = db.query(Product).filter(Product.id == data.items[0].product_id).first().currency

        order = Order(
            buyer_id=buyer_id,
            status="pending",
            total_amount=total_amount,
            currency=currency,
            shipping_country=data.shipping_country,
            shipping_city=data.shipping_city,
            shipping_address=data.shipping_address,
            items=order_items,
        )
        db.add(order)
        db.commit()
        db.refresh(order)
        return order
    except (ProductNotFoundError, InsufficientStockError):
        db.rollback()
        raise


def get_order(db: Session, order_id: str, buyer_id: str) -> Order:
    order = db.query(Order).filter(Order.id == order_id, Order.buyer_id == buyer_id).first()
    if order is None:
        raise OrderNotFoundError("Commande introuvable.")
    return order


def list_buyer_orders(db: Session, buyer_id: str, limit: int = 20, offset: int = 0) -> list[Order]:
    return (
        db.query(Order)
        .filter(Order.buyer_id == buyer_id)
        .order_by(Order.created_at.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )


def list_seller_orders(db: Session, seller_id: str, limit: int = 20, offset: int = 0) -> list[Order]:
    """Commandes contenant au moins un article vendu par ce vendeur."""
    return (
        db.query(Order)
        .join(OrderItem)
        .filter(OrderItem.seller_id == seller_id)
        .order_by(Order.created_at.desc())
        .distinct()
        .offset(offset)
        .limit(limit)
        .all()
    )


_VALID_TRANSITIONS = {
    "pending": {"confirmed", "cancelled"},
    "confirmed": {"shipped", "cancelled"},
    "shipped": {"delivered"},
    "delivered": set(),
    "cancelled": set(),
}


def update_order_status(db: Session, order_id: str, seller_id: str, new_status: str) -> Order:
    """Seul un vendeur impliqué dans la commande peut faire progresser son statut."""
    order = (
        db.query(Order)
        .join(OrderItem)
        .filter(Order.id == order_id, OrderItem.seller_id == seller_id)
        .first()
    )
    if order is None:
        raise OrderNotFoundError("Commande introuvable pour ce vendeur.")

    if new_status not in _VALID_TRANSITIONS.get(order.status, set()):
        raise InvalidOrderTransitionError(
            f"Transition de statut invalide : « {order.status} » -> « {new_status} »."
        )

    order.status = new_status
    db.commit()
    db.refresh(order)
    return order
