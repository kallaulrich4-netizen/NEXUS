"""
Tests du statut super-administrateur (accès créateur illimité).
Nécessitent : pip install -r requirements.txt
Lancer avec : pytest tests/ -v
"""
import os

os.environ.setdefault("SECRET_KEY", "test-secret-key-not-for-production")
os.environ["INITIAL_SUPERUSER_EMAIL"] = "createur@nexus-test.com"

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.config import get_settings

get_settings.cache_clear()  # essentiel : force la relecture de INITIAL_SUPERUSER_EMAIL même si un autre test a déjà mis en cache la configuration

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


def test_matching_email_is_promoted_to_superuser_on_registration():
    response = client.post(
        "/auth/register",
        json={
            "email": "createur@nexus-test.com",
            "password": "MotDePasse123",
            "full_name": "Kalla Douglas",
        },
    )
    assert response.status_code == 201
    assert response.json()["is_superuser"] is True


def test_other_emails_are_never_promoted():
    response = client.post(
        "/auth/register",
        json={
            "email": "utilisateur_normal@example.com",
            "password": "MotDePasse123",
            "full_name": "Quelqu'un d'autre",
        },
    )
    assert response.status_code == 201
    assert response.json()["is_superuser"] is False


def test_superuser_has_premium_access_even_after_trial_expires():
    from datetime import datetime, timedelta, timezone
    from app.modules.auth.models import User

    client.post(
        "/auth/register",
        json={
            "email": "createur@nexus-test.com",
            "password": "MotDePasse123",
            "full_name": "Kalla Douglas",
        },
    )
    db = TestSessionLocal()
    user = db.query(User).filter(User.email == "createur@nexus-test.com").first()
    user.trial_ends_at = datetime.now(timezone.utc) - timedelta(days=365)
    db.commit()
    db.close()

    login = client.post(
        "/auth/login", json={"email": "createur@nexus-test.com", "password": "MotDePasse123"}
    )
    token = login.json()["access_token"]

    status_response = client.get(
        "/studio/account/premium-status", headers={"Authorization": f"Bearer {token}"}
    )
    assert status_response.json()["has_premium_access"] is True


def test_superuser_bypasses_rate_limiting():
    client.post(
        "/auth/register",
        json={
            "email": "createur@nexus-test.com",
            "password": "MotDePasse123",
            "full_name": "Kalla Douglas",
        },
    )
    login = client.post(
        "/auth/login", json={"email": "createur@nexus-test.com", "password": "MotDePasse123"}
    )
    token = login.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    for i in range(15):
        response = client.post(
            "/business/companies",
            json={"name": f"Entreprise {i}", "sector": "commerce", "country": "Cameroun"},
            headers=headers,
        )
        assert response.status_code == 201


def test_regular_user_still_rate_limited():
    client.post(
        "/auth/register",
        json={"email": "utilisateur_limite@example.com", "password": "MotDePasse123", "full_name": "Test"},
    )
    login = client.post(
        "/auth/login", json={"email": "utilisateur_limite@example.com", "password": "MotDePasse123"}
    )
    token = login.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    statuses = []
    for i in range(15):
        response = client.post(
            "/business/companies",
            json={"name": f"Entreprise {i}", "sector": "commerce", "country": "Cameroun"},
            headers=headers,
        )
        statuses.append(response.status_code)
    assert 429 in statuses
