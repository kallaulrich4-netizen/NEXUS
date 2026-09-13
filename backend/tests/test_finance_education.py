"""
Tests des insights financiers et du contenu éducatif (module Finance).
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


def test_insights_response_always_includes_disclaimer():
    token = _register_and_login("eleve_finance1@example.com")
    headers = {"Authorization": f"Bearer {token}"}
    response = client.get(
        "/finance/insights",
        params={"start_date": "2026-04-01", "end_date": "2026-04-30"},
        headers=headers,
    )
    assert response.status_code == 200
    body = response.json()
    assert "conseil financier" in body["disclaimer"].lower()


def test_insights_flag_significant_spending_increase():
    token = _register_and_login("eleve_finance2@example.com")
    headers = {"Authorization": f"Bearer {token}"}
    account = client.post(
        "/finance/accounts", json={"name": "Compte", "currency": "XOF"}, headers=headers
    ).json()

    # Période précédente : 10 000 dépensés en "loisirs"
    client.post(
        "/finance/transactions",
        json={
            "account_id": account["id"], "transaction_type": "depense", "category": "loisirs",
            "amount": 10000, "transaction_date": "2026-02-15",
        },
        headers=headers,
    )
    # Période courante : 30 000 dépensés en "loisirs" (+200%)
    client.post(
        "/finance/transactions",
        json={
            "account_id": account["id"], "transaction_type": "depense", "category": "loisirs",
            "amount": 30000, "transaction_date": "2026-03-15",
        },
        headers=headers,
    )

    response = client.get(
        "/finance/insights",
        params={"start_date": "2026-03-01", "end_date": "2026-03-31"},
        headers=headers,
    ).json()

    loisirs_insight = next((i for i in response["insights"] if i["category"] == "loisirs"), None)
    assert loisirs_insight is not None
    assert loisirs_insight["severity"] == "attention"
    assert loisirs_insight["change_percent"] > 100


def test_savings_rate_calculated_from_real_data():
    token = _register_and_login("eleve_finance3@example.com")
    headers = {"Authorization": f"Bearer {token}"}
    account = client.post(
        "/finance/accounts", json={"name": "Compte", "currency": "XOF"}, headers=headers
    ).json()
    client.post(
        "/finance/transactions",
        json={
            "account_id": account["id"], "transaction_type": "revenu", "category": "salaire",
            "amount": 200000, "transaction_date": "2026-05-05",
        },
        headers=headers,
    )
    client.post(
        "/finance/transactions",
        json={
            "account_id": account["id"], "transaction_type": "depense", "category": "loyer",
            "amount": 100000, "transaction_date": "2026-05-06",
        },
        headers=headers,
    )

    response = client.get(
        "/finance/insights",
        params={"start_date": "2026-05-01", "end_date": "2026-05-31"},
        headers=headers,
    ).json()
    # Revenu 200000, dépense 100000 -> épargne nette 100000 -> taux 50%
    assert response["savings_rate_percent"] == 50.0


TIP = {
    "title": "Comprendre le taux d'épargne et pourquoi il compte",
    "category": "epargne",
    "summary": "Une explication simple du taux d'épargne et de son utilité pour la planification.",
    "content": "Le taux d'épargne représente la part de vos revenus que vous mettez de côté plutôt "
    "que de dépenser. Un taux d'épargne régulier, même modeste, permet de constituer un fonds "
    "d'urgence et de préparer des projets à moyen ou long terme.",
}


def test_financial_tip_not_published_by_default():
    token = _register_and_login("educateur1@example.com")
    response = client.post("/finance/tips", json=TIP, headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 201
    assert response.json()["is_published"] is False


def test_unpublished_tip_not_searchable():
    token = _register_and_login("educateur2@example.com")
    client.post("/finance/tips", json=TIP, headers={"Authorization": f"Bearer {token}"})
    results = client.get("/finance/tips/search").json()
    assert len(results) == 0


def test_invalid_tip_category_rejected():
    token = _register_and_login("educateur3@example.com")
    response = client.post(
        "/finance/tips",
        json={**TIP, "category": "categorie_inventee"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 422


def test_short_tip_content_rejected():
    token = _register_and_login("educateur4@example.com")
    response = client.post(
        "/finance/tips",
        json={**TIP, "content": "Trop court."},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 422
