from datetime import datetime

from pydantic import BaseModel, ConfigDict, field_validator

from app.modules.maps.models import LISTING_CATEGORIES


class ListingCreate(BaseModel):
    name: str
    category: str
    description: str
    latitude: float
    longitude: float
    address: str
    city: str
    country: str
    phone: str | None = None
    email: str | None = None
    website: str | None = None

    @field_validator("name")
    @classmethod
    def name_valid(cls, value: str) -> str:
        cleaned = value.strip()
        if not (2 <= len(cleaned) <= 255):
            raise ValueError("Le nom doit contenir entre 2 et 255 caractères.")
        return cleaned

    @field_validator("category")
    @classmethod
    def category_valid(cls, value: str) -> str:
        if value not in LISTING_CATEGORIES:
            raise ValueError(f"Catégorie invalide. Catégories valides : {', '.join(sorted(LISTING_CATEGORIES))}.")
        return value

    @field_validator("description")
    @classmethod
    def description_valid(cls, value: str) -> str:
        cleaned = value.strip()
        if len(cleaned) < 10:
            raise ValueError("La description doit contenir au moins 10 caractères.")
        return cleaned

    @field_validator("latitude")
    @classmethod
    def latitude_valid(cls, value: float) -> float:
        if not (-90 <= value <= 90):
            raise ValueError("La latitude doit être comprise entre -90 et 90.")
        return value

    @field_validator("longitude")
    @classmethod
    def longitude_valid(cls, value: float) -> float:
        if not (-180 <= value <= 180):
            raise ValueError("La longitude doit être comprise entre -180 et 180.")
        return value


class ListingUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    address: str | None = None
    phone: str | None = None
    email: str | None = None
    website: str | None = None
    is_active: bool | None = None


class ListingOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    owner_id: str
    name: str
    category: str
    description: str
    latitude: float
    longitude: float
    address: str
    city: str
    country: str
    phone: str | None
    email: str | None
    website: str | None
    is_verified: bool
    is_active: bool
    created_at: datetime
    updated_at: datetime
    average_rating: float | None = None
    reviews_count: int = 0
    distance_km: float | None = None  # renseigné uniquement lors d'une recherche par proximité


class ReviewCreate(BaseModel):
    rating: int
    comment: str | None = None

    @field_validator("rating")
    @classmethod
    def rating_valid(cls, value: int) -> int:
        if not (1 <= value <= 5):
            raise ValueError("La note doit être comprise entre 1 et 5.")
        return value

    @field_validator("comment")
    @classmethod
    def comment_valid(cls, value: str | None) -> str | None:
        if value is None:
            return value
        cleaned = value.strip()
        if len(cleaned) > 2000:
            raise ValueError("Le commentaire dépasse la longueur maximale autorisée.")
        return cleaned or None


class ReviewOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    listing_id: str
    author_id: str
    rating: int
    comment: str | None
    created_at: datetime
