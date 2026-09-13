"""
Tests d'intégration des endpoints d'export de documents.
Nécessitent : pip install -r requirements.txt
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


def test_export_cashflow_as_pdf():
    token = _register_and_login("export1@example.com")
    headers = {"Authorization": f"Bearer {token}"}
    account = client.post(
        "/finance/accounts", json={"name": "Compte", "currency": "XOF"}, headers=headers
    ).json()
    client.post(
        "/finance/transactions",
        json={
            "account_id": account["id"], "transaction_type": "revenu", "category": "salaire",
            "amount": 100000, "transaction_date": "2026-06-05",
        },
        headers=headers,
    )
    response = client.get(
        "/finance/cashflow/export",
        params={"start_date": "2026-06-01", "end_date": "2026-06-30", "file_format": "pdf"},
        headers=headers,
    )
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/pdf"
    assert response.content.startswith(b"%PDF")


def test_export_cashflow_as_excel():
    token = _register_and_login("export2@example.com")
    headers = {"Authorization": f"Bearer {token}"}
    response = client.get(
        "/finance/cashflow/export",
        params={"start_date": "2026-06-01", "end_date": "2026-06-30", "file_format": "excel"},
        headers=headers,
    )
    assert response.status_code == 200
    assert "spreadsheetml" in response.headers["content-type"]


def test_export_invoice_as_pdf():
    token = _register_and_login("export3@example.com")
    headers = {"Authorization": f"Bearer {token}"}
    company = client.post(
        "/business/companies",
        json={"name": "Export SARL", "sector": "commerce", "country": "Sénégal"},
        headers=headers,
    ).json()
    biz_client = client.post(
        f"/business/companies/{company['id']}/clients", json={"name": "Client Export"}, headers=headers
    ).json()
    invoice = client.post(
        f"/business/companies/{company['id']}/invoices",
        json={
            "client_id": biz_client["id"], "invoice_number": "FAC-EXPORT-001",
            "issue_date": "2026-01-01", "due_date": "2026-01-31",
            "items": [{"description": "Service de conseil", "quantity": 1, "unit_price": 50000}],
        },
        headers=headers,
    ).json()

    response = client.get(
        f"/business/invoices/{invoice['id']}/export", params={"file_format": "pdf"}, headers=headers
    )
    assert response.status_code == 200
    assert response.content.startswith(b"%PDF")


def test_export_invoice_as_word():
    token = _register_and_login("export4@example.com")
    headers = {"Authorization": f"Bearer {token}"}
    company = client.post(
        "/business/companies",
        json={"name": "Export Word SARL", "sector": "commerce", "country": "Sénégal"},
        headers=headers,
    ).json()
    biz_client = client.post(
        f"/business/companies/{company['id']}/clients", json={"name": "Client Word"}, headers=headers
    ).json()
    invoice = client.post(
        f"/business/companies/{company['id']}/invoices",
        json={
            "client_id": biz_client["id"], "invoice_number": "FAC-EXPORT-002",
            "issue_date": "2026-01-01", "due_date": "2026-01-31",
            "items": [{"description": "Service", "quantity": 2, "unit_price": 10000}],
        },
        headers=headers,
    ).json()

    response = client.get(
        f"/business/invoices/{invoice['id']}/export", params={"file_format": "word"}, headers=headers
    )
    assert response.status_code == 200
    assert response.content[:2] == b"PK"


def test_cannot_export_another_users_invoice():
    token_a = _register_and_login("export5@example.com")
    token_b = _register_and_login("export6@example.com")
    company = client.post(
        "/business/companies",
        json={"name": "Privée SARL", "sector": "commerce", "country": "Sénégal"},
        headers={"Authorization": f"Bearer {token_a}"},
    ).json()
    biz_client = client.post(
        f"/business/companies/{company['id']}/clients",
        json={"name": "Client Privé"},
        headers={"Authorization": f"Bearer {token_a}"},
    ).json()
    invoice = client.post(
        f"/business/companies/{company['id']}/invoices",
        json={
            "client_id": biz_client["id"], "invoice_number": "FAC-PRIVEE",
            "issue_date": "2026-01-01", "due_date": "2026-01-31",
            "items": [{"description": "Service", "quantity": 1, "unit_price": 1000}],
        },
        headers={"Authorization": f"Bearer {token_a}"},
    ).json()

    response = client.get(
        f"/business/invoices/{invoice['id']}/export",
        params={"file_format": "pdf"},
        headers={"Authorization": f"Bearer {token_b}"},
    )
    assert response.status_code == 404
