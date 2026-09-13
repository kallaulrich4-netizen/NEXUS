from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.rate_limit import rate_limit
from app.modules.auth.router import get_current_user
from app.modules.auth.models import User
from app.modules.maps import service
from app.modules.maps.models import Listing
from app.modules.maps.schemas import ListingCreate, ListingUpdate, ListingOut, ReviewCreate, ReviewOut

router = APIRouter(prefix="/maps", tags=["Cartographie intelligente"])


def _to_listing_out(db: Session, listing: Listing) -> ListingOut:
    avg_rating, reviews_count = service.get_listing_rating_stats(db, listing.id)
    return ListingOut(
        id=listing.id,
        owner_id=listing.owner_id,
        name=listing.name,
        category=listing.category,
        description=listing.description,
        latitude=listing.latitude,
        longitude=listing.longitude,
        address=listing.address,
        city=listing.city,
        country=listing.country,
        phone=listing.phone,
        email=listing.email,
        website=listing.website,
        is_verified=listing.is_verified,
        is_active=listing.is_active,
        created_at=listing.created_at,
        updated_at=listing.updated_at,
        average_rating=avg_rating,
        reviews_count=reviews_count,
        distance_km=round(listing.__dict__["_distance_km"], 2) if "_distance_km" in listing.__dict__ else None,
    )


@router.post(
    "/listings",
    response_model=ListingOut,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(rate_limit(max_requests=20, window_seconds=60))],
)
def create_listing(
    data: ListingCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    listing = service.create_listing(db, current_user.id, data)
    return _to_listing_out(db, listing)


@router.get("/listings/search", response_model=list[ListingOut])
def search_listings(
    category: str | None = Query(None),
    country: str | None = Query(None),
    city: str | None = Query(None),
    q: str | None = Query(None),
    near_lat: float | None = Query(None),
    near_lng: float | None = Query(None),
    radius_km: float | None = Query(None, gt=0),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
):
    listings = service.search_listings(
        db,
        category=category,
        country=country,
        city=city,
        query_text=q,
        near_lat=near_lat,
        near_lng=near_lng,
        radius_km=radius_km,
        limit=limit,
        offset=offset,
    )
    return [_to_listing_out(db, l) for l in listings]


@router.get("/listings/{listing_id}", response_model=ListingOut)
def get_listing(listing_id: str, db: Session = Depends(get_db)):
    try:
        listing = service.get_listing(db, listing_id)
    except service.ListingNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    return _to_listing_out(db, listing)


@router.patch("/listings/{listing_id}", response_model=ListingOut)
def update_listing(
    listing_id: str,
    data: ListingUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        listing = service.update_listing(db, listing_id, current_user.id, data)
    except service.ListingNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    except service.NotOwnerError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc))
    return _to_listing_out(db, listing)


@router.delete("/listings/{listing_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_listing(
    listing_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        service.delete_listing(db, listing_id, current_user.id)
    except service.ListingNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    except service.NotOwnerError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc))


@router.post(
    "/listings/{listing_id}/reviews",
    response_model=ReviewOut,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(rate_limit(max_requests=20, window_seconds=60))],
)
def add_review(
    listing_id: str,
    data: ReviewCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        return service.add_review(db, listing_id, current_user.id, data.rating, data.comment)
    except service.ListingNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    except service.AlreadyReviewedError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))


@router.get("/listings/{listing_id}/reviews", response_model=list[ReviewOut])
def list_reviews(
    listing_id: str,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
):
    return service.list_reviews(db, listing_id, limit=limit, offset=offset)
