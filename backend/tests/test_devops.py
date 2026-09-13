"""
Tests du module DevOps/Cloud. Nécessitent : pip install -r requirements.txt
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


RESOURCE = {"name": "Cluster API Nexus", "resource_type": "cluster_kubernetes", "provider": "aws", "region": "eu-west-3"}


def test_create_resource():
    token = _register_and_login("devops1@example.com")
    response = client.post("/devops/resources", json=RESOURCE, headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 201
    assert response.json()["status"] == "actif"


def test_resource_isolated_between_users():
    token_a = _register_and_login("devops2@example.com")
    token_b = _register_and_login("devops3@example.com")
    resource = client.post(
        "/devops/resources", json=RESOURCE, headers={"Authorization": f"Bearer {token_a}"}
    ).json()
    response = client.get(
        f"/devops/resources/{resource['id']}", headers={"Authorization": f"Bearer {token_b}"}
    )
    assert response.status_code == 404


def test_deployment_status_workflow():
    token = _register_and_login("devops4@example.com")
    headers = {"Authorization": f"Bearer {token}"}
    resource = client.post("/devops/resources", json=RESOURCE, headers=headers).json()

    deployment = client.post(
        f"/devops/resources/{resource['id']}/deployments",
        json={"version_tag": "v1.0.0", "environment": "production", "commit_reference": "a1b2c3d"},
        headers=headers,
    ).json()
    assert deployment["status"] == "en_attente"

    invalid = client.patch(
        f"/devops/deployments/{deployment['id']}/status", json={"status": "reussi"}, headers=headers
    )
    assert invalid.status_code == 400

    started = client.patch(
        f"/devops/deployments/{deployment['id']}/status", json={"status": "en_cours"}, headers=headers
    )
    assert started.status_code == 200

    finished = client.patch(
        f"/devops/deployments/{deployment['id']}/status", json={"status": "echoue"}, headers=headers
    )
    assert finished.json()["status"] == "echoue"
    assert finished.json()["finished_at"] is not None


def test_rollback_marks_original_deployment_cancelled():
    token = _register_and_login("devops5@example.com")
    headers = {"Authorization": f"Bearer {token}"}
    resource = client.post("/devops/resources", json=RESOURCE, headers=headers).json()

    original = client.post(
        f"/devops/resources/{resource['id']}/deployments",
        json={"version_tag": "v1.1.0", "environment": "production"},
        headers=headers,
    ).json()
    client.patch(f"/devops/deployments/{original['id']}/status", json={"status": "en_cours"}, headers=headers)
    client.patch(f"/devops/deployments/{original['id']}/status", json={"status": "reussi"}, headers=headers)

    rollback = client.post(
        f"/devops/deployments/{original['id']}/rollback",
        json={"version_tag": "v1.0.9-rollback", "environment": "production"},
        headers=headers,
    )
    assert rollback.status_code == 201
    assert rollback.json()["rollback_of_id"] == original["id"]

    original_after = client.get(
        f"/devops/resources/{resource['id']}/deployments", headers=headers
    ).json()
    original_updated = next(d for d in original_after if d["id"] == original["id"])
    assert original_updated["status"] == "annule_par_rollback"


def test_alert_lifecycle_and_dashboard():
    token = _register_and_login("devops6@example.com")
    headers = {"Authorization": f"Bearer {token}"}
    resource = client.post("/devops/resources", json=RESOURCE, headers=headers).json()

    alert = client.post(
        f"/devops/resources/{resource['id']}/alerts",
        json={"severity": "critique", "message": "Utilisation CPU à 98% depuis 10 minutes."},
        headers=headers,
    ).json()
    assert alert["status"] == "ouverte"

    dashboard_before = client.get("/devops/dashboard", headers=headers).json()
    assert dashboard_before["open_alerts_by_severity"]["critique"] == 1

    client.patch(f"/devops/alerts/{alert['id']}/status", json={"status": "resolue"}, headers=headers)

    dashboard_after = client.get("/devops/dashboard", headers=headers).json()
    assert dashboard_after["open_alerts_by_severity"].get("critique", 0) == 0


def test_invalid_resource_type_or_provider_rejected():
    token = _register_and_login("devops7@example.com")
    response = client.post(
        "/devops/resources",
        json={**RESOURCE, "resource_type": ""},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 422


def test_invalid_environment_rejected():
    token = _register_and_login("devops8@example.com")
    headers = {"Authorization": f"Bearer {token}"}
    resource = client.post("/devops/resources", json=RESOURCE, headers=headers).json()
    response = client.post(
        f"/devops/resources/{resource['id']}/deployments",
        json={"version_tag": "v1.0.0", "environment": "environnement_invente"},
        headers=headers,
    )
    assert response.status_code == 422
