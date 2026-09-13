from collections import defaultdict
from datetime import date, timedelta

from sqlalchemy.orm import Session

from app.modules.finance.models import Account, Transaction, Budget, FinancialTip


class AccountNotFoundError(Exception):
    """Levée quand un compte n'existe pas ou n'appartient pas à l'utilisateur."""


class TransactionNotFoundError(Exception):
    """Levée quand une transaction n'existe pas ou n'appartient pas à l'utilisateur."""


class BudgetNotFoundError(Exception):
    """Levée quand un budget n'existe pas ou n'appartient pas à l'utilisateur."""


# --- Comptes ---

def create_account(db: Session, owner_id: str, data) -> Account:
    account = Account(owner_id=owner_id, **data.model_dump())
    db.add(account)
    db.commit()
    db.refresh(account)
    return account


def get_account(db: Session, account_id: str, owner_id: str) -> Account:
    account = db.query(Account).filter(Account.id == account_id, Account.owner_id == owner_id).first()
    if account is None:
        raise AccountNotFoundError("Compte introuvable.")
    return account


def list_accounts(db: Session, owner_id: str) -> list[Account]:
    return db.query(Account).filter(Account.owner_id == owner_id).order_by(Account.created_at.desc()).all()


def delete_account(db: Session, account_id: str, owner_id: str) -> None:
    account = get_account(db, account_id, owner_id)
    db.delete(account)
    db.commit()


def get_account_balance(db: Session, account_id: str, owner_id: str) -> dict:
    account = get_account(db, account_id, owner_id)
    transactions = db.query(Transaction).filter(Transaction.account_id == account_id).all()

    total_income = sum(float(t.amount) for t in transactions if t.transaction_type == "revenu")
    total_expense = sum(float(t.amount) for t in transactions if t.transaction_type == "depense")
    current_balance = float(account.initial_balance) + total_income - total_expense

    return {
        "id": account.id,
        "owner_id": account.owner_id,
        "name": account.name,
        "account_type": account.account_type,
        "currency": account.currency,
        "initial_balance": account.initial_balance,
        "created_at": account.created_at,
        "updated_at": account.updated_at,
        "current_balance": current_balance,
        "total_income": total_income,
        "total_expense": total_expense,
    }


# --- Transactions ---

def create_transaction(db: Session, owner_id: str, data) -> Transaction:
    get_account(db, data.account_id, owner_id)  # vérifie que le compte appartient bien à l'utilisateur
    transaction = Transaction(owner_id=owner_id, **data.model_dump())
    db.add(transaction)
    db.commit()
    db.refresh(transaction)
    return transaction


def get_transaction(db: Session, transaction_id: str, owner_id: str) -> Transaction:
    transaction = (
        db.query(Transaction)
        .filter(Transaction.id == transaction_id, Transaction.owner_id == owner_id)
        .first()
    )
    if transaction is None:
        raise TransactionNotFoundError("Transaction introuvable.")
    return transaction


def list_transactions(
    db: Session,
    owner_id: str,
    account_id: str | None = None,
    category: str | None = None,
    start_date: date | None = None,
    end_date: date | None = None,
    limit: int = 50,
    offset: int = 0,
) -> list[Transaction]:
    q = db.query(Transaction).filter(Transaction.owner_id == owner_id)
    if account_id:
        q = q.filter(Transaction.account_id == account_id)
    if category:
        q = q.filter(Transaction.category == category)
    if start_date:
        q = q.filter(Transaction.transaction_date >= start_date)
    if end_date:
        q = q.filter(Transaction.transaction_date <= end_date)
    return q.order_by(Transaction.transaction_date.desc()).offset(offset).limit(limit).all()


def delete_transaction(db: Session, transaction_id: str, owner_id: str) -> None:
    transaction = get_transaction(db, transaction_id, owner_id)
    db.delete(transaction)
    db.commit()


# --- Budgets ---

def create_budget(db: Session, owner_id: str, data) -> Budget:
    budget = Budget(owner_id=owner_id, **data.model_dump())
    db.add(budget)
    db.commit()
    db.refresh(budget)
    return budget


def get_budget(db: Session, budget_id: str, owner_id: str) -> Budget:
    budget = db.query(Budget).filter(Budget.id == budget_id, Budget.owner_id == owner_id).first()
    if budget is None:
        raise BudgetNotFoundError("Budget introuvable.")
    return budget


def list_budgets(db: Session, owner_id: str) -> list[Budget]:
    return db.query(Budget).filter(Budget.owner_id == owner_id).order_by(Budget.period_start.desc()).all()


def get_budget_status(db: Session, budget_id: str, owner_id: str) -> dict:
    budget = get_budget(db, budget_id, owner_id)
    spent = (
        db.query(Transaction)
        .filter(
            Transaction.owner_id == owner_id,
            Transaction.category == budget.category,
            Transaction.transaction_type == "depense",
            Transaction.transaction_date >= budget.period_start,
            Transaction.transaction_date <= budget.period_end,
        )
        .all()
    )
    spent_amount = sum(float(t.amount) for t in spent)
    remaining = float(budget.limit_amount) - spent_amount

    return {
        "budget": budget,
        "spent_amount": spent_amount,
        "remaining_amount": remaining,
        "is_over_budget": spent_amount > float(budget.limit_amount),
    }


