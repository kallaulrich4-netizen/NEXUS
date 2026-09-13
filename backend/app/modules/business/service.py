from datetime import date

from sqlalchemy.orm import Session, joinedload

from app.modules.business.models import Company, Employee, BusinessClient, Invoice, InvoiceItem


class CompanyNotFoundError(Exception):
    """Levée quand une entreprise n'existe pas ou n'appartient pas à l'utilisateur."""


class EmployeeNotFoundError(Exception):
    """Levée quand un employé n'existe pas ou n'appartient pas à une entreprise de l'utilisateur."""


class ClientNotFoundError(Exception):
    """Levée quand un client n'existe pas ou n'appartient pas à une entreprise de l'utilisateur."""


class InvoiceNotFoundError(Exception):
    """Levée quand une facture n'existe pas ou n'appartient pas à une entreprise de l'utilisateur."""


class DuplicateInvoiceNumberError(Exception):
    """Levée quand un numéro de facture est déjà utilisé pour cette entreprise."""


class InvalidInvoiceTransitionError(Exception):
    """Levée quand un changement de statut de facture n'est pas cohérent."""


# --- Entreprises ---

def create_company(db: Session, owner_id: str, data) -> Company:
    company = Company(owner_id=owner_id, **data.model_dump())
    db.add(company)
    db.commit()
    db.refresh(company)
    return company


def get_company(db: Session, company_id: str, owner_id: str) -> Company:
    company = db.query(Company).filter(Company.id == company_id, Company.owner_id == owner_id).first()
    if company is None:
        raise CompanyNotFoundError("Entreprise introuvable.")
    return company


def list_companies(db: Session, owner_id: str) -> list[Company]:
    return db.query(Company).filter(Company.owner_id == owner_id).order_by(Company.created_at.desc()).all()


def update_company(db: Session, company_id: str, owner_id: str, data) -> Company:
    company = get_company(db, company_id, owner_id)
    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(company, key, value)
    db.commit()
    db.refresh(company)
    return company


def delete_company(db: Session, company_id: str, owner_id: str) -> None:
    company = get_company(db, company_id, owner_id)
    db.delete(company)
    db.commit()


# --- Employés ---

def add_employee(db: Session, company_id: str, owner_id: str, data) -> Employee:
    get_company(db, company_id, owner_id)
    employee = Employee(company_id=company_id, status="actif", **data.model_dump())
    db.add(employee)
    db.commit()
    db.refresh(employee)
    return employee


def list_employees(db: Session, company_id: str, owner_id: str) -> list[Employee]:
    get_company(db, company_id, owner_id)
    return db.query(Employee).filter(Employee.company_id == company_id).order_by(Employee.hire_date.desc()).all()


def _get_employee_for_owner(db: Session, employee_id: str, owner_id: str) -> Employee:
    employee = (
        db.query(Employee)
        .join(Company)
        .filter(Employee.id == employee_id, Company.owner_id == owner_id)
        .first()
    )
    if employee is None:
        raise EmployeeNotFoundError("Employé introuvable.")
    return employee


def update_employee_status(db: Session, employee_id: str, owner_id: str, new_status: str) -> Employee:
    employee = _get_employee_for_owner(db, employee_id, owner_id)
    employee.status = new_status
    db.commit()
    db.refresh(employee)
    return employee


# --- Clients ---

def add_client(db: Session, company_id: str, owner_id: str, data) -> BusinessClient:
    get_company(db, company_id, owner_id)
    biz_client = BusinessClient(company_id=company_id, **data.model_dump())
    db.add(biz_client)
    db.commit()
    db.refresh(biz_client)
    return biz_client


def list_clients(db: Session, company_id: str, owner_id: str) -> list[BusinessClient]:
    get_company(db, company_id, owner_id)
    return (
        db.query(BusinessClient)
        .filter(BusinessClient.company_id == company_id)
        .order_by(BusinessClient.created_at.desc())
        .all()
    )


def _get_client_for_owner(db: Session, client_id: str, owner_id: str) -> BusinessClient:
    biz_client = (
        db.query(BusinessClient)
        .join(Company)
        .filter(BusinessClient.id == client_id, Company.owner_id == owner_id)
        .first()
    )
    if biz_client is None:
        raise ClientNotFoundError("Client introuvable.")
    return biz_client


# --- Factures ---

def _invoice_total(invoice: Invoice) -> float:
    return sum(float(item.quantity) * float(item.unit_price) for item in invoice.items)


