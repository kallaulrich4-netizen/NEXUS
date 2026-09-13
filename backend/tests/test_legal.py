"""
Tests du module Droit. Nécessitent : pip install -r requirements.txt
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


def _register_and_login(email: str) -> tuple[str, str]:
    user = {"email": email, "password": "MotDePasse123", "full_name": f"Utilisateur {email}"}
    client.post("/auth/register", json=user)
    login = client.post("/auth/login", json={"email": email, "password": user["password"]})
    token = login.json()["access_token"]
    me = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
    return token, me.json()["id"]


RESOURCE = {
    "title": "Comprendre la procédure de divorce par consentement mutuel",
    "category": "divorce",
    "summary": "Un aperçu des étapes clés de la procédure de divorce à l'amiable.",
    "content": "Le divorce par consentement mutuel nécessite un accord entre les deux époux sur "
    "l'ensemble des conséquences du divorce, formalisé par une convention soumise à un notaire.",
    "jurisdiction_country": "France",
}


def test_submit_resource_not_published_by_default():
    token, _ = _register_and_login("juriste1@example.com")
    response = client.post("/legal/resources", json=RESOURCE, headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 201
    assert response.json()["is_published"] is False
    assert response.json()["is_reviewed"] is False


def test_unpublished_resource_not_visible_in_search():
    token, _ = _register_and_login("juriste2@example.com")
    client.post("/legal/resources", json=RESOURCE, headers={"Authorization": f"Bearer {token}"})

    results = client.get("/legal/resources/search", params={"country": "France"}).json()
    assert len(results) == 0  # non publié, donc invisible publiquement


def test_unpublished_resource_not_directly_accessible():
    token, _ = _register_and_login("juriste3@example.com")
    created = client.post(
        "/legal/resources", json=RESOURCE, headers={"Authorization": f"Bearer {token}"}
    ).json()

    response = client.get(f"/legal/resources/{created['id']}")
    assert response.status_code == 404


def test_author_can_see_own_unpublished_resource_in_mine():
    token, _ = _register_and_login("juriste4@example.com")
    headers = {"Authorization": f"Bearer {token}"}
    client.post("/legal/resources", json=RESOURCE, headers=headers)

    mine = client.get("/legal/resources/mine", headers=headers).json()
    assert len(mine) == 1


def test_short_content_rejected():
    token, _ = _register_and_login("juriste5@example.com")
    response = client.post(
        "/legal/resources",
        json={**RESOURCE, "content": "Trop court."},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 422


def test_invalid_category_rejected():
    token, _ = _register_and_login("juriste6@example.com")
    response = client.post(
        "/legal/resources",
        json={**RESOURCE, "category": "categorie_inventee"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 422


def _create_lawyer_listing(token: str) -> dict:
    listing = {
        "name": "Cabinet Diop & Associés",
        "category": "avocat",
        "description": "Cabinet spécialisé en droit des affaires et droit de la famille.",
        "latitude": 14.7167,
        "longitude": -17.4677,
        "address": "Plateau",
        "city": "Dakar",
        "country": "Sénégal",
    }
    return client.post("/maps/listings", json=listing, headers={"Authorization": f"Bearer {token}"}).json()


def test_consultation_request_requires_real_lawyer_listing():
    client_token, _ = _register_and_login("client1@example.com")
    response = client.post(
        "/legal/consultations",
        json={
            "lawyer_listing_id": "id-inexistant",
            "category": "droit_du_travail",
            "subject": "Litige avec mon employeur",
            "description": "Mon employeur ne respecte pas les termes de mon contrat de travail.",
        },
        headers={"Authorization": f"Bearer {client_token}"},
    )
    assert response.status_code == 404


def test_consultation_request_rejects_non_lawyer_listing():
    owner_token, _ = _register_and_login("owner_ferme@example.com")
    ferme_listing = client.post(
        "/maps/listings",
        json={
            "name": "Ferme Test",
            "category": "ferme",
            "description": "Une ferme, pas un cabinet d'avocat.",
            "latitude": 14.7,
            "longitude": -17.4,
            "address": "Route rurale",
            "city": "Dakar",
            "country": "Sénégal",
        },
        headers={"Authorization": f"Bearer {owner_token}"},
    ).json()

    client_token, _ = _register_and_login("client2@example.com")
    response = client.post(
        "/legal/consultations",
        json={
            "lawyer_listing_id": ferme_listing["id"],
            "category": "droit_du_travail",
            "subject": "Litige",
            "description": "Une description suffisamment longue pour passer la validation.",
        },
        headers={"Authorization": f"Bearer {client_token}"},
    )
    assert response.status_code == 404


def test_full_consultation_workflow():
    lawyer_token, _ = _register_and_login("avocat1@example.com")
    lawyer_listing = _create_lawyer_listing(lawyer_token)

    client_token, _ = _register_and_login("client3@example.com")
    request = client.post(
        "/legal/consultations",
        json={
            "lawyer_listing_id": lawyer_listing["id"],
            "category": "droit_de_la_famille",
            "subject": "Question sur la garde d'enfants",
            "description": "Je souhaite comprendre mes droits concernant la garde de mes enfants.",
        },
        headers={"Authorization": f"Bearer {client_token}"},
    ).json()
    assert request["status"] == "en_attente"

    # Le client ne peut pas s'auto-accepter.
    forbidden = client.patch(
        f"/legal/consultations/{request['id']}/status",
        json={"status": "acceptee"},
        headers={"Authorization": f"Bearer {client_token}"},
    )
    assert forbidden.status_code == 403

    # L'avocat accepte.
    accepted = client.patch(
        f"/legal/consultations/{request['id']}/status",
        json={"status": "acceptee"},
        headers={"Authorization": f"Bearer {lawyer_token}"},
    )
    assert accepted.status_code == 200
    assert accepted.json()["status"] == "acceptee"

    # L'avocat retrouve la demande dans ses demandes entrantes.
    incoming = client.get(
        "/legal/consultations/incoming", headers={"Authorization": f"Bearer {lawyer_token}"}
    ).json()
    assert len(incoming) == 1

    # L'avocat termine la consultation.
    completed = client.patch(
        f"/legal/consultations/{request['id']}/status",
        json={"status": "terminee"},
        headers={"Authorization": f"Bearer {lawyer_token}"},
    )
    assert completed.json()["status"] == "terminee"


def test_stranger_cannot_view_consultation():
    lawyer_token, _ = _register_and_login("avocat2@example.com")
    lawyer_listing = _create_lawyer_listing(lawyer_token)
    client_token, _ = _register_and_login("client4@example.com")
    request = client.post(
        "/legal/consultations",
        json={
            "lawyer_listing_id": lawyer_listing["id"],
            "category": "fiscalite",
            "subject": "Question fiscale",
            "description": "Je souhaite des informations sur ma déclaration d'impôts annuelle.",
        },
        headers={"Authorization": f"Bearer {client_token}"},
    ).json()

    stranger_token, _ = _register_and_login("etranger@example.com")
    response = client.get(
        f"/legal/consultations/{request['id']}", headers={"Authorization": f"Bearer {stranger_token}"}
    )
    assert response.status_code == 403
