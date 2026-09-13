"""
Tests du module Marketplace. Nécessitent : pip install -r requirements.txt
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


def _register_and_login(email: str, country: str = "Sénégal") -> tuple[str, str]:
    user = {
        "email": email,
        "password": "MotDePasse123",
        "full_name": f"Utilisateur {email}",
        "country": country,
    }
    client.post("/auth/register", json=user)
    login = client.post("/auth/login", json={"email": email, "password": user["password"]})
    token = login.json()["access_token"]
    me = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
    return token, me.json()["id"]


VALID_PRODUCT = {
    "title": "Sac de riz local 25kg",
    "description": "Riz cultivé localement, sac de 25kg, qualité supérieure.",
    "price_amount": "15000",
    "currency": "XOF",
    "stock_quantity": 10,
    "category": "alimentation",
    "country": "Sénégal",
    "city": "Dakar",
    "shipping_scope": "national",
}


def test_create_product():
    token, _ = _register_and_login("aissatou@example.com")
    headers = {"Authorization": f"Bearer {token}"}
    response = client.post("/marketplace/products", json=VALID_PRODUCT, headers=headers)
    assert response.status_code == 201
    assert response.json()["title"] == VALID_PRODUCT["title"]


def test_only_seller_can_update_product():
    token_a, _ = _register_and_login("moussa@example.com")
    token_b, _ = _register_and_login("ibrahim@example.com")
    product = client.post(
        "/marketplace/products", json=VALID_PRODUCT, headers={"Authorization": f"Bearer {token_a}"}
    ).json()

    forbidden = client.patch(
        f"/marketplace/products/{product['id']}",
        json={"price_amount": "1"},
        headers={"Authorization": f"Bearer {token_b}"},
    )
    assert forbidden.status_code == 403


def test_order_creation_decrements_stock():
    token_seller, _ = _register_and_login("seller@example.com")
    token_buyer, _ = _register_and_login("buyer@example.com")
    product = client.post(
        "/marketplace/products", json=VALID_PRODUCT, headers={"Authorization": f"Bearer {token_seller}"}
    ).json()

    order = client.post(
        "/marketplace/orders",
        json={
            "items": [{"product_id": product["id"], "quantity": 3}],
            "shipping_country": "Sénégal",
            "shipping_city": "Dakar",
            "shipping_address": "Rue 12, Médina",
        },
        headers={"Authorization": f"Bearer {token_buyer}"},
    )
    assert order.status_code == 201
    assert order.json()["total_amount"] == "45000.00"

    updated_product = client.get(f"/marketplace/products/{product['id']}").json()
    assert updated_product["stock_quantity"] == 7


def test_order_rejected_when_stock_insufficient():
    token_seller, _ = _register_and_login("seller2@example.com")
    token_buyer, _ = _register_and_login("buyer2@example.com")
    product = client.post(
        "/marketplace/products",
        json={**VALID_PRODUCT, "stock_quantity": 2},
        headers={"Authorization": f"Bearer {token_seller}"},
    ).json()

    order = client.post(
        "/marketplace/orders",
        json={
            "items": [{"product_id": product["id"], "quantity": 5}],
            "shipping_country": "Sénégal",
            "shipping_address": "Rue 12, Médina",
        },
        headers={"Authorization": f"Bearer {token_buyer}"},
    )
    assert order.status_code == 409

    # Le stock ne doit PAS avoir été modifié par une commande refusée.
    unchanged_product = client.get(f"/marketplace/products/{product['id']}").json()
    assert unchanged_product["stock_quantity"] == 2


def test_buyer_cannot_see_another_buyers_order():
    token_seller, _ = _register_and_login("seller3@example.com")
    token_buyer_a, _ = _register_and_login("buyera@example.com")
    token_buyer_b, _ = _register_and_login("buyerb@example.com")

    product = client.post(
        "/marketplace/products", json=VALID_PRODUCT, headers={"Authorization": f"Bearer {token_seller}"}
    ).json()

    order = client.post(
        "/marketplace/orders",
        json={
            "items": [{"product_id": product["id"], "quantity": 1}],
            "shipping_country": "Sénégal",
            "shipping_address": "Rue 12, Médina",
        },
        headers={"Authorization": f"Bearer {token_buyer_a}"},
    ).json()

    forbidden = client.get(
        f"/marketplace/orders/{order['id']}", headers={"Authorization": f"Bearer {token_buyer_b}"}
    )
    assert forbidden.status_code == 404


def test_seller_can_progress_order_status_validly():
    token_seller, _ = _register_and_login("seller4@example.com")
    token_buyer, _ = _register_and_login("buyer4@example.com")
    product = client.post(
        "/marketplace/products", json=VALID_PRODUCT, headers={"Authorization": f"Bearer {token_seller}"}
    ).json()
    order = client.post(
        "/marketplace/orders",
        json={
            "items": [{"product_id": product["id"], "quantity": 1}],
            "shipping_country": "Sénégal",
            "shipping_address": "Rue 12, Médina",
        },
        headers={"Authorization": f"Bearer {token_buyer}"},
    ).json()

    confirm = client.patch(
        f"/marketplace/orders/{order['id']}/status",
        json={"status": "confirmed"},
        headers={"Authorization": f"Bearer {token_seller}"},
    )
    assert confirm.status_code == 200
    assert confirm.json()["status"] == "confirmed"

    # Impossible de sauter directement de "confirmed" à "delivered".
    invalid_jump = client.patch(
        f"/marketplace/orders/{order['id']}/status",
        json={"status": "delivered"},
        headers={"Authorization": f"Bearer {token_seller}"},
    )
    assert invalid_jump.status_code == 400


def test_local_products_prioritized_for_viewer_country():
    token_sn, _ = _register_and_login("vendeur_sn@example.com", country="Sénégal")
    client.post(
        "/marketplace/products",
        json={**VALID_PRODUCT, "country": "France", "title": "Produit France"},
        headers={"Authorization": f"Bearer {token_sn}"},
    )
    client.post(
        "/marketplace/products",
        json={**VALID_PRODUCT, "country": "Sénégal", "title": "Produit Sénégal"},
        headers={"Authorization": f"Bearer {token_sn}"},
    )

    viewer_token, _ = _register_and_login("viewer_sn@example.com", country="Sénégal")
    results = client.get(
        "/marketplace/products/search", headers={"Authorization": f"Bearer {viewer_token}"}
    ).json()

    # Le produit du même pays que le visiteur doit apparaître en premier,
    # sans que le produit international soit exclu des résultats.
    assert results[0]["country"] == "Sénégal"
    assert any(p["country"] == "France" for p in results)
