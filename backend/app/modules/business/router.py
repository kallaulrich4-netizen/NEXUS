from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.rate_limit import rate_limit
from app.core.exports import ExportDocument, ExportSection, export_to_pdf, export_to_word
from app.modules.auth.router import get_current_user
from app.modules.auth.models import User
from app.modules.business import service
from app.modules.business.schemas import (
    CompanyCreate, CompanyUpdate, CompanyOut, CompanyDashboard,
    EmployeeCreate, EmployeeOut, EmployeeStatusUpdate,
    ClientCreate, ClientOut,
    InvoiceCreate, InvoiceOut, InvoiceStatusUpdate,
)

router = APIRouter(prefix="/business", tags=["Gestion d'entreprise"])

EXPORT_MEDIA_TYPES = {
    "pdf": "application/pdf",
    "word": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
}


# --- Entreprises ---

@router.post(
    "/companies",
    response_model=CompanyOut,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(rate_limit(max_requests=10, window_seconds=60))],
)
def create_company(
    data: CompanyCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return service.create_company(db, current_user.id, data)


@router.get("/companies", response_model=list[CompanyOut])
def list_companies(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return service.list_companies(db, current_user.id)


@router.get("/companies/{company_id}", response_model=CompanyOut)
def get_company(
    company_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        return service.get_company(db, company_id, current_user.id)
    except service.CompanyNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))


@router.patch("/companies/{company_id}", response_model=CompanyOut)
def update_company(
    company_id: str,
    data: CompanyUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        return service.update_company(db, company_id, current_user.id, data)
    except service.CompanyNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))


@router.delete("/companies/{company_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_company(
    company_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        service.delete_company(db, company_id, current_user.id)
    except service.CompanyNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))


@router.get("/companies/{company_id}/dashboard", response_model=CompanyDashboard)
def get_company_dashboard(
    company_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        return service.get_company_dashboard(db, company_id, current_user.id)
    except service.CompanyNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))


# --- Employés ---

@router.post(
    "/companies/{company_id}/employees",
    response_model=EmployeeOut,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(rate_limit(max_requests=30, window_seconds=60))],
)
def add_employee(
    company_id: str,
    data: EmployeeCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        return service.add_employee(db, company_id, current_user.id, data)
    except service.CompanyNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))


@router.get("/companies/{company_id}/employees", response_model=list[EmployeeOut])
def list_employees(
    company_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        return service.list_employees(db, company_id, current_user.id)
    except service.CompanyNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))


@router.patch("/employees/{employee_id}/status", response_model=EmployeeOut)
def update_employee_status(
    employee_id: str,
    data: EmployeeStatusUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        return service.update_employee_status(db, employee_id, current_user.id, data.status)
    except service.EmployeeNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))


# --- Clients ---

@router.post(
    "/companies/{company_id}/clients",
    response_model=ClientOut,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(rate_limit(max_requests=30, window_seconds=60))],
)
def add_client(
    company_id: str,
    data: ClientCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        return service.add_client(db, company_id, current_user.id, data)
    except service.CompanyNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))


@router.get("/companies/{company_id}/clients", response_model=list[ClientOut])
def list_clients(
    company_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        return service.list_clients(db, company_id, current_user.id)
    except service.CompanyNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))


# --- Factures ---

@router.post(
    "/companies/{company_id}/invoices",
    response_model=InvoiceOut,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(rate_limit(max_requests=20, window_seconds=60))],
)
def create_invoice(
    company_id: str,
    data: InvoiceCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        return service.create_invoice(db, company_id, current_user.id, data)
    except service.CompanyNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    except service.ClientNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    except service.DuplicateInvoiceNumberError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))


@router.get("/companies/{company_id}/invoices", response_model=list[InvoiceOut])
def list_invoices(
    company_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        return service.list_invoices(db, company_id, current_user.id)
    except service.CompanyNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))


@router.get("/invoices/{invoice_id}", response_model=InvoiceOut)
def get_invoice(
    invoice_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        return service.get_invoice(db, invoice_id, current_user.id)
    except service.InvoiceNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))


@router.get("/invoices/{invoice_id}/export")
def export_invoice(
    invoice_id: str,
    file_format: str = Query("pdf", pattern="^(pdf|word)$"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Exporte une facture en PDF ou Word, prête à envoyer à un client."""
    try:
        invoice = service.get_invoice(db, invoice_id, current_user.id)
        company = service.get_company(db, invoice["company_id"], current_user.id)
    except service.InvoiceNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    except service.CompanyNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))

    item_rows = [
        [item.description, str(item.quantity), f"{item.unit_price:,.2f} {invoice['currency']}"]
        for item in invoice["items"]
    ]

    document = ExportDocument(
        title=f"Facture {invoice['invoice_number']}",
        subtitle=company.name,
        sections=[
            ExportSection(
                heading="Détails",
                paragraphs=[
                    f"Date d'émission : {invoice['issue_date'].isoformat()}",
                    f"Date d'échéance : {invoice['due_date'].isoformat()}",
                    f"Statut : {invoice['status']}",
                ],
            ),
            ExportSection(
                heading="Articles",
                table_headers=["Description", "Quantité", "Prix unitaire"],
                table_rows=item_rows,
            ),
            ExportSection(
                heading="Total",
                paragraphs=[f"Montant total : {invoice['total_amount']:,.2f} {invoice['currency']}"],
            ),
        ],
    )

    filename = f"facture_{invoice['invoice_number']}"
    if file_format == "pdf":
        content = export_to_pdf(document)
        filename += ".pdf"
    else:
        content = export_to_word(document)
        filename += ".docx"

    return Response(
        content=content,
        media_type=EXPORT_MEDIA_TYPES[file_format],
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.patch("/invoices/{invoice_id}/status", response_model=InvoiceOut)
def update_invoice_status(
    invoice_id: str,
    data: InvoiceStatusUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        return service.update_invoice_status(db, invoice_id, current_user.id, data.status)
    except service.InvoiceNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    except service.InvalidInvoiceTransitionError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
