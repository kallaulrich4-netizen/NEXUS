import math

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.modules.maps.models import Listing, Review


class ListingNotFoundError(Exception):
    """Levée quand une fiche professionnelle n'existe pas."""


class NotOwnerError(Exception):
    """Levée quand un utilisateur tente de modifier la fiche d'un autre professionnel."""


class AlreadyReviewedError(Exception):
    """Levée quand un utilisateur tente de laisser un second avis sur la même fiche."""


EARTH_RADIUS_KM = 6371.0


def haversine_distance_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Calcule la distance en kilomètres entre deux points GPS (formule de
    Haversine). Utilisée pour trier les fiches par proximité réelle,
    et pas seulement par ville/pays déclarés.
    """
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)

    a = math.sin(delta_phi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2) ** 2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return EARTH_RADIUS_KM * c


def create_listing(db: Session, owner_id: str, data) -> Listing:
    listing = Listing(owner_id=owner_id, **data.model_dump())
    db.add(listing)
    db.commit()
    db.refresh(listing)
    return listing


def get_listing(db: Session, listing_id: str) -> Listing:
    listing = db.query(Listing).filter(Listing.id == listing_id).first()
    if listing is None:
        raise ListingNotFoundError("Fiche professionnelle introuvable.")
    return listing


def update_listing(db: Session, listing_id: str, owner_id: str, data) -> Listing:
    listing = get_listing(db, listing_id)
    if listing.owner_id != owner_id:
        raise NotOwnerError("Vous ne pouvez modifier que vos propres fiches.")

    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(listing, field, value)

    db.commit()
    db.refresh(listing)
    return listing


def delete_listing(db: Session, listing_id: str, owner_id: str) -> None:
    listing = get_listing(db, listing_id)
    if listing.owner_id != owner_id:
        raise NotOwnerError("Vous ne pouvez supprimer que vos propres fiches.")
    db.delete(listing)
    db.commit()


def search_listings(
    db: Session,
    category: str | None = None,
    country: str | None = None,
    city: str | None = None,
    query_text: str | None = None,
    near_lat: float | None = None,
    near_lng: float | None = None,
    radius_km: float | None = None,
    limit: int = 20,
    offset: int = 0,
) -> list[Listing]:
    """
    Recherche de fiches professionnelles. Si near_lat/near_lng/radius_km
    sont fournis, filtre et trie par distance réelle plutôt que par
    simple correspondance de ville, ce qui gère correctement les zones
    rurales où "la ville" ne suffit pas à situer une ferme isolée.
    """
    q = db.query(Listing).filter(Listing.is_active.is_(True))

    if category:
        q = q.filter(Listing.category == category)
    if country:
        q = q.filter(Listing.country == country)
    if city:
        q = q.filter(Listing.city == city)
    if query_text:
        like_pattern = f"%{query_text.strip()}%"
        q = q.filter(Listing.name.ilike(like_pattern) | Listing.description.ilike(like_pattern))

    results = q.all()

    if near_lat is not None and near_lng is not None:
        annotated = [
            (listing, haversine_distance_km(near_lat, near_lng, listing.latitude, listing.longitude))
            for listing in results
        ]
        if radius_km is not None:
            annotated = [(l, d) for l, d in annotated if d <= radius_km]
        annotated.sort(key=lambda pair: pair[1])
        for listing, distance in annotated:
            listing.__dict__["_distance_km"] = distance
        results = [listing for listing, _ in annotated]
    else:
        results = sorted(results, key=lambda l: l.created_at, reverse=True)

    return results[offset: offset + limit]


def get_listing_rating_stats(db: Session, listing_id: str) -> tuple[float | None, int]:
    avg_rating, count = (
        db.query(func.avg(Review.rating), func.count(Review.id))
        .filter(Review.listing_id == listing_id)
        .first()
    )
    return (round(avg_rating, 2) if avg_rating is not None else None, count or 0)


def add_review(db: Session, listing_id: str, author_id: str, rating: int, comment: str | None) -> Review:
    get_listing(db, listing_id)  # vérifie l'existence
    existing = (
        db.query(Review)
        .filter(Review.listing_id == listing_id, Review.author_id == author_id)
        .first()
    )
    if existing is not None:
        raise AlreadyReviewedError("Vous avez déjà laissé un avis sur cette fiche.")

    review = Review(listing_id=listing_id, author_id=author_id, rating=rating, comment=comment)
    db.add(review)
    db.commit()
    db.refresh(review)
    return review


def list_reviews(db: Session, listing_id: str, limit: int = 50, offset: int = 0) -> list[Review]:
    return (
        db.query(Review)
        .filter(Review.listing_id == listing_id)
        .order_by(Review.created_at.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )
