"""
Tests des fonctionnalités Agriculture V2. Nécessitent : pip install -r requirements.txt
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


def _create_field(token: str) -> dict:
    field = {
        "name": "Parcelle Test",
        "area_hectares": 2.0,
        "soil_type": "argilo-sableux",
        "country": "Cameroun",
        "region": "Centre",
    }
    return client.post("/agriculture/fields", json=field, headers={"Authorization": f"Bearer {token}"}).json()


def _create_cycle(token: str, field_id: str, crop_name="riz", expected_harvest_date="2026-10-01") -> dict:
    cycle = {"crop_name": crop_name, "planting_date": "2026-07-01", "expected_harvest_date": expected_harvest_date}
    return client.post(
        f"/agriculture/fields/{field_id}/crop-cycles", json=cycle, headers={"Authorization": f"Bearer {token}"}
    ).json()


def test_generate_crop_recommendations_returns_scored_suggestions():
    token = _register_and_login("agriv2_1@example.com")
    field = _create_field(token)
    headers = {"Authorization": f"Bearer {token}"}

    response = client.post(
        f"/agriculture/fields/{field['id']}/recommendations",
        json={"season": "pluies", "budget_amount": 100000, "budget_currency": "XOF"},
        headers=headers,
    )
    assert response.status_code == 201
    body = response.json()
    assert len(body) > 0
    assert all(0 <= item["score"] <= 100 for item in body)
    assert all(item["rationale"] for item in body)


def test_list_crop_recommendations_requires_owner():
    token = _register_and_login("agriv2_2@example.com")
    other_token = _register_and_login("agriv2_2b@example.com")
    field = _create_field(token)

    response = client.get(
        f"/agriculture/fields/{field['id']}/recommendations",
        headers={"Authorization": f"Bearer {other_token}"},
    )
    assert response.status_code == 404


def test_generate_calendar_creates_tasks_including_harvest():
    token = _register_and_login("agriv2_3@example.com")
    field = _create_field(token)
    cycle = _create_cycle(token, field["id"])
    headers = {"Authorization": f"Bearer {token}"}

    response = client.post(f"/agriculture/crop-cycles/{cycle['id']}/calendar", headers=headers)
    assert response.status_code == 200
    tasks = response.json()
    assert len(tasks) > 0
    assert any(t["task_type"] == "recolte" for t in tasks)


def test_update_calendar_task_status():
    token = _register_and_login("agriv2_4@example.com")
    field = _create_field(token)
    cycle = _create_cycle(token, field["id"])
    headers = {"Authorization": f"Bearer {token}"}

    tasks = client.post(f"/agriculture/crop-cycles/{cycle['id']}/calendar", headers=headers).json()
    task_id = tasks[0]["id"]

    response = client.patch(
        f"/agriculture/calendar-tasks/{task_id}", json={"status": "faite"}, headers=headers
    )
    assert response.status_code == 200
    assert response.json()["status"] == "faite"


def test_update_calendar_task_rejects_invalid_status():
    token = _register_and_login("agriv2_5@example.com")
    field = _create_field(token)
    cycle = _create_cycle(token, field["id"])
    headers = {"Authorization": f"Bearer {token}"}

    tasks = client.post(f"/agriculture/crop-cycles/{cycle['id']}/calendar", headers=headers).json()
    task_id = tasks[0]["id"]

    response = client.patch(
        f"/agriculture/calendar-tasks/{task_id}", json={"status": "statut_invalide"}, headers=headers
    )
    assert response.status_code == 422


def test_diagnose_disease_returns_diagnosis_and_recommendations():
    token = _register_and_login("agriv2_6@example.com")
    field = _create_field(token)
    cycle = _create_cycle(token, field["id"])
    headers = {"Authorization": f"Bearer {token}"}

    response = client.post(
        f"/agriculture/crop-cycles/{cycle['id']}/diagnose",
        json={"symptoms_description": "Taches jaunes sur les feuilles et flétrissement."},
        headers=headers,
    )
    assert response.status_code == 201
    body = response.json()
    assert body["diagnosis_text"]
    assert body["recommended_actions"]
    assert body["status"] == "en_analyse"


def test_diagnose_disease_rejects_too_short_description():
    token = _register_and_login("agriv2_7@example.com")
    field = _create_field(token)
    cycle = _create_cycle(token, field["id"])
    headers = {"Authorization": f"Bearer {token}"}

    response = client.post(
        f"/agriculture/crop-cycles/{cycle['id']}/diagnose",
        json={"symptoms_description": "ab"},
        headers=headers,
    )
    assert response.status_code == 422


def test_financial_projection_computes_profit():
    token = _register_and_login("agriv2_8@example.com")
    field = _create_field(token)
    cycle = _create_cycle(token, field["id"])
    headers = {"Authorization": f"Bearer {token}"}

    # Une activité avec un coût réel connu.
    client.post(
        f"/agriculture/crop-cycles/{cycle['id']}/activities",
        json={"activity_type": "fertilisation", "activity_date": "2026-07-10", "cost_amount": 20000},
        headers=headers,
    )

    response = client.post(
        f"/agriculture/fields/{field['id']}/financial-projection",
        json={"crop_cycle_id": cycle["id"], "market_price_per_unit": 300, "currency": "XOF"},
        headers=headers,
    )
    assert response.status_code == 201
    body = response.json()
    assert body["estimated_cost_total"] >= 20000
    assert body["estimated_profit"] == body["estimated_revenue_total"] - body["estimated_cost_total"]


def test_get_financial_projection_returns_latest_or_none():
    token = _register_and_login("agriv2_9@example.com")
    field = _create_field(token)
    headers = {"Authorization": f"Bearer {token}"}

    response = client.get(f"/agriculture/fields/{field['id']}/financial-projection", headers=headers)
    assert response.status_code == 200
    assert response.json() is None


def test_farm_dashboard_aggregates_fields():
    token = _register_and_login("agriv2_10@example.com")
    field = _create_field(token)
    _create_cycle(token, field["id"])
    headers = {"Authorization": f"Bearer {token}"}

    response = client.get("/agriculture/dashboard", headers=headers)
    assert response.status_code == 200
    body = response.json()
    assert body["total_fields"] == 1
    assert body["total_active_cycles"] == 1
    assert len(body["fields"]) == 1