# --- Analyses ---

def get_cashflow_summary(db: Session, owner_id: str, start_date: date, end_date: date) -> dict:
    """
    Résumé de trésorerie sur une période : c'est ce qui alimente les
    tableaux de bord et les analyses de rentabilité de la vision.
    """
    transactions = (
        db.query(Transaction)
        .filter(
            Transaction.owner_id == owner_id,
            Transaction.transaction_date >= start_date,
            Transaction.transaction_date <= end_date,
        )
        .all()
    )

    income_by_category: dict[str, float] = defaultdict(float)
    expense_by_category: dict[str, float] = defaultdict(float)

    for t in transactions:
        amount = float(t.amount)
        if t.transaction_type == "revenu":
            income_by_category[t.category] += amount
        else:
            expense_by_category[t.category] += amount

    total_income = sum(income_by_category.values())
    total_expense = sum(expense_by_category.values())

    return {
        "period_start": start_date,
        "period_end": end_date,
        "total_income": total_income,
        "total_expense": total_expense,
        "net_cashflow": total_income - total_expense,
        "income_by_category": dict(income_by_category),
        "expense_by_category": dict(expense_by_category),
    }


# --- Éducation financière : observations factuelles (jamais des recommandations) ---

INSIGHT_ATTENTION_THRESHOLD_PERCENT = 20.0


def generate_financial_insights(db: Session, owner_id: str, start_date: date, end_date: date) -> dict:
    """
    Compare la période demandée à la période précédente de même durée,
    et signale les catégories dont la dépense a significativement
    augmenté. Ce sont des CONSTATS calculés, jamais des recommandations
    ("vous devriez..."). Le taux d'épargne est un simple ratio calculé
    sur les vrais revenus/dépenses de l'utilisateur.
    """
    period_length = (end_date - start_date).days + 1
    previous_end = start_date - timedelta(days=1)
    previous_start = previous_end - timedelta(days=period_length - 1)

    current = get_cashflow_summary(db, owner_id, start_date, end_date)
    previous = get_cashflow_summary(db, owner_id, previous_start, previous_end)

    insights = []
    for category, current_amount in current["expense_by_category"].items():
        previous_amount = previous["expense_by_category"].get(category, 0.0)
        if previous_amount > 0:
            change_percent = ((current_amount - previous_amount) / previous_amount) * 100
        elif current_amount > 0:
            change_percent = 100.0
        else:
            change_percent = 0.0

        if change_percent >= INSIGHT_ATTENTION_THRESHOLD_PERCENT:
            insights.append(
                {
                    "category": category,
                    "severity": "attention",
                    "message": (
                        f"Vos dépenses en « {category} » ont augmenté de {change_percent:.0f}% "
                        f"par rapport à la période précédente équivalente."
                    ),
                    "current_period_amount": current_amount,
                    "previous_period_amount": previous_amount,
                    "change_percent": round(change_percent, 1),
                }
            )

    if current["total_income"] > 0:
        savings_rate = (current["net_cashflow"] / current["total_income"]) * 100
        insights.append(
            {
                "category": "epargne",
                "severity": "info",
                "message": f"Votre taux d'épargne sur cette période est de {savings_rate:.0f}% de vos revenus.",
                "current_period_amount": current["net_cashflow"],
                "previous_period_amount": None,
                "change_percent": None,
            }
        )
    else:
        savings_rate = None

    return {
        "period_start": start_date,
        "period_end": end_date,
        "savings_rate_percent": round(savings_rate, 1) if savings_rate is not None else None,
        "insights": insights,
    }


# --- Contenu éducatif (littératie financière) ---

def submit_financial_tip(db: Session, author_id: str, data) -> FinancialTip:
    tip = FinancialTip(author_id=author_id, is_reviewed=False, is_published=False, **data.model_dump())
    db.add(tip)
    db.commit()
    db.refresh(tip)
    return tip


class TipNotFoundError(Exception):
    """Levée quand un contenu éducatif n'existe pas ou n'est pas publié."""


def get_published_tip(db: Session, tip_id: str) -> FinancialTip:
    tip = db.query(FinancialTip).filter(FinancialTip.id == tip_id, FinancialTip.is_published.is_(True)).first()
    if tip is None:
        raise TipNotFoundError("Contenu éducatif introuvable ou non publié.")
    return tip


def search_published_tips(
    db: Session, category: str | None = None, limit: int = 20, offset: int = 0
) -> list[FinancialTip]:
    q = db.query(FinancialTip).filter(FinancialTip.is_published.is_(True))
    if category:
        q = q.filter(FinancialTip.category == category)
    return q.order_by(FinancialTip.updated_at.desc()).offset(offset).limit(limit).all()
