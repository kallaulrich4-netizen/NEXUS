"""
Tests des corrections de sécurité : verrouillage de compte (anti brute-force)
et limiteur de débit (anti spam / anti déni de service).
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
    _limiter._hits.clear()  # évite qu'un test pollue le suivant
    yield
    Base.metadata.drop_all(bind=TEST_ENGINE)


app.dependency_overrides[get_db] = override_get_db
client = TestClient(app)

VALID_USER = {
    "email": "victor@example.com",
    "password": "MotDePasse123",
    "full_name": "Victor Hugo",
}


def test_account_locks_after_repeated_failed_logins():
    client.post("/auth/register", json=VALID_USER)

    for _ in range(5):
        response = client.post(
            "/auth/login", json={"email": VALID_USER["email"], "password": "MauvaisMotDePasse1"}
        )
        assert response.status_code == 401

    # Le 6e essai, même avec le bon mot de passe, doit être bloqué : le compte est verrouillé.
    locked_response = client.post(
        "/auth/login", json={"email": VALID_USER["email"], "password": VALID_USER["password"]}
    )
    assert locked_response.status_code == 423


def test_successful_login_resets_failed_attempts():
    client.post("/auth/register", json=VALID_USER)
    client.post("/auth/login", json={"email": VALID_USER["email"], "password": "Mauvais1234"})

    ok_response = client.post(
        "/auth/login", json={"email": VALID_USER["email"], "password": VALID_USER["password"]}
    )
    assert ok_response.status_code == 200


def test_rate_limit_blocks_excessive_registration_attempts():
    for i in range(5):
        client.post(
            "/auth/register",
            json={**VALID_USER, "email": f"user{i}@example.com"},
        )

    # 6e inscription dans la même minute, depuis la même IP de test : doit être limitée.
    response = client.post(
        "/auth/register", json={**VALID_USER, "email": "user6@example.com"}
    )
    assert response.status_code == 429
