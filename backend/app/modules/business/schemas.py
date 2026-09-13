from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, EmailStr, field_validator, model_validator

from app.modules.business.models import EMPLOYEE_STATUSES, INVOICE_STATUSES


class CompanyCreate(BaseModel):
    name: str
    sector: str
    registration_number: str | None = None
    country: str
    city: str | None = None

    @field_validator("name")
    @classmethod
    def name_valid(cls, value: str) -> str:
        cleaned = value.strip()
        if not (2 <= len(cleaned) <= 255):
            raise ValueError("Le nom de l'entreprise doit contenir entre 2 et 255 caractères.")
        return cleaned

    @field_validator("sector")
    @classmethod
    def sector_valid(cls, value: str) -> str:
        cleaned = value.strip().lower()
        if not (2 <= len(cleaned) <= 100):
            raise ValueError("Le secteur doit contenir entre 2 et 100 caractères.")
        return cleaned


class CompanyUpdate(BaseModel):
    name: str | None = None
    registration_number: str | None = None
    city: str | None = None


class CompanyOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    owner_id: str
    name: str
    sector: str
    registration_number: str | None
    country: str
    city: str | None
    created_at: datetime
    updated_at: datetime


class EmployeeCreate(BaseModel):
    full_name: str
    role: str
    monthly_salary: float | None = None
    currency: str | None = None
    hire_date: date

    @field_validator("full_name", "role")
    @classmethod
    def not_empty(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("Ce champ ne peut pas être vide.")
        return cleaned

    @field_validator("monthly_salary")
    @classmethod
    def salary_non_negative(cls, value: float | None) -> float | None:
        if value is not None and value < 0:
            raise ValueError("Le salaire ne peut pas être négatif.")
        return value


class EmployeeStatusUpdate(BaseModel):
    status: str

    @field_validator("status")
    @classmethod
    def status_valid(cls, value: str) -> str:
        if value not in EMPLOYEE_STATUSES:
            raise ValueError(f"Statut invalide. Statuts valides : {', '.join(sorted(EMPLOYEE_STATUSES))}.")
        return value


class EmployeeOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    company_id: str
    full_name: str
    role: str
    monthly_salary: float | None
    currency: str | None
    hire_date: date
    status: str
    created_at: datetime
    updated_at: datetime


class ClientCreate(BaseModel):
    name: str
    email: EmailStr | None = None
    phone: str | None = None
    address: str | None = None

    @field_validator("name")
    @classmethod
    def name_valid(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("Le nom du client ne peut pas être vide.")
        return cleaned


class ClientOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    company_id: str
    name: str
    email: str | None
    phone: str | None
    address: str | None
    created_at: datetime


class InvoiceItemCreate(BaseModel):
    description: str
    quantity: float = 1
    unit_price: float

    @field_validator("description")
    @classmethod
    def description_valid(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("La description ne peut pas être vide.")
        return cleaned

    @field_validator("quantity")
    @classmethod
    def quantity_positive(cls, value: float) -> float:
        if value <= 0:
            raise ValueError("La quantité doit être supérieure à zéro.")
        return value

    @field_validator("unit_price")
    @classmethod
    def unit_price_non_negative(cls, value: float) -> float:
        if value < 0:
            raise ValueError("Le prix unitaire ne peut pas être négatif.")
        return value


class InvoiceCreate(BaseModel):
    client_id: str
    invoice_number: str
    currency: str = "XOF"
    issue_date: date
    due_date: date
    items: list[InvoiceItemCreate]

    @field_validator("invoice_number")
    @classmethod
    def number_valid(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("Le numéro de facture ne peut pas être vide.")
        return cleaned

    @field_validator("items")
    @classmethod
    def items_not_empty(cls, value: list[InvoiceItemCreate]) -> list[InvoiceItemCreate]:
        if not value:
            raise ValueError("La facture doit contenir au moins un article.")
        return value

    @model_validator(mode="after")
    def due_after_issue(self):
        if self.due_date < self.issue_date:
            raise ValueError("La date d'échéance ne peut pas précéder la date d'émission.")
        return self


class InvoiceItemOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    description: str
    quantity: float
    unit_price: float


class InvoiceOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    company_id: str
    client_id: str
    invoice_number: str
    status: str
    currency: str
    issue_date: date
    due_date: date
    items: list[InvoiceItemOut] = []
    total_amount: float = 0
    created_at: datetime
    updated_at: datetime


class InvoiceStatusUpdate(BaseModel):
    status: str

    @field_validator("status")
    @classmethod
    def status_valid(cls, value: str) -> str:
        if value not in INVOICE_STATUSES:
            raise ValueError(f"Statut invalide. Statuts valides : {', '.join(sorted(INVOICE_STATUSES))}.")
        return value


class CompanyDashboard(BaseModel):
    company_id: str
    company_name: str
    total_employees: int
    active_employees: int
    total_clients: int
    total_invoiced: float
    total_paid: float
    total_outstanding: float
    invoices_overdue_count: int
