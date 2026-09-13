from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, field_validator

from app.modules.livestock.models import HEALTH_EVENT_TYPES, SUGGESTED_SPECIES


class HerdCreate(BaseModel):
    name: str
    species: str  # texte libre — voir SUGGESTED_SPECIES pour des exemples, non contraignant
    breed: str | None = None
    current_count: int = 0
    country: str
    region: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    notes: str | None = None

    @field_validator("name")
    @classmethod
    def name_valid(cls, value: str) -> str:
        cleaned = value.strip()
        if not (2 <= len(cleaned) <= 255):
            raise ValueError("Le nom du troupeau doit contenir entre 2 et 255 caractères.")
        return cleaned

    @field_validator("species")
    @classmethod
    def species_valid(cls, value: str) -> str:
        cleaned = value.strip().lower()
        if not (2 <= len(cleaned) <= 100):
            raise ValueError("L'espèce doit contenir entre 2 et 100 caractères.")
        return cleaned

    @field_validator("current_count")
    @classmethod
    def count_non_negative(cls, value: int) -> int:
        if value < 0:
            raise ValueError("L'effectif ne peut pas être négatif.")
        return value


class HerdUpdate(BaseModel):
    name: str | None = None
    breed: str | None = None
    region: str | None = None
    notes: str | None = None


class HerdOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    owner_id: str
    name: str
    species: str
    breed: str | None
    current_count: int
    country: str
    region: str | None
    latitude: float | None
    longitude: float | None
    notes: str | None
    created_at: datetime
    updated_at: datetime


class HealthEventCreate(BaseModel):
    event_type: str
    event_date: date
    count_change: int = 0
    notes: str | None = None
    cost_amount: float | None = None
    cost_currency: str | None = None

    @field_validator("event_type")
    @classmethod
    def event_type_valid(cls, value: str) -> str:
        if value not in HEALTH_EVENT_TYPES:
            raise ValueError(f"Type d'événement invalide. Valeurs valides : {', '.join(sorted(HEALTH_EVENT_TYPES))}.")
        return value

    @field_validator("cost_amount")
    @classmethod
    def cost_non_negative(cls, value: float | None) -> float | None:
        if value is not None and value < 0:
            raise ValueError("Le coût ne peut pas être négatif.")
        return value


class HealthEventOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    herd_id: str
    event_type: str
    event_date: date
    count_change: int
    notes: str | None
    cost_amount: float | None
    cost_currency: str | None
    created_at: datetime


class ProductionRecordCreate(BaseModel):
    product_type: str  # texte libre : lait, oeufs, laine, miel, viande...
    quantity: float
    unit: str
    record_date: date
    notes: str | None = None

    @field_validator("product_type")
    @classmethod
    def product_type_valid(cls, value: str) -> str:
        cleaned = value.strip().lower()
        if not (2 <= len(cleaned) <= 100):
            raise ValueError("Le type de production doit contenir entre 2 et 100 caractères.")
        return cleaned

    @field_validator("quantity")
    @classmethod
    def quantity_non_negative(cls, value: float) -> float:
        if value < 0:
            raise ValueError("La quantité ne peut pas être négative.")
        return value


class ProductionRecordOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    herd_id: str
    product_type: str
    quantity: float
    unit: str
    record_date: date
    notes: str | None
    created_at: datetime


class HerdSummary(BaseModel):
    herd_id: str
    herd_name: str
    current_count: int
    total_health_events: int
    total_health_cost: float
    total_production_by_type: dict[str, float]


# ============================================================================
# ÉLEVAGE V2 — Fiche individuelle
# ============================================================================

class AnimalCreate(BaseModel):
    tag: str
    breed: str | None = None
    sex: str = "inconnu"
    birth_date: date | None = None
    current_weight_kg: float | None = None
    parent_id: str | None = None
    notes: str | None = None

    @field_validator("tag")
    @classmethod
    def tag_valid(cls, value: str) -> str:
        cleaned = value.strip()
        if not (1 <= len(cleaned) <= 100):
            raise ValueError("L'identifiant de l'animal doit contenir entre 1 et 100 caractères.")
        return cleaned

    @field_validator("sex")
    @classmethod
    def sex_valid(cls, value: str) -> str:
        from app.modules.livestock.models import ANIMAL_SEXES
        if value not in ANIMAL_SEXES:
            raise ValueError(f"Sexe invalide. Valeurs valides : {', '.join(sorted(ANIMAL_SEXES))}.")
        return value

    @field_validator("current_weight_kg")
    @classmethod
    def weight_non_negative(cls, value: float | None) -> float | None:
        if value is not None and value < 0:
            raise ValueError("Le poids ne peut pas être négatif.")
        return value