def _to_invoice_out_dict(invoice: Invoice) -> dict:
    return {
        "id": invoice.id,
        "company_id": invoice.company_id,
        "client_id": invoice.client_id,
        "invoice_number": invoice.invoice_number,
        "status": invoice.status,
        "currency": invoice.currency,
        "issue_date": invoice.issue_date,
        "due_date": invoice.due_date,
        "items": invoice.items,
        "total_amount": _invoice_total(invoice),
        "created_at": invoice.created_at,
        "updated_at": invoice.updated_at,
    }


def create_invoice(db: Session, company_id: str, owner_id: str, data) -> dict:
    get_company(db, company_id, owner_id)
    _get_client_for_owner(db, data.client_id, owner_id)

    existing = (
        db.query(Invoice)
        .filter(Invoice.company_id == company_id, Invoice.invoice_number == data.invoice_number)
        .first()
    )
    if existing is not None:
        raise DuplicateInvoiceNumberError(
            f"Le numéro de facture « {data.invoice_number} » est déjà utilisé pour cette entreprise."
        )

    items_data = data.model_dump()["items"]
    invoice = Invoice(
        company_id=company_id,
        client_id=data.client_id,
        invoice_number=data.invoice_number,
        currency=data.currency,
        issue_date=data.issue_date,
        due_date=data.due_date,
        status="brouillon",
        items=[InvoiceItem(**item) for item in items_data],
    )
    db.add(invoice)
    db.commit()
    db.refresh(invoice)
    return _to_invoice_out_dict(invoice)


def _get_invoice_for_owner(db: Session, invoice_id: str, owner_id: str) -> Invoice:
    invoice = (
        db.query(Invoice)
        .join(Company)
        .options(joinedload(Invoice.items))
        .filter(Invoice.id == invoice_id, Company.owner_id == owner_id)
        .first()
    )
    if invoice is None:
        raise InvoiceNotFoundError("Facture introuvable.")
    return invoice


def get_invoice(db: Session, invoice_id: str, owner_id: str) -> dict:
    invoice = _get_invoice_for_owner(db, invoice_id, owner_id)
    return _to_invoice_out_dict(invoice)


def list_invoices(db: Session, company_id: str, owner_id: str) -> list[dict]:
    get_company(db, company_id, owner_id)
    invoices = (
        db.query(Invoice)
        .options(joinedload(Invoice.items))
        .filter(Invoice.company_id == company_id)
        .order_by(Invoice.issue_date.desc())
        .all()
    )
    return [_to_invoice_out_dict(inv) for inv in invoices]


_VALID_INVOICE_TRANSITIONS = {
    "brouillon": {"envoyee", "annulee"},
    "envoyee": {"payee", "en_retard", "annulee"},
    "en_retard": {"payee", "annulee"},
    "payee": set(),
    "annulee": set(),
}


def update_invoice_status(db: Session, invoice_id: str, owner_id: str, new_status: str) -> dict:
    invoice = _get_invoice_for_owner(db, invoice_id, owner_id)
    if new_status not in _VALID_INVOICE_TRANSITIONS.get(invoice.status, set()):
        raise InvalidInvoiceTransitionError(
            f"Transition de statut invalide : « {invoice.status} » -> « {new_status} »."
        )
    invoice.status = new_status
    db.commit()
    db.refresh(invoice)
    return _to_invoice_out_dict(invoice)


# --- Tableau de bord ---

def get_company_dashboard(db: Session, company_id: str, owner_id: str) -> dict:
    company = get_company(db, company_id, owner_id)

    employees = db.query(Employee).filter(Employee.company_id == company_id).all()
    active_employees = [e for e in employees if e.status == "actif"]

    clients_count = db.query(BusinessClient).filter(BusinessClient.company_id == company_id).count()

    invoices = (
        db.query(Invoice)
        .options(joinedload(Invoice.items))
        .filter(Invoice.company_id == company_id)
        .all()
    )
    total_invoiced = sum(_invoice_total(inv) for inv in invoices if inv.status != "annulee")
    total_paid = sum(_invoice_total(inv) for inv in invoices if inv.status == "payee")
    total_outstanding = sum(
        _invoice_total(inv) for inv in invoices if inv.status in {"envoyee", "en_retard"}
    )
    overdue_count = sum(1 for inv in invoices if inv.status == "en_retard")

    return {
        "company_id": company.id,
        "company_name": company.name,
        "total_employees": len(employees),
        "active_employees": len(active_employees),
        "total_clients": clients_count,
        "total_invoiced": total_invoiced,
        "total_paid": total_paid,
        "total_outstanding": total_outstanding,
        "invoices_overdue_count": overdue_count,
    }
