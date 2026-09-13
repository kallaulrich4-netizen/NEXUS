"""
Tests du module Finance. Nécessitent : pip install -r requirements.txt
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


def test_create_account():
    token = _register_and_login("financier1@example.com")
    response = client.post(
        "/finance/accounts",
        json={"name": "Compte principal", "currency": "XOF", "initial_balance": 100000},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 201
    assert response.json()["initial_balance"] == "100000.00"


def test_account_balance_reflects_transactions():
    token = _register_and_login("financier2@example.com")
    headers = {"Authorization": f"Bearer {token}"}
    account = client.post(
        "/finance/accounts",
        json={"name": "Compte test", "currency": "XOF", "initial_balance": 50000},
        headers=headers,
    ).json()

    client.post(
        "/finance/transactions",
        json={
            "account_id": account["id"],
            "transaction_type": "revenu",
            "category": "salaire",
            "amount": 200000,
            "transaction_date": "2026-01-31",
        },
        headers=headers,
    )
    client.post(
        "/finance/transactions",
        json={
            "account_id": account["id"],
            "transaction_type": "depense",
            "category": "loyer",
            "amount": 75000,
            "transaction_date": "2026-02-01",
        },
        headers=headers,
    )

    balance = client.get(f"/finance/accounts/{account['id']}/balance", headers=headers).json()
    assert balance["total_income"] == 200000
    assert balance["total_expense"] == 75000
    assert balance["current_balance"] == 50000 + 200000 - 75000


def test_negative_amount_rejected():
    token = _register_and_login("financier3@example.com")
    headers = {"Authorization": f"Bearer {token}"}
    account = client.post(
        "/finance/accounts", json={"name": "Compte", "currency": "XOF"}, headers=headers
    ).json()
    response = client.post(
        "/finance/transactions",
        json={
            "account_id": account["id"],
            "transaction_type": "depense",
            "category": "test",
            "amount": -100,
            "transaction_date": "2026-01-01",
        },
        headers=headers,
    )
    assert response.status_code == 422


def test_transaction_requires_own_account():
    token_a = _register_and_login("financier4@example.com")
    token_b = _register_and_login("financier5@example.com")
    account_a = client.post(
        "/finance/accounts", json={"name": "Compte A", "currency": "XOF"},
        headers={"Authorization": f"Bearer {token_a}"},
    ).json()

    response = client.post(
        "/finance/transactions",
        json={
            "account_id": account_a["id"],
            "transaction_type": "depense",
            "category": "test",
            "amount": 1000,
            "transaction_date": "2026-01-01",
        },
        headers={"Authorization": f"Bearer {token_b}"},
    )
    assert response.status_code == 404


def test_budget_status_tracks_spending():
    token = _register_and_login("financier6@example.com")
    headers = {"Authorization": f"Bearer {token}"}
    account = client.post(
        "/finance/accounts", json={"name": "Compte", "currency": "XOF"}, headers=headers
    ).json()

    budget = client.post(
        "/finance/budgets",
        json={
            "category": "alimentation",
            "limit_amount": 100000,
            "currency": "XOF",
            "period_start": "2026-03-01",
            "period_end": "2026-03-31",
        },
        headers=headers,
    ).json()

    client.post(
        "/finance/transactions",
        json={
            "account_id": account["id"],
            "transaction_type": "depense",
            "category": "alimentation",
            "amount": 40000,
            "transaction_date": "2026-03-05",
        },
        headers=headers,
    )
    client.post(
        "/finance/transactions",
        json={
            "account_id": account["id"],
            "transaction_type": "depense",
            "category": "alimentation",
            "amount": 30000,
            "transaction_date": "2026-03-15",
        },
        headers=headers,
    )

    status_response = client.get(f"/finance/budgets/{budget['id']}/status", headers=headers).json()
    assert status_response["spent_amount"] == 70000
    assert status_response["remaining_amount"] == 30000
    assert status_response["is_over_budget"] is False


def test_budget_detects_overspending():
    token = _register_and_login("financier7@example.com")
    headers = {"Authorization": f"Bearer {token}"}
    account = client.post(
        "/finance/accounts", json={"name": "Compte", "currency": "XOF"}, headers=headers
    ).json()
    budget = client.post(
        "/finance/budgets",
        json={
            "category": "transport",
            "limit_amount": 20000,
            "currency": "XOF",
            "period_start": "2026-03-01",
            "period_end": "2026-03-31",
        },
        headers=headers,
    ).json()
    client.post(
        "/finance/transactions",
        json={
            "account_id": account["id"],
            "transaction_type": "depense",
            "category": "transport",
            "amount": 35000,
            "transaction_date": "2026-03-10",
        },
        headers=headers,
    )
    status_response = client.get(f"/finance/budgets/{budget['id']}/status", headers=headers).json()
    assert status_response["is_over_budget"] is True


def test_invalid_budget_period_rejected():
    token = _register_and_login("financier8@example.com")
    response = client.post(
        "/finance/budgets",
        json={
            "category": "loisirs",
            "limit_amount": 10000,
            "currency": "XOF",
            "period_start": "2026-03-31",
            "period_end": "2026-03-01",
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 422


def test_cashflow_summary_groups_by_category():
    token = _register_and_login("financier9@example.com")
    headers = {"Authorization": f"Bearer {token}"}
    account = client.post(
        "/finance/accounts", json={"name": "Compte", "currency": "XOF"}, headers=headers
    ).json()

    client.post(
        "/finance/transactions",
        json={
            "account_id": account["id"], "transaction_type": "revenu", "category": "salaire",
            "amount": 300000, "transaction_date": "2026-04-05",
        },
        headers=headers,
    )
    client.post(
        "/finance/transactions",
        json={
            "account_id": account["id"], "transaction_type": "depense", "category": "loyer",
            "amount": 100000, "transaction_date": "2026-04-06",
        },
        headers=headers,
    )
    client.post(
        "/finance/transactions",
        json={
            "account_id": account["id"], "transaction_type": "depense", "category": "alimentation",
            "amount": 50000, "transaction_date": "2026-04-10",
        },
        headers=headers,
    )

    summary = client.get(
        "/finance/cashflow",
        params={"start_date": "2026-04-01", "end_date": "2026-04-30"},
        headers=headers,
    ).json()

    assert summary["total_income"] == 300000
    assert summary["total_expense"] == 150000
    assert summary["net_cashflow"] == 150000
    assert summary["expense_by_category"]["loyer"] == 100000
    assert summary["expense_by_category"]["alimentation"] == 50000
