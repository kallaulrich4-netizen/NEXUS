from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, field_validator, model_validator

from app.modules.agriculture.models import CROP_CYCLE_STATUSES, ACTIVITY_TYPES


class FieldCreate(BaseModel):
    name: str
    area_hectares: float
    soil_type: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    country: str
    region: str | None = None

    @field_validator("name")
    @classmethod
    def name_valid(cls, value: str) -> str:
        cleaned = value.strip()
        if not (2 <= len(cleaned) <= 255):
            raise ValueError("Le nom de la parcelle doit contenir entre 2 et 255 caractères.")
        return cleaned

    @field_validator("area_hectares")
    @classmethod
    def area_positive(cls, value: float) -> float:
        if value <= 0:
            raise ValueError("La superficie doit être supérieure à zéro.")
        return value


class FieldUpdate(BaseModel):
    name: str | None = None
    soil_type: str | None = None
    region: str | None = None


class FieldOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    owner_id: str
    name: str
    area_hectares: float
    soil_type: str | None
    latitude: float | None
    longitude: float | None
    country: str
    region: str | None
    created_at: datetime
    updated_at: datetime


class CropCycleCreate(BaseModel):
    crop_name: str
    planting_date: date
    expected_harvest_date: date | None = None
    notes: str | None = None

    @field_validator("crop_name")
    @classmethod
    def crop_name_valid(cls, value: str) -> str:
        cleaned = value.strip()
        if not (2 <= len(cleaned) <= 100):
            raise ValueError("Le nom de la culture doit contenir entre 2 et 100 caractères.")
        return cleaned

    @model_validator(mode="after")
    def harvest_after_planting(self):
        if self.expected_harvest_date and self.expected_harvest_date < self.planting_date:
            raise ValueError("La date de récolte prévue ne peut pas précéder la date de semis.")
        return self


class CropCycleHarvest(BaseModel):
    actual_harvest_date: date
    yield_amount: float
    yield_unit: str

    @field_validator("yield_amount")
    @classmethod
    def yield_non_negative(cls, value: float) -> float:
        if value < 0:
            raise ValueError("Le rendement ne peut pas être négatif.")
        return value


class CropCycleOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    field_id: str
    crop_name: str
    status: str
    planting_date: date
    expected_harvest_date: date | None
    actual_harvest_date: date | None
    yield_amount: float | None
    yield_unit: str | None
    notes: str | None
    created_at: datetime
    updated_at: datetime


class ActivityCreate(BaseModel):
    activity_type: str
    activity_date: date
    notes: str | None = None
    cost_amount: float | None = None
    cost_currency: str | None = None

    @field_validator("activity_type")
    @classmethod
    def activity_type_valid(cls, value: str) -> str:
        if value not in ACTIVITY_TYPES:
            raise ValueError(f"Type d'activité invalide. Valeurs valides : {', '.join(sorted(ACTIVITY_TYPES))}.")
        return value

    @field_validator("cost_amount")
    @classmethod
    def cost_non_negative(cls, value: float | None) -> float | None:
        if value is not None and value < 0:
            raise ValueError("Le coût ne peut pas être négatif.")
        return value


class ActivityOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    crop_cycle_id: str
    activity_type: str
    activity_date: date
    notes: str | None
    cost_amount: float | None
    cost_currency: str | None
    created_at: datetime


class FieldYieldSummary(BaseModel):
    field_id: str
    field_name: str
    total_cycles: int
    harvested_cycles: int
    total_yield_by_unit: dict[str, float]
    total_cost: float


# ============================================================================
# AGRICULTURE V2
# ============================================================================

class CropRecommendationRequest(BaseModel):
    season: str | None = None
    budget_amount: float | None = None
    budget_currency: str | None = "XOF"

    @field_validator("budget_amount")
    @classmethod
    def budget_non_negative(cls, value: float | None) -> float | None:
        if value is not None and value < 0:
            raise ValueError("Le budget ne peut pas être négatif.")
        return value


class CropRecommendationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    field_id: str
    crop_name: str
    score: float
    rationale: str
    season: str | None
    budget_amount: float | None
    budget_currency: str | None
    created_at: datetime


class CalendarTaskOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    crop_cycle_id: str
    task_type: str
    title: str
    due_date: date
    status: str
    notes: str | None
    created_at: datetime
    updated_at: datetime


class CalendarTaskUpdate(BaseModel):
    status: str
    notes: str | None = None

    @field_validator("status")
    @classmethod
    def status_valid(cls, value: str) -> str:
        from app.modules.agriculture.models import CALENDAR_TASK_STATUSES
        if value not in CALENDAR_TASK_STATUSES:
            raise ValueError(f"Statut invalide. Valeurs valides : {', '.join(sorted(CALENDAR_TASK_STATUSES))}.")
        return value


class DiseaseDiagnosisRequest(BaseModel):
    symptoms_description: str
    photo_reference: str | None = None

    @field_validator("symptoms_description")
    @classmethod
    def symptoms_valid(cls, value: str) -> str:
        cleaned = value.strip()
        if len(cleaned) < 5:
            raise ValueError("Veuillez décrire les symptômes observés (5 caractères minimum).")
        return cleaned


class DiseaseDiagnosisOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    crop_cycle_id: str
    symptoms_description: str
    photo_reference: str | None
    diagnosis_text: str
    recommended_actions: str
    confidence: float | None
    status: str
    created_at: datetime


class FinancialProjectionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    field_id: str
    crop_cycle_id: str | None
    estimated_cost_total: float
    estimated_revenue_total: float
    estimated_profit: float
    currency: str
    assumptions: str | None
    created_at: datetime


class FinancialProjectionRequest(BaseModel):
    crop_cycle_id: str | None = None
    market_price_per_unit: float | None = None
    currency: str = "XOF"

    @field_validator("market_price_per_unit")
    @classmethod
    def price_non_negative(cls, value: float | None) -> float | None:
        if value is not None and value < 0:
            raise ValueError("Le prix de marché ne peut pas être négatif.")
        return value


class FarmDashboardField(BaseModel):
    field_id: str
    field_name: str
    active_cycles: int
    upcoming_tasks: int
    overdue_tasks: int
    total_cost_to_date: float


class FarmDashboard(BaseModel):
    total_fields: int
    total_active_cycles: int
    total_upcoming_tasks: int
    total_overdue_tasks: int
    fields: list[FarmDashboardField]
