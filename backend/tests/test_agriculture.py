"""
Tests du module Agriculture. Nécessitent : pip install -r requirements.txt
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


FIELD = {
    "name": "Parcelle Nord",
    "area_hectares": 3.5,
    "soil_type": "argilo-sableux",
    "country": "Cameroun",
    "region": "Centre",
}


def test_create_field():
    token = _register_and_login("agri1@example.com")
    response = client.post("/agriculture/fields", json=FIELD, headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 201
    assert response.json()["area_hectares"] == 3.5


def test_negative_area_rejected():
    token = _register_and_login("agri2@example.com")
    response = client.post(
        "/agriculture/fields",
        json={**FIELD, "area_hectares": -1},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 422


def test_field_isolated_between_users():
    token_a = _register_and_login("agri3@example.com")
    token_b = _register_and_login("agri4@example.com")
    field = client.post(
        "/agriculture/fields", json=FIELD, headers={"Authorization": f"Bearer {token_a}"}
    ).json()

    response = client.get(f"/agriculture/fields/{field['id']}", headers={"Authorization": f"Bearer {token_b}"})
    assert response.status_code == 404


def test_full_crop_cycle_lifecycle():
    token = _register_and_login("agri5@example.com")
    headers = {"Authorization": f"Bearer {token}"}
    field = client.post("/agriculture/fields", json=FIELD, headers=headers).json()

    cycle = client.post(
        f"/agriculture/fields/{field['id']}/crop-cycles",
        json={"crop_name": "Maïs", "planting_date": "2026-03-01", "expected_harvest_date": "2026-07-01"},
        headers=headers,
    ).json()
    assert cycle["status"] == "planifie"

    started = client.post(f"/agriculture/crop-cycles/{cycle['id']}/start-growing", headers=headers)
    assert started.json()["status"] == "en_croissance"

    harvested = client.post(
        f"/agriculture/crop-cycles/{cycle['id']}/harvest",
        json={"actual_harvest_date": "2026-07-10", "yield_amount": 4200, "yield_unit": "kg"},
        headers=headers,
    )
    assert harvested.status_code == 200
    assert harvested.json()["status"] == "recolte"
    assert harvested.json()["yield_amount"] == 4200


def test_cannot_harvest_before_planting_date():
    token = _register_and_login("agri6@example.com")
    headers = {"Authorization": f"Bearer {token}"}
    field = client.post("/agriculture/fields", json=FIELD, headers=headers).json()
    cycle = client.post(
        f"/agriculture/fields/{field['id']}/crop-cycles",
        json={"crop_name": "Manioc", "planting_date": "2026-05-01"},
        headers=headers,
    ).json()

    response = client.post(
        f"/agriculture/crop-cycles/{cycle['id']}/harvest",
        json={"actual_harvest_date": "2026-04-01", "yield_amount": 100, "yield_unit": "kg"},
        headers=headers,
    )
    assert response.status_code == 400


def test_cannot_re_harvest_already_harvested_cycle():
    token = _register_and_login("agri7@example.com")
    headers = {"Authorization": f"Bearer {token}"}
    field = client.post("/agriculture/fields", json=FIELD, headers=headers).json()
    cycle = client.post(
        f"/agriculture/fields/{field['id']}/crop-cycles",
        json={"crop_name": "Arachide", "planting_date": "2026-01-01"},
        headers=headers,
    ).json()
    client.post(
        f"/agriculture/crop-cycles/{cycle['id']}/harvest",
        json={"actual_harvest_date": "2026-05-01", "yield_amount": 500, "yield_unit": "kg"},
        headers=headers,
    )
    second_attempt = client.post(
        f"/agriculture/crop-cycles/{cycle['id']}/harvest",
        json={"actual_harvest_date": "2026-06-01", "yield_amount": 600, "yield_unit": "kg"},
        headers=headers,
    )
    assert second_attempt.status_code == 400


def test_add_activity_and_yield_summary():
    token = _register_and_login("agri8@example.com")
    headers = {"Authorization": f"Bearer {token}"}
    field = client.post("/agriculture/fields", json=FIELD, headers=headers).json()
    cycle = client.post(
        f"/agriculture/fields/{field['id']}/crop-cycles",
        json={"crop_name": "Tomate", "planting_date": "2026-02-01"},
        headers=headers,
    ).json()

    activity = client.post(
        f"/agriculture/crop-cycles/{cycle['id']}/activities",
        json={
            "activity_type": "fertilisation",
            "activity_date": "2026-02-15",
            "cost_amount": 25000,
            "cost_currency": "XOF",
        },
        headers=headers,
    )
    assert activity.status_code == 201

    client.post(
        f"/agriculture/crop-cycles/{cycle['id']}/harvest",
        json={"actual_harvest_date": "2026-05-01", "yield_amount": 800, "yield_unit": "kg"},
        headers=headers,
    )

    summary = client.get(f"/agriculture/fields/{field['id']}/yield-summary", headers=headers).json()
    assert summary["total_cycles"] == 1
    assert summary["harvested_cycles"] == 1
    assert summary["total_yield_by_unit"]["kg"] == 800
    assert summary["total_cost"] == 25000


def test_invalid_activity_type_rejected():
    token = _register_and_login("agri9@example.com")
    headers = {"Authorization": f"Bearer {token}"}
    field = client.post("/agriculture/fields", json=FIELD, headers=headers).json()
    cycle = client.post(
        f"/agriculture/fields/{field['id']}/crop-cycles",
        json={"crop_name": "Café", "planting_date": "2026-01-01"},
        headers=headers,
    ).json()
    response = client.post(
        f"/agriculture/crop-cycles/{cycle['id']}/activities",
        json={"activity_type": "type_invente", "activity_date": "2026-01-10"},
        headers=headers,
    )
    assert response.status_code == 422