class AnimalUpdate(BaseModel):
    tag: str | None = None
    breed: str | None = None
    current_weight_kg: float | None = None
    status: str | None = None
    notes: str | None = None

    @field_validator("status")
    @classmethod
    def status_valid(cls, value: str | None) -> str | None:
        if value is None:
            return value
        from app.modules.livestock.models import ANIMAL_STATUSES
        if value not in ANIMAL_STATUSES:
            raise ValueError(f"Statut invalide. Valeurs valides : {', '.join(sorted(ANIMAL_STATUSES))}.")
        return value


class AnimalOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    herd_id: str
    parent_id: str | None
    tag: str
    breed: str | None
    sex: str
    birth_date: date | None
    current_weight_kg: float | None
    status: str
    notes: str | None
    created_at: datetime
    updated_at: datetime


class AnimalHealthRecordCreate(BaseModel):
    record_type: str
    record_date: date
    notes: str | None = None
    cost_amount: float | None = None
    cost_currency: str | None = None
    next_due_date: date | None = None

    @field_validator("record_type")
    @classmethod
    def record_type_valid(cls, value: str) -> str:
        from app.modules.livestock.models import ANIMAL_HEALTH_RECORD_TYPES
        if value not in ANIMAL_HEALTH_RECORD_TYPES:
            raise ValueError(
                f"Type d'événement invalide. Valeurs valides : {', '.join(sorted(ANIMAL_HEALTH_RECORD_TYPES))}."
            )
        return value

    @field_validator("cost_amount")
    @classmethod
    def cost_non_negative(cls, value: float | None) -> float | None:
        if value is not None and value < 0:
            raise ValueError("Le coût ne peut pas être négatif.")
        return value


class AnimalHealthRecordOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    animal_id: str
    record_type: str
    record_date: date
    notes: str | None
    cost_amount: float | None
    cost_currency: str | None
    next_due_date: date | None
    created_at: datetime


class WeightRecordCreate(BaseModel):
    weight_kg: float
    measured_at: date
    notes: str | None = None

    @field_validator("weight_kg")
    @classmethod
    def weight_non_negative(cls, value: float) -> float:
        if value < 0:
            raise ValueError("Le poids ne peut pas être négatif.")
        return value


class WeightRecordOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    animal_id: str
    weight_kg: float
    measured_at: date
    notes: str | None
    created_at: datetime


class GrowthSummary(BaseModel):
    animal_id: str
    animal_tag: str
    first_weight_kg: float | None
    latest_weight_kg: float | None
    total_gain_kg: float | None
    average_daily_gain_kg: float | None
    records: list[WeightRecordOut]


class ReproductionRecordCreate(BaseModel):
    event_type: str
    event_date: date
    expected_birth_date: date | None = None
    notes: str | None = None

    @field_validator("event_type")
    @classmethod
    def event_type_valid(cls, value: str) -> str:
        from app.modules.livestock.models import REPRODUCTION_EVENT_TYPES
        if value not in REPRODUCTION_EVENT_TYPES:
            raise ValueError(
                f"Type d'événement invalide. Valeurs valides : {', '.join(sorted(REPRODUCTION_EVENT_TYPES))}."
            )
        return value


class ReproductionRecordOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    animal_id: str
    offspring_animal_id: str | None
    event_type: str
    event_date: date
    expected_birth_date: date | None
    notes: str | None
    created_at: datetime


class BirthDeclaration(BaseModel):
    """Déclare la mise bas : crée automatiquement les fiches des petits et ajuste l'effectif du troupeau."""
    event_date: date
    offspring_count: int
    offspring_sex: str = "inconnu"
    notes: str | None = None

    @field_validator("offspring_count")
    @classmethod
    def offspring_count_positive(cls, value: int) -> int:
        if value <= 0:
            raise ValueError("Le nombre de petits doit être supérieur à zéro.")
        return value


class FeedPlanRequest(BaseModel):
    feed_type: str | None = None

    @field_validator("feed_type")
    @classmethod
    def feed_type_valid(cls, value: str | None) -> str | None:
        if value is not None and not value.strip():
            raise ValueError("Le type d'aliment ne peut pas être vide.")
        return value


class FeedPlanOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    herd_id: str
    feed_type: str
    daily_quantity_kg: float
    estimated_daily_cost: float
    currency: str
    notes: str | None
    created_at: datetime


class HerdEconomics(BaseModel):
    herd_id: str
    herd_name: str
    total_cost: float
    total_revenue_from_sales: float
    total_revenue_from_production: float
    estimated_herd_value: float
    net_profit: float
    currency: str
