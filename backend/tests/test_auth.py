"""
Tests du module auth. Nécessitent : pip install -r requirements.txt
Lancer avec : pytest tests/ -v
"""
import os

os.environ.setdefault("SECRET_KEY", "test-secret-key-not-for-production")
os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

from app.core.database import Base, get_db
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
    yield
    Base.metadata.drop_all(bind=TEST_ENGINE)


app.dependency_overrides[get_db] = override_get_db
client = TestClient(app)

VALID_USER = {
    "email": "marie@example.com",
    "password": "MotDePasse123",
    "full_name": "Marie Curie",
    "preferred_language": "fr",
    "country": "France",
}


def test_register_creates_user():
    response = client.post("/auth/register", json=VALID_USER)
    assert response.status_code == 201
    body = response.json()
    assert body["email"] == VALID_USER["email"]
    assert "hashed_password" not in body  # le mot de passe haché ne doit JAMAIS être exposé


def test_register_rejects_duplicate_email():
    client.post("/auth/register", json=VALID_USER)
    response = client.post("/auth/register", json=VALID_USER)
    assert response.status_code == 409


def test_register_rejects_weak_password():
    weak = {**VALID_USER, "password": "1234"}
    response = client.post("/auth/register", json=weak)
    assert response.status_code == 422


def test_login_returns_tokens():
    client.post("/auth/register", json=VALID_USER)
    response = client.post(
        "/auth/login", json={"email": VALID_USER["email"], "password": VALID_USER["password"]}
    )
    assert response.status_code == 200
    body = response.json()
    assert "access_token" in body
    assert "refresh_token" in body


def test_login_rejects_wrong_password():
    client.post("/auth/register", json=VALID_USER)
    response = client.post(
        "/auth/login", json={"email": VALID_USER["email"], "password": "MauvaisMotDePasse1"}
    )
    assert response.status_code == 401


def test_me_requires_authentication():
    response = client.get("/auth/me")
    assert response.status_code == 401


def test_me_returns_current_user_with_valid_token():
    client.post("/auth/register", json=VALID_USER)
    login_response = client.post(
        "/auth/login", json={"email": VALID_USER["email"], "password": VALID_USER["password"]}
    )
    token = login_response.json()["access_token"]
    response = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    assert response.json()["email"] == VALID_USER["email"]


def _register_and_get_token(email: str) -> str:
    user = {**VALID_USER, "email": email}
    client.post("/auth/register", json=user)
    login = client.post("/auth/login", json={"email": email, "password": user["password"]})
    return login.json()["access_token"]


def test_update_profile_changes_allowed_fields():
    token = _register_and_get_token("profile1@example.com")
    response = client.patch(
        "/auth/me",
        json={"full_name": "Nouveau Nom", "preferred_language": "en"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["full_name"] == "Nouveau Nom"
    assert body["preferred_language"] == "en"


def test_update_profile_requires_authentication():
    response = client.patch("/auth/me", json={"full_name": "Test"})
    assert response.status_code == 401


def test_change_password_succeeds_with_correct_current_password():
    email = "profile2@example.com"
    token = _register_and_get_token(email)
    response = client.post(
        "/auth/me/change-password",
        json={"current_password": VALID_USER["password"], "new_password": "NouveauMotDePasse123"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 204

    # L'ancien mot de passe ne fonctionne plus, le nouveau si.
    old_login = client.post("/auth/login", json={"email": email, "password": VALID_USER["password"]})
    assert old_login.status_code == 401
    new_login = client.post("/auth/login", json={"email": email, "password": "NouveauMotDePasse123"})
    assert new_login.status_code == 200


def test_change_password_rejects_incorrect_current_password():
    token = _register_and_get_token("profile3@example.com")
    response = client.post(
        "/auth/me/change-password",
        json={"current_password": "MotDePasseIncorrect1", "new_password": "NouveauMotDePasse123"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 401


def test_deactivate_account_prevents_further_login():
    email = "profile4@example.com"
    token = _register_and_get_token(email)
    response = client.delete("/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 204

    login = client.post("/auth/login", json={"email": email, "password": VALID_USER["password"]})
    assert login.status_code == 401
