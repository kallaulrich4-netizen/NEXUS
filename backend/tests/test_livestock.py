"""
Tests du module Élevage. Nécessitent : pip install -r requirements.txt
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


HERD = {
    "name": "Troupeau Ndama Nord",
    "species": "bovins",
    "breed": "Ndama",
    "current_count": 25,
    "country": "Cameroun",
    "region": "Adamaoua",
}


def test_create_herd():
    token = _register_and_login("eleveur1@example.com")
    response = client.post("/livestock/herds", json=HERD, headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 201
    assert response.json()["current_count"] == 25


def test_species_is_free_text_not_restricted():
    """Le champ espèce accepte n'importe quelle valeur, pas seulement la liste suggérée."""
    token = _register_and_login("eleveur2@example.com")
    response = client.post(
        "/livestock/herds",
        json={**HERD, "species": "grillons comestibles", "name": "Élevage d'insectes"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 201
    assert response.json()["species"] == "grillons comestibles"


def test_species_suggestions_endpoint_returns_list():
    response = client.get("/livestock/species/suggestions")
    assert response.status_code == 200
    suggestions = response.json()
    assert "bovins" in suggestions
    assert "abeilles" in suggestions
    assert "poissons" in suggestions


def test_negative_count_rejected():
    token = _register_and_login("eleveur3@example.com")
    response = client.post(
        "/livestock/herds",
        json={**HERD, "current_count": -5},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 422


def test_health_event_adjusts_herd_count():
    token = _register_and_login("eleveur4@example.com")
    headers = {"Authorization": f"Bearer {token}"}
    herd = client.post("/livestock/herds", json=HERD, headers=headers).json()

    birth = client.post(
        f"/livestock/herds/{herd['id']}/health-events",
        json={"event_type": "naissance", "event_date": "2026-03-01", "count_change": 3},
        headers=headers,
    )
    assert birth.status_code == 201

    updated_herd = client.get(f"/livestock/herds/{herd['id']}", headers=headers).json()
    assert updated_herd["current_count"] == 28

    death = client.post(
        f"/livestock/herds/{herd['id']}/health-events",
        json={"event_type": "deces", "event_date": "2026-04-01", "count_change": -2},
        headers=headers,
    )
    assert death.status_code == 201
    final_herd = client.get(f"/livestock/herds/{herd['id']}", headers=headers).json()
    assert final_herd["current_count"] == 26


def test_herd_count_never_goes_negative():
    token = _register_and_login("eleveur5@example.com")
    headers = {"Authorization": f"Bearer {token}"}
    herd = client.post(
        "/livestock/herds", json={**HERD, "current_count": 2}, headers=headers
    ).json()

    client.post(
        f"/livestock/herds/{herd['id']}/health-events",
        json={"event_type": "deces", "event_date": "2026-01-01", "count_change": -10},
        headers=headers,
    )
    updated_herd = client.get(f"/livestock/herds/{herd['id']}", headers=headers).json()
    assert updated_herd["current_count"] == 0


def test_invalid_health_event_type_rejected():
    token = _register_and_login("eleveur6@example.com")
    headers = {"Authorization": f"Bearer {token}"}
    herd = client.post("/livestock/herds", json=HERD, headers=headers).json()
    response = client.post(
        f"/livestock/herds/{herd['id']}/health-events",
        json={"event_type": "type_invente", "event_date": "2026-01-01"},
        headers=headers,
    )
    assert response.status_code == 422


def test_production_record_and_summary():
    token = _register_and_login("eleveur7@example.com")
    headers = {"Authorization": f"Bearer {token}"}
    herd = client.post("/livestock/herds", json=HERD, headers=headers).json()

    client.post(
        f"/livestock/herds/{herd['id']}/production-records",
        json={"product_type": "lait", "quantity": 120, "unit": "litres", "record_date": "2026-03-01"},
        headers=headers,
    )
    client.post(
        f"/livestock/herds/{herd['id']}/production-records",
        json={"product_type": "lait", "quantity": 100, "unit": "litres", "record_date": "2026-03-02"},
        headers=headers,
    )
    client.post(
        f"/livestock/herds/{herd['id']}/health-events",
        json={
            "event_type": "vaccination",
            "event_date": "2026-03-05",
            "cost_amount": 15000,
            "cost_currency": "XOF",
        },
        headers=headers,
    )

    summary = client.get(f"/livestock/herds/{herd['id']}/summary", headers=headers).json()
    assert summary["total_production_by_type"]["lait"] == 220
    assert summary["total_health_cost"] == 15000
    assert summary["total_health_events"] == 1


def test_herd_isolated_between_users():
    token_a = _register_and_login("eleveur8@example.com")
    token_b = _register_and_login("eleveur9@example.com")
    herd = client.post("/livestock/herds", json=HERD, headers={"Authorization": f"Bearer {token_a}"}).json()

    response = client.get(f"/livestock/herds/{herd['id']}", headers={"Authorization": f"Bearer {token_b}"})
    assert response.status_code == 404
