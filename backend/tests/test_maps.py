"""
Tests du module Cartographie intelligente. Nécessitent : pip install -r requirements.txt
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


# Dakar
LISTING_DAKAR = {
    "name": "Ferme Agro Teranga",
    "category": "ferme",
    "description": "Exploitation maraîchère spécialisée en légumes bio.",
    "latitude": 14.7167,
    "longitude": -17.4677,
    "address": "Route de Rufisque",
    "city": "Dakar",
    "country": "Sénégal",
}

# Thiès, à environ 65 km de Dakar
LISTING_THIES = {
    "name": "Clinique Vétérinaire Thiès",
    "category": "veterinaire",
    "description": "Soins pour bétail et animaux domestiques.",
    "latitude": 14.7910,
    "longitude": -16.9256,
    "address": "Avenue Lat Dior",
    "city": "Thiès",
    "country": "Sénégal",
}

# Paris, très loin des deux précédents
LISTING_PARIS = {
    "name": "Cabinet Juridique Dupont",
    "category": "avocat",
    "description": "Cabinet spécialisé en droit des affaires internationales.",
    "latitude": 48.8566,
    "longitude": 2.3522,
    "address": "10 rue de Rivoli",
    "city": "Paris",
    "country": "France",
}


def test_create_listing():
    token, _ = _register_and_login("fermier@example.com")
    response = client.post(
        "/maps/listings", json=LISTING_DAKAR, headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 201
    assert response.json()["is_verified"] is False  # jamais auto-vérifié à la création


def test_invalid_category_rejected():
    token, _ = _register_and_login("test_cat@example.com")
    response = client.post(
        "/maps/listings",
        json={**LISTING_DAKAR, "category": "categorie_inventee"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 422


def test_invalid_coordinates_rejected():
    token, _ = _register_and_login("test_coord@example.com")
    response = client.post(
        "/maps/listings",
        json={**LISTING_DAKAR, "latitude": 999},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 422


def test_only_owner_can_update_listing():
    token_a, _ = _register_and_login("owner@example.com")
    token_b, _ = _register_and_login("intruder@example.com")
    listing = client.post(
        "/maps/listings", json=LISTING_DAKAR, headers={"Authorization": f"Bearer {token_a}"}
    ).json()

    response = client.patch(
        f"/maps/listings/{listing['id']}",
        json={"name": "Nom modifié"},
        headers={"Authorization": f"Bearer {token_b}"},
    )
    assert response.status_code == 403


def test_search_by_proximity_orders_by_distance():
    token, _ = _register_and_login("cartographe@example.com")
    headers = {"Authorization": f"Bearer {token}"}
    client.post("/maps/listings", json=LISTING_DAKAR, headers=headers)
    client.post("/maps/listings", json=LISTING_THIES, headers=headers)
    client.post("/maps/listings", json=LISTING_PARIS, headers=headers)

    # Recherche depuis un point proche de Dakar, rayon 100 km : Paris doit être exclu.
    response = client.get(
        "/maps/listings/search",
        params={"near_lat": 14.7167, "near_lng": -17.4677, "radius_km": 100},
    )
    results = response.json()
    names = [r["name"] for r in results]
    assert LISTING_DAKAR["name"] in names
    assert LISTING_THIES["name"] in names
    assert LISTING_PARIS["name"] not in names
    # Dakar (distance ~0) doit arriver avant Thiès (~65 km).
    assert results[0]["name"] == LISTING_DAKAR["name"]
    assert results[0]["distance_km"] < results[1]["distance_km"]


def test_add_review_and_average_rating():
    owner_token, _ = _register_and_login("owner2@example.com")
    reviewer_token, _ = _register_and_login("reviewer@example.com")
    listing = client.post(
        "/maps/listings", json=LISTING_DAKAR, headers={"Authorization": f"Bearer {owner_token}"}
    ).json()

    review = client.post(
        f"/maps/listings/{listing['id']}/reviews",
        json={"rating": 4, "comment": "Très bon accueil."},
        headers={"Authorization": f"Bearer {reviewer_token}"},
    )
    assert review.status_code == 201

    updated_listing = client.get(f"/maps/listings/{listing['id']}").json()
    assert updated_listing["average_rating"] == 4.0
    assert updated_listing["reviews_count"] == 1


def test_cannot_review_same_listing_twice():
    owner_token, _ = _register_and_login("owner3@example.com")
    reviewer_token, _ = _register_and_login("reviewer2@example.com")
    listing = client.post(
        "/maps/listings", json=LISTING_DAKAR, headers={"Authorization": f"Bearer {owner_token}"}
    ).json()

    headers = {"Authorization": f"Bearer {reviewer_token}"}
    client.post(f"/maps/listings/{listing['id']}/reviews", json={"rating": 5}, headers=headers)
    second = client.post(f"/maps/listings/{listing['id']}/reviews", json={"rating": 2}, headers=headers)
    assert second.status_code == 409


def test_invalid_rating_rejected():
    owner_token, _ = _register_and_login("owner4@example.com")
    listing = client.post(
        "/maps/listings", json=LISTING_DAKAR, headers={"Authorization": f"Bearer {owner_token}"}
    ).json()
    response = client.post(
        f"/maps/listings/{listing['id']}/reviews",
        json={"rating": 8},
        headers={"Authorization": f"Bearer {owner_token}"},
    )
    assert response.status_code == 422
