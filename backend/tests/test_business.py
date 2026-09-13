"""
Tests du module Gestion d'entreprise. Nécessitent : pip install -r requirements.txt
Lancer avec : pytest tests/ -v
"""
import os

os.environ.setdefault("SECRET_KEY", "test-secret-key-not-for-production")

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.database import Base, get_db
from app.core.rate_limit import _limiter
from app.main import app

TEST_ENGINE = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
TestSessionLocal = sessionmaker(bind=TEST_ENGINE)


def override_get_db():
    db = TestSessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture(autouse=True)
def setup_database():
    Base.metadata.create_all(bind=TEST_ENGINE)
    _limiter._hits.clear()
    yield
    Base.metadata.drop_all(bind=TEST_ENGINE)


app.dependency_overrides[get_db] = override_get_db
client = TestClient(app)


def _register_and_login(email: str) -> str:
    user = {"email": email, "password": "MotDePasse123", "full_name": f"Utilisateur {email}"}
    client.post("/auth/register", json=user)
    login = client.post("/auth/login", json={"email": email, "password": user["password"]})
    return login.json()["access_token"]


COMPANY = {"name": "Teranga Services", "sector": "logistique", "country": "Sénégal", "city": "Dakar"}


def test_create_company():
    token = _register_and_login("patron1@example.com")
    response = client.post("/business/companies", json=COMPANY, headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 201
    assert response.json()["sector"] == "logistique"


def test_company_isolated_between_users():
    token_a = _register_and_login("patron2@example.com")
    token_b = _register_and_login("patron3@example.com")
    company = client.post(
        "/business/companies", json=COMPANY, headers={"Authorization": f"Bearer {token_a}"}
    ).json()
    response = client.get(
        f"/business/companies/{company['id']}", headers={"Authorization": f"Bearer {token_b}"}
    )
    assert response.status_code == 404


def test_add_employee():
    token = _register_and_login("patron4@example.com")
    headers = {"Authorization": f"Bearer {token}"}
    company = client.post("/business/companies", json=COMPANY, headers=headers).json()
    response = client.post(
        f"/business/companies/{company['id']}/employees",
        json={"full_name": "Awa Ndiaye", "role": "Comptable", "monthly_salary": 250000, "hire_date": "2025-01-15"},
        headers=headers,
    )
    assert response.status_code == 201
    assert response.json()["status"] == "actif"


def test_negative_salary_rejected():
    token = _register_and_login("patron5@example.com")
    headers = {"Authorization": f"Bearer {token}"}
    company = client.post("/business/companies", json=COMPANY, headers=headers).json()
    response = client.post(
        f"/business/companies/{company['id']}/employees",
        json={"full_name": "Test", "role": "Test", "monthly_salary": -1000, "hire_date": "2025-01-01"},
        headers=headers,
    )
    assert response.status_code == 422


def test_invoice_creation_and_total_calculation():
    token = _register_and_login("patron6@example.com")
    headers = {"Authorization": f"Bearer {token}"}
    company = client.post("/business/companies", json=COMPANY, headers=headers).json()
    biz_client = client.post(
        f"/business/companies/{company['id']}/clients",
        json={"name": "Client Alpha SARL"},
        headers=headers,
    ).json()

    invoice = client.post(
        f"/business/companies/{company['id']}/invoices",
        json={
            "client_id": biz_client["id"],
            "invoice_number": "FAC-2026-001",
            "issue_date": "2026-01-10",
            "due_date": "2026-02-10",
            "items": [
                {"description": "Transport de marchandises", "quantity": 2, "unit_price": 50000},
                {"description": "Frais de manutention", "quantity": 1, "unit_price": 15000},
            ],
        },
        headers=headers,
    )
    assert invoice.status_code == 201
    assert invoice.json()["total_amount"] == 115000
    assert invoice.json()["status"] == "brouillon"


def test_duplicate_invoice_number_rejected():
    token = _register_and_login("patron7@example.com")
    headers = {"Authorization": f"Bearer {token}"}
    company = client.post("/business/companies", json=COMPANY, headers=headers).json()
    biz_client = client.post(
        f"/business/companies/{company['id']}/clients", json={"name": "Client Beta"}, headers=headers
    ).json()
    invoice_payload = {
        "client_id": biz_client["id"],
        "invoice_number": "FAC-DUPLIQUE",
        "issue_date": "2026-01-10",
        "due_date": "2026-02-10",
        "items": [{"description": "Service", "quantity": 1, "unit_price": 10000}],
    }
    client.post(f"/business/companies/{company['id']}/invoices", json=invoice_payload, headers=headers)
    second = client.post(f"/business/companies/{company['id']}/invoices", json=invoice_payload, headers=headers)
    assert second.status_code == 409


def test_invoice_status_workflow():
    token = _register_and_login("patron8@example.com")
    headers = {"Authorization": f"Bearer {token}"}
    company = client.post("/business/companies", json=COMPANY, headers=headers).json()
    biz_client = client.post(
        f"/business/companies/{company['id']}/clients", json={"name": "Client Gamma"}, headers=headers
    ).json()
    invoice = client.post(
        f"/business/companies/{company['id']}/invoices",
        json={
            "client_id": biz_client["id"], "invoice_number": "FAC-002",
            "issue_date": "2026-01-01", "due_date": "2026-01-31",
            "items": [{"description": "Service", "quantity": 1, "unit_price": 20000}],
        },
        headers=headers,
    ).json()

    # Impossible de passer directement de "brouillon" à "payee".
    invalid = client.patch(
        f"/business/invoices/{invoice['id']}/status", json={"status": "payee"}, headers=headers
    )
    assert invalid.status_code == 400

    sent = client.patch(
        f"/business/invoices/{invoice['id']}/status", json={"status": "envoyee"}, headers=headers
    )
    assert sent.status_code == 200

    paid = client.patch(
        f"/business/invoices/{invoice['id']}/status", json={"status": "payee"}, headers=headers
    )
    assert paid.status_code == 200
    assert paid.json()["status"] == "payee"


def test_dashboard_aggregates_correctly():
    token = _register_and_login("patron9@example.com")
    headers = {"Authorization": f"Bearer {token}"}
    company = client.post("/business/companies", json=COMPANY, headers=headers).json()

    client.post(
        f"/business/companies/{company['id']}/employees",
        json={"full_name": "Employé 1", "role": "Vendeur", "hire_date": "2025-01-01"},
        headers=headers,
    )
    client.post(
        f"/business/companies/{company['id']}/clients", json={"name": "Client Delta"}, headers=headers
    )
    biz_client = client.get(f"/business/companies/{company['id']}/clients", headers=headers).json()[0]

    invoice = client.post(
        f"/business/companies/{company['id']}/invoices",
        json={
            "client_id": biz_client["id"], "invoice_number": "FAC-003",
            "issue_date": "2026-01-01", "due_date": "2026-01-31",
            "items": [{"description": "Service", "quantity": 1, "unit_price": 30000}],
        },
        headers=headers,
    ).json()
    client.patch(f"/business/invoices/{invoice['id']}/status", json={"status": "envoyee"}, headers=headers)

    dashboard = client.get(f"/business/companies/{company['id']}/dashboard", headers=headers).json()
    assert dashboard["total_employees"] == 1
    assert dashboard["total_clients"] == 1
    assert dashboard["total_outstanding"] == 30000
