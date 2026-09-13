from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.rate_limit import rate_limit
from app.modules.auth.router import get_current_user
from app.modules.auth.models import User
from app.modules.marketplace import service
from app.modules.marketplace.schemas import (
    ProductCreate,
    ProductUpdate,
    ProductOut,
    OrderCreate,
    OrderOut,
    OrderStatusUpdate,
)

router = APIRouter(prefix="/marketplace", tags=["Marketplace"])


@router.post(
    "/products",
    response_model=ProductOut,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(rate_limit(max_requests=20, window_seconds=60))],
)
def create_product(
    data: ProductCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return service.create_product(db, current_user.id, data)


@router.get("/products/search", response_model=list[ProductOut])
def search_products(
    country: str | None = Query(None),
    category: str | None = Query(None),
    q: str | None = Query(None, description="Recherche texte dans le titre et la description"),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return service.search_products(
        db,
        country=country,
        category=category,
        query_text=q,
        limit=limit,
        offset=offset,
        viewer_country=current_user.country,
    )


@router.get("/products/{product_id}", response_model=ProductOut)
def get_product(product_id: str, db: Session = Depends(get_db)):
    try:
        return service.get_product(db, product_id)
    except service.ProductNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))


@router.patch("/products/{product_id}", response_model=ProductOut)
def update_product(
    product_id: str,
    data: ProductUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        return service.update_product(db, product_id, current_user.id, data)
    except service.ProductNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    except service.NotSellerError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc))


@router.delete("/products/{product_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_product(
    product_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        service.delete_product(db, product_id, current_user.id)
    except service.ProductNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    except service.NotSellerError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc))


@router.post(
    "/orders",
    response_model=OrderOut,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(rate_limit(max_requests=10, window_seconds=60))],
)
def create_order(
    data: OrderCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        return service.create_order(db, current_user.id, data)
    except service.ProductNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    except service.InsufficientStockError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))


@router.get("/orders/mine", response_model=list[OrderOut])
def list_my_orders(
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return service.list_buyer_orders(db, current_user.id, limit=limit, offset=offset)


@router.get("/orders/selling", response_model=list[OrderOut])
def list_orders_to_fulfill(
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Commandes que l'utilisateur doit honorer en tant que vendeur."""
    return service.list_seller_orders(db, current_user.id, limit=limit, offset=offset)


@router.get("/orders/{order_id}", response_model=OrderOut)
def get_order(
    order_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        return service.get_order(db, order_id, current_user.id)
    except service.OrderNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))


@router.patch("/orders/{order_id}/status", response_model=OrderOut)
def update_order_status(
    order_id: str,
    data: OrderStatusUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        return service.update_order_status(db, order_id, current_user.id, data.status)
    except service.OrderNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    except service.InvalidOrderTransitionError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
