"""
Tests du module Cybersécurité. Nécessitent : pip install -r requirements.txt
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


ASSET = {
    "name": "Site vitrine Nexus",
    "asset_type": "site_web",
    "identifier": "https://exemple-nexus.com",
    "description": "Site web principal de présentation.",
}


def test_create_asset():
    token = _register_and_login("secu1@example.com")
    response = client.post("/cybersecurity/assets", json=ASSET, headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 201


def test_invalid_asset_type_rejected():
    token = _register_and_login("secu2@example.com")
    response = client.post(
        "/cybersecurity/assets",
        json={**ASSET, "asset_type": "type_invente"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 422


def test_audit_requires_ownership_confirmation():
    token = _register_and_login("secu3@example.com")
    headers = {"Authorization": f"Bearer {token}"}
    asset = client.post("/cybersecurity/assets", json=ASSET, headers=headers).json()

    response = client.post(
        f"/cybersecurity/assets/{asset['id']}/audits",
        json={"ownership_confirmed": False},
        headers=headers,
    )
    assert response.status_code == 422


def test_audit_created_with_confirmation():
    token = _register_and_login("secu4@example.com")
    headers = {"Authorization": f"Bearer {token}"}
    asset = client.post("/cybersecurity/assets", json=ASSET, headers=headers).json()

    response = client.post(
        f"/cybersecurity/assets/{asset['id']}/audits",
        json={"ownership_confirmed": True, "scheduled_date": "2026-08-01"},
        headers=headers,
    )
    assert response.status_code == 201
    assert response.json()["status"] == "demande"


def test_asset_isolated_between_users():
    token_a = _register_and_login("secu5@example.com")
    token_b = _register_and_login("secu6@example.com")
    asset = client.post(
        "/cybersecurity/assets", json=ASSET, headers={"Authorization": f"Bearer {token_a}"}
    ).json()
    response = client.post(
        f"/cybersecurity/assets/{asset['id']}/audits",
        json={"ownership_confirmed": True},
        headers={"Authorization": f"Bearer {token_b}"},
    )
    assert response.status_code == 404


def test_add_finding_and_risk_dashboard():
    token = _register_and_login("secu7@example.com")
    headers = {"Authorization": f"Bearer {token}"}
    asset = client.post("/cybersecurity/assets", json=ASSET, headers=headers).json()
    audit = client.post(
        f"/cybersecurity/assets/{asset['id']}/audits",
        json={"ownership_confirmed": True},
        headers=headers,
    ).json()

    finding = client.post(
        f"/cybersecurity/audits/{audit['id']}/findings",
        json={
            "title": "En-têtes de sécurité HTTP manquants",
            "severity": "moyenne",
            "description": "Le site ne renvoie pas d'en-tête X-Frame-Options.",
            "remediation_advice": "Ajouter les en-têtes de sécurité standards au serveur web.",
        },
        headers=headers,
    )
    assert finding.status_code == 201

    dashboard = client.get(f"/cybersecurity/assets/{asset['id']}/risk-dashboard", headers=headers).json()
    assert dashboard["total_findings"] == 1
    assert dashboard["open_findings_by_severity"]["moyenne"] == 1


def test_finding_status_update():
    token = _register_and_login("secu8@example.com")
    headers = {"Authorization": f"Bearer {token}"}
    asset = client.post("/cybersecurity/assets", json=ASSET, headers=headers).json()
    audit = client.post(
        f"/cybersecurity/assets/{asset['id']}/audits", json={"ownership_confirmed": True}, headers=headers
    ).json()
    finding = client.post(
        f"/cybersecurity/audits/{audit['id']}/findings",
        json={
            "title": "Mot de passe par défaut",
            "severity": "critique",
            "description": "Le compte administrateur utilise encore le mot de passe par défaut.",
            "remediation_advice": "Changer immédiatement le mot de passe administrateur.",
        },
        headers=headers,
    ).json()

    updated = client.patch(
        f"/cybersecurity/findings/{finding['id']}/status", json={"status": "corrige"}, headers=headers
    )
    assert updated.json()["status"] == "corrige"

    dashboard = client.get(f"/cybersecurity/assets/{asset['id']}/risk-dashboard", headers=headers).json()
    assert dashboard["critical_open_count"] == 0  # corrigé, donc plus compté comme ouvert


def test_security_guide_not_published_by_default():
    token = _register_and_login("secu9@example.com")
    response = client.post(
        "/cybersecurity/guides",
        json={
            "title": "Bonnes pratiques d'authentification multi-facteurs",
            "category": "authentification",
            "summary": "Pourquoi et comment activer le MFA sur vos comptes professionnels.",
            "content": "L'authentification multi-facteurs réduit drastiquement le risque de "
            "compromission de compte, même en cas de fuite de mot de passe. Elle devrait être "
            "activée sur tous les comptes ayant accès à des données sensibles.",
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 201
    assert response.json()["is_published"] is False
