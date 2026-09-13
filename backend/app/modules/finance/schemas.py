from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, field_validator, model_validator

from app.modules.finance.models import TRANSACTION_TYPES, FINANCIAL_TIP_CATEGORIES


class AccountCreate(BaseModel):
    name: str
    account_type: str = "general"
    currency: str = "XOF"
    initial_balance: float = 0

    @field_validator("name")
    @classmethod
    def name_valid(cls, value: str) -> str:
        cleaned = value.strip()
        if not (2 <= len(cleaned) <= 255):
            raise ValueError("Le nom du compte doit contenir entre 2 et 255 caractères.")
        return cleaned


class AccountOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    owner_id: str
    name: str
    account_type: str
    currency: str
    initial_balance: float
    created_at: datetime
    updated_at: datetime


class AccountBalance(AccountOut):
    current_balance: float
    total_income: float
    total_expense: float


class TransactionCreate(BaseModel):
    account_id: str
    transaction_type: str
    category: str
    amount: float
    currency: str = "XOF"
    transaction_date: date
    description: str | None = None

    @field_validator("transaction_type")
    @classmethod
    def type_valid(cls, value: str) -> str:
        if value not in TRANSACTION_TYPES:
            raise ValueError(f"Type invalide. Valeurs valides : {', '.join(sorted(TRANSACTION_TYPES))}.")
        return value

    @field_validator("category")
    @classmethod
    def category_valid(cls, value: str) -> str:
        cleaned = value.strip().lower()
        if not (2 <= len(cleaned) <= 100):
            raise ValueError("La catégorie doit contenir entre 2 et 100 caractères.")
        return cleaned

    @field_validator("amount")
    @classmethod
    def amount_positive(cls, value: float) -> float:
        if value <= 0:
            raise ValueError("Le montant doit être supérieur à zéro.")
        return value


class TransactionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    owner_id: str
    account_id: str
    transaction_type: str
    category: str
    amount: float
    currency: str
    transaction_date: date
    description: str | None
    created_at: datetime


class BudgetCreate(BaseModel):
    category: str
    limit_amount: float
    currency: str = "XOF"
    period_start: date
    period_end: date

    @field_validator("category")
    @classmethod
    def category_valid(cls, value: str) -> str:
        cleaned = value.strip().lower()
        if not (2 <= len(cleaned) <= 100):
            raise ValueError("La catégorie doit contenir entre 2 et 100 caractères.")
        return cleaned

    @field_validator("limit_amount")
    @classmethod
    def limit_positive(cls, value: float) -> float:
        if value <= 0:
            raise ValueError("Le plafond budgétaire doit être supérieur à zéro.")
        return value

    @model_validator(mode="after")
    def period_valid(self):
        if self.period_end < self.period_start:
            raise ValueError("La date de fin de période ne peut pas précéder la date de début.")
        return self


class BudgetOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    owner_id: str
    category: str
    limit_amount: float
    currency: str
    period_start: date
    period_end: date
    created_at: datetime


class BudgetStatus(BaseModel):
    budget: BudgetOut
    spent_amount: float
    remaining_amount: float
    is_over_budget: bool


class CashflowSummary(BaseModel):
    period_start: date
    period_end: date
    total_income: float
    total_expense: float
    net_cashflow: float
    income_by_category: dict[str, float]
    expense_by_category: dict[str, float]


class FinancialInsight(BaseModel):
    """
    Une observation FACTUELLE calculée à partir des propres données de
    l'utilisateur — jamais une recommandation d'action ("investissez
    dans X"), toujours un constat vérifiable ("vos dépenses en Y ont
    augmenté de Z% par rapport au mois précédent").
    """
    category: str
    severity: str  # info | attention
    message: str
    current_period_amount: float
    previous_period_amount: float | None = None
    change_percent: float | None = None


class FinancialInsightsResponse(BaseModel):
    period_start: date
    period_end: date
    savings_rate_percent: float | None
    insights: list[FinancialInsight]
    disclaimer: str = (
        "Ces observations sont calculées automatiquement à partir de vos propres données. "
        "Elles ne constituent pas un conseil financier, fiscal ou d'investissement personnalisé. "
        "Pour une décision importante, consultez un professionnel agréé."
    )


class FinancialTipCreate(BaseModel):
    title: str
    category: str
    summary: str
    content: str
    language: str = "fr"

    @field_validator("title")
    @classmethod
    def title_valid(cls, value: str) -> str:
        cleaned = value.strip()
        if not (5 <= len(cleaned) <= 255):
            raise ValueError("Le titre doit contenir entre 5 et 255 caractères.")
        return cleaned

    @field_validator("category")
    @classmethod
    def category_valid(cls, value: str) -> str:
        if value not in FINANCIAL_TIP_CATEGORIES:
            raise ValueError(
                f"Catégorie invalide. Catégories valides : {', '.join(sorted(FINANCIAL_TIP_CATEGORIES))}."
            )
        return value

    @field_validator("summary")
    @classmethod
    def summary_valid(cls, value: str) -> str:
        cleaned = value.strip()
        if not (10 <= len(cleaned) <= 500):
            raise ValueError("Le résumé doit contenir entre 10 et 500 caractères.")
        return cleaned

    @field_validator("content")
    @classmethod
    def content_valid(cls, value: str) -> str:
        cleaned = value.strip()
        if len(cleaned) < 50:
            raise ValueError("Le contenu doit contenir au moins 50 caractères.")
        return cleaned


class FinancialTipOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    author_id: str
    title: str
    category: str
    summary: str
    content: str
    language: str
    is_reviewed: bool
    is_published: bool
    created_at: datetime
    updated_at: datetime


class FinancialTipListOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    title: str
    category: str
    summary: str
    language: str
    created_at: datetime
