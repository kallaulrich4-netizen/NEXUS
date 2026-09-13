from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.rate_limit import rate_limit
from app.core.exports import ExportDocument, ExportSection, export_to_pdf, export_to_excel
from app.modules.auth.router import get_current_user
from app.modules.auth.models import User
from app.modules.finance import service
from app.modules.finance.schemas import (
    AccountCreate, AccountOut, AccountBalance,
    TransactionCreate, TransactionOut,
    BudgetCreate, BudgetOut, BudgetStatus,
    CashflowSummary, FinancialInsightsResponse,
    FinancialTipCreate, FinancialTipOut, FinancialTipListOut,
)

router = APIRouter(prefix="/finance", tags=["Finance"])

EXPORT_MEDIA_TYPES = {
    "pdf": "application/pdf",
    "excel": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
}


# --- Comptes ---

@router.post(
    "/accounts",
    response_model=AccountOut,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(rate_limit(max_requests=20, window_seconds=60))],
)
def create_account(
    data: AccountCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return service.create_account(db, current_user.id, data)


@router.get("/accounts", response_model=list[AccountOut])
def list_accounts(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return service.list_accounts(db, current_user.id)


@router.get("/accounts/{account_id}/balance", response_model=AccountBalance)
def get_account_balance(
    account_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        return service.get_account_balance(db, account_id, current_user.id)
    except service.AccountNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))


@router.delete("/accounts/{account_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_account(
    account_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        service.delete_account(db, account_id, current_user.id)
    except service.AccountNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))


# --- Transactions ---

@router.post(
    "/transactions",
    response_model=TransactionOut,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(rate_limit(max_requests=60, window_seconds=60))],
)
def create_transaction(
    data: TransactionCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        return service.create_transaction(db, current_user.id, data)
    except service.AccountNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))


@router.get("/transactions", response_model=list[TransactionOut])
def list_transactions(
    account_id: str | None = Query(None),
    category: str | None = Query(None),
    start_date: date | None = Query(None),
    end_date: date | None = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return service.list_transactions(
        db, current_user.id,
        account_id=account_id, category=category,
        start_date=start_date, end_date=end_date,
        limit=limit, offset=offset,
    )


@router.delete("/transactions/{transaction_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_transaction(
    transaction_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        service.delete_transaction(db, transaction_id, current_user.id)
    except service.TransactionNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))


# --- Budgets ---

@router.post(
    "/budgets",
    response_model=BudgetOut,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(rate_limit(max_requests=20, window_seconds=60))],
)
def create_budget(
    data: BudgetCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return service.create_budget(db, current_user.id, data)


@router.get("/budgets", response_model=list[BudgetOut])
def list_budgets(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return service.list_budgets(db, current_user.id)


@router.get("/budgets/{budget_id}/status", response_model=BudgetStatus)
def get_budget_status(
    budget_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        return service.get_budget_status(db, budget_id, current_user.id)
    except service.BudgetNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))


# --- Analyses ---

@router.get("/cashflow", response_model=CashflowSummary)
def get_cashflow_summary(
    start_date: date = Query(...),
    end_date: date = Query(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if end_date < start_date:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="La date de fin ne peut pas précéder la date de début.",
        )
    return service.get_cashflow_summary(db, current_user.id, start_date, end_date)


@router.get("/cashflow/export")
def export_cashflow_summary(
    start_date: date = Query(...),
    end_date: date = Query(...),
    file_format: str = Query("pdf", pattern="^(pdf|excel)$"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Exporte le résumé de trésorerie de la période en PDF ou Excel."""
    if end_date < start_date:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="La date de fin ne peut pas précéder la date de début.",
        )
    summary = service.get_cashflow_summary(db, current_user.id, start_date, end_date)

    income_rows = [[category, f"{amount:,.2f}"] for category, amount in summary["income_by_category"].items()]
    expense_rows = [[category, f"{amount:,.2f}"] for category, amount in summary["expense_by_category"].items()]

    document = ExportDocument(
        title="Résumé de trésorerie — Nexus Finance",
        subtitle=f"Période du {start_date.isoformat()} au {end_date.isoformat()}",
        sections=[
            ExportSection(
                heading="Synthèse",
                paragraphs=[
                    f"Revenus totaux : {summary['total_income']:,.2f}",
                    f"Dépenses totales : {summary['total_expense']:,.2f}",
                    f"Flux net : {summary['net_cashflow']:,.2f}",
                ],
            ),
            ExportSection(
                heading="Revenus par catégorie",
                table_headers=["Catégorie", "Montant"],
                table_rows=income_rows,
            ),
            ExportSection(
                heading="Dépenses par catégorie",
                table_headers=["Catégorie", "Montant"],
                table_rows=expense_rows,
            ),
        ],
    )

    filename = f"tresorerie_{start_date.isoformat()}_{end_date.isoformat()}"
    if file_format == "pdf":
        content = export_to_pdf(document)
        filename += ".pdf"
    else:
        content = export_to_excel(document)
        filename += ".xlsx"

    return Response(
        content=content,
        media_type=EXPORT_MEDIA_TYPES[file_format],
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/insights", response_model=FinancialInsightsResponse)
def get_financial_insights(
    start_date: date = Query(...),
    end_date: date = Query(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Observations factuelles calculées sur les données de l'utilisateur
    (évolution des dépenses par catégorie, taux d'épargne). Ce n'est PAS
    un conseil financier personnalisé — voir le champ `disclaimer` de
    la réponse.
    """
    if end_date < start_date:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="La date de fin ne peut pas précéder la date de début.",
        )
    return service.generate_financial_insights(db, current_user.id, start_date, end_date)


# --- Éducation financière ---

@router.post(
    "/tips",
    response_model=FinancialTipOut,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(rate_limit(max_requests=10, window_seconds=60))],
)
def submit_financial_tip(
    data: FinancialTipCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return service.submit_financial_tip(db, current_user.id, data)


@router.get("/tips/search", response_model=list[FinancialTipListOut])
def search_financial_tips(
    category: str | None = Query(None),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
):
    return service.search_published_tips(db, category=category, limit=limit, offset=offset)


@router.get("/tips/{tip_id}", response_model=FinancialTipOut)
def get_financial_tip(tip_id: str, db: Session = Depends(get_db)):
    try:
        return service.get_published_tip(db, tip_id)
    except service.TipNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
