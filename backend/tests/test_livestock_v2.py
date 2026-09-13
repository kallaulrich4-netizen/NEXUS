"""
Tests des fonctionnalités Élevage V2. Nécessitent : pip install -r requirements.txt
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


def _create_herd(token: str, species="bovins", current_count=5) -> dict:
    herd = {"name": "Troupeau Test", "species": species, "current_count": current_count, "country": "Cameroun"}
    return client.post("/livestock/herds", json=herd, headers={"Authorization": f"Bearer {token}"}).json()


def _create_animal(token: str, herd_id: str, tag="A-001", sex="femelle") -> dict:
    animal = {"tag": tag, "sex": sex, "birth_date": "2024-01-01"}
    return client.post(
        f"/livestock/herds/{herd_id}/animals", json=animal, headers={"Authorization": f"Bearer {token}"}
    ).json()


def test_create_and_list_animals():
    token = _register_and_login("elevagev2_1@example.com")
    herd = _create_herd(token)
    headers = {"Authorization": f"Bearer {token}"}

    created = client.post(f"/livestock/herds/{herd['id']}/animals", json={"tag": "A-001"}, headers=headers)
    assert created.status_code == 201
    assert created.json()["status"] == "vivant"

    listed = client.get(f"/livestock/herds/{herd['id']}/animals", headers=headers)
    assert listed.status_code == 200
    assert len(listed.json()) == 1


def test_animal_not_found_for_other_owner():
    token = _register_and_login("elevagev2_2@example.com")
    other_token = _register_and_login("elevagev2_2b@example.com")
    herd = _create_herd(token)
    animal = _create_animal(token, herd["id"])

    response = client.get(f"/livestock/animals/{animal['id']}", headers={"Authorization": f"Bearer {other_token}"})
    assert response.status_code == 404


def test_update_animal_status():
    token = _register_and_login("elevagev2_3@example.com")
    herd = _create_herd(token)
    animal = _create_animal(token, herd["id"])
    headers = {"Authorization": f"Bearer {token}"}

    response = client.patch(f"/livestock/animals/{animal['id']}", json={"status": "vendu"}, headers=headers)
    assert response.status_code == 200
    assert response.json()["status"] == "vendu"


def test_add_animal_health_record():
    token = _register_and_login("elevagev2_4@example.com")
    herd = _create_herd(token)
    animal = _create_animal(token, herd["id"])
    headers = {"Authorization": f"Bearer {token}"}

    response = client.post(
        f"/livestock/animals/{animal['id']}/health-records",
        json={"record_type": "vaccination", "record_date": "2026-01-15", "cost_amount": 2000},
        headers=headers,
    )
    assert response.status_code == 201
    assert response.json()["record_type"] == "vaccination"


def test_growth_summary_computes_gain_and_average_daily_gain():
    token = _register_and_login("elevagev2_5@example.com")
    herd = _create_herd(token)
    animal = _create_animal(token, herd["id"])
    headers = {"Authorization": f"Bearer {token}"}

    client.post(
        f"/livestock/animals/{animal['id']}/weight-records",
        json={"weight_kg": 100, "measured_at": "2026-01-01"},
        headers=headers,
    )
    client.post(
        f"/livestock/animals/{animal['id']}/weight-records",
        json={"weight_kg": 120, "measured_at": "2026-01-11"},
        headers=headers,
    )

    response = client.get(f"/livestock/animals/{animal['id']}/growth-summary", headers=headers)
    assert response.status_code == 200
    body = response.json()
    assert body["first_weight_kg"] == 100
    assert body["latest_weight_kg"] == 120
    assert body["total_gain_kg"] == 20
    assert round(body["average_daily_gain_kg"], 1) == 2.0


def test_declare_birth_creates_offspring_and_increments_herd_count():
    token = _register_and_login("elevagev2_6@example.com")
    herd = _create_herd(token, current_count=5)
    mother = _create_animal(token, herd["id"], tag="MERE-001", sex="femelle")
    headers = {"Authorization": f"Bearer {token}"}

    response = client.post(
        f"/livestock/animals/{mother['id']}/declare-birth",
        json={"event_date": "2026-02-01", "offspring_count": 2, "offspring_sex": "inconnu"},
        headers=headers,
    )
    assert response.status_code == 201
    body = response.json()
    assert len(body["offspring"]) == 2
    assert all(a["parent_id"] == mother["id"] for a in body["offspring"])

    updated_herd = client.get(f"/livestock/herds/{herd['id']}", headers=headers).json()
    assert updated_herd["current_count"] == 7


def test_generate_feed_plan_scales_with_current_count():
    token = _register_and_login("elevagev2_7@example.com")
    herd = _create_herd(token, species="bovins", current_count=10)
    headers = {"Authorization": f"Bearer {token}"}

    response = client.post(f"/livestock/herds/{herd['id']}/feed-plan", json={}, headers=headers)
    assert response.status_code == 201
    body = response.json()
    assert body["daily_quantity_kg"] > 0
    assert body["estimated_daily_cost"] > 0


def test_herd_economics_reflects_costs_and_sales():
    token = _register_and_login("elevagev2_8@example.com")
    herd = _create_herd(token, current_count=3)
    animal = _create_animal(token, herd["id"])
    headers = {"Authorization": f"Bearer {token}"}

    client.post(
        f"/livestock/animals/{animal['id']}/health-records",
        json={"record_type": "traitement", "record_date": "2026-01-01", "cost_amount": 5000},
        headers=headers,
    )
    client.patch(f"/livestock/animals/{animal['id']}", json={"status": "vendu"}, headers=headers)

    response = client.get(f"/livestock/herds/{herd['id']}/economics", headers=headers)
    assert response.status_code == 200
    body = response.json()
    assert body["total_cost"] >= 5000
    assert body["total_revenue_from_sales"] > 0
