"""
Tests du module Paiement. Nécessitent : pip install -r requirements.txt
Lancer avec : pytest tests/ -v
"""
import os

os.environ.setdefault("SECRET_KEY", "test-secret-key-not-for-production")
# Depuis l'audit de juillet 2026, la création de plan tarifaire est
# réservée au super-administrateur (voir modules/payments/router.py).
# On fixe donc UN SEUL email admin pour tout ce fichier, comme le fait
# test_superuser.py, plutôt que les emails "admin_paiementN@..." d'avant
# qui n'étaient pas réellement superusers (la route était encore ouverte
# à tous à l'époque).
os.environ["INITIAL_SUPERUSER_EMAIL"] = "admin_paiements@nexus-test.com"

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.config import get_settings

get_settings.cache_clear()  # essentiel : force la relecture de INITIAL_SUPERUSER_EMAIL

from app.core.database import Base, get_db
from app.core.rate_limit import _limiter
from app.main import app

ADMIN_EMAIL = "admin_paiements@nexus-test.com"

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


def _create_plan(token: str, name="Journalier", duration_days=1, price=100) -> dict:
    return client.post(
        "/payments/plans",
        json={"name": name, "duration_days": duration_days, "price_amount": price, "currency": "XOF"},
        headers={"Authorization": f"Bearer {token}"},
    ).json()


def test_create_and_list_plans():
    admin_token = _register_and_login(ADMIN_EMAIL)
    _create_plan(admin_token, "Journalier", 1, 100)
    _create_plan(admin_token, "Hebdomadaire", 7, 500)
    plans = client.get("/payments/plans").json()
    assert len(plans) == 2


def test_plan_creation_requires_superuser():
    token = _register_and_login("payeur1@example.com")
    response = client.post(
        "/payments/plans",
        json={"name": "Journalier", "duration_days": 1, "price_amount": 100, "currency": "XOF"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 403


def test_negative_plan_price_rejected():
    admin_token = _register_and_login(ADMIN_EMAIL)
    response = client.post(
        "/payments/plans",
        json={"name": "Invalide", "duration_days": 1, "price_amount": -100, "currency": "XOF"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 422


def test_subscribe_does_not_grant_premium_before_confirmation():
    admin_token = _register_and_login(ADMIN_EMAIL)
    plan = _create_plan(admin_token, "Mensuel", 30, 1350)

    user_token = _register_and_login("client_paiement1@example.com")
    headers = {"Authorization": f"Bearer {user_token}"}

    response = client.post(
        "/payments/subscribe",
        json={"plan_id": plan["id"], "payment_method": "mtn_mobile_money"},
        headers=headers,
    )
    assert response.status_code == 201
    body = response.json()
    assert body["subscription"]["status"] == "en_attente_paiement"
    assert body["payment"]["status"] == "en_attente"

    subs = client.get("/payments/subscriptions/mine", headers=headers).json()
    assert subs[0]["status"] == "en_attente_paiement"


def test_webhook_confirms_payment_and_activates_premium():
    admin_token = _register_and_login(ADMIN_EMAIL)
    plan = _create_plan(admin_token, "Journalier", 1, 100)

    user_token = _register_and_login("client_paiement2@example.com")
    headers = {"Authorization": f"Bearer {user_token}"}

    sub_response = client.post(
        "/payments/subscribe",
        json={"plan_id": plan["id"], "payment_method": "orange_money"},
        headers=headers,
    ).json()

    from app.modules.payments.models import Payment

    db = TestSessionLocal()
    payment = db.query(Payment).filter(Payment.id == sub_response["payment"]["id"]).first()
    payment.provider_reference = "TEST-REF-001"
    db.commit()
    db.close()

    webhook_response = client.post(
        "/payments/webhook", json={"provider_reference": "TEST-REF-001", "status": "reussi"}
    )
    assert webhook_response.status_code == 200
    assert webhook_response.json()["status"] == "reussi"

    subscription = client.get(
        f"/payments/subscriptions/{sub_response['subscription']['id']}", headers=headers
    ).json()
    assert subscription["status"] == "active"
    assert subscription["ends_at"] is not None


def test_webhook_cannot_double_credit_same_payment():
    admin_token = _register_and_login(ADMIN_EMAIL)
    plan = _create_plan(admin_token, "Journalier", 1, 100)
    user_token = _register_and_login("client_paiement3@example.com")
    headers = {"Authorization": f"Bearer {user_token}"}

    sub_response = client.post(
        "/payments/subscribe", json={"plan_id": plan["id"], "payment_method": "visa"}, headers=headers
    ).json()

    from app.modules.payments.models import Payment

    db = TestSessionLocal()
    payment = db.query(Payment).filter(Payment.id == sub_response["payment"]["id"]).first()
    payment.provider_reference = "TEST-REF-002"
    db.commit()
    db.close()

    first = client.post("/payments/webhook", json={"provider_reference": "TEST-REF-002", "status": "reussi"})
    assert first.status_code == 200

    second = client.post("/payments/webhook", json={"provider_reference": "TEST-REF-002", "status": "reussi"})
    assert second.status_code == 409


def test_webhook_unknown_reference_rejected():
    response = client.post(
        "/payments/webhook", json={"provider_reference": "REFERENCE-INEXISTANTE", "status": "reussi"}
    )
    assert response.status_code == 404


def test_cancel_subscription():
    admin_token = _register_and_login(ADMIN_EMAIL)
    plan = _create_plan(admin_token, "Journalier", 1, 100)
    user_token = _register_and_login("client_paiement4@example.com")
    headers = {"Authorization": f"Bearer {user_token}"}

    sub_response = client.post(
        "/payments/subscribe", json={"plan_id": plan["id"], "payment_method": "mtn_mobile_money"}, headers=headers
    ).json()

    from app.modules.payments.models import Payment

    db = TestSessionLocal()
    payment = db.query(Payment).filter(Payment.id == sub_response["payment"]["id"]).first()
    payment.provider_reference = "TEST-REF-003"
    db.commit()
    db.close()
    client.post("/payments/webhook", json={"provider_reference": "TEST-REF-003", "status": "reussi"})

    cancelled = client.post(
        f"/payments/subscriptions/{sub_response['subscription']['id']}/cancel", headers=headers
    )
    assert cancelled.status_code == 200
    assert cancelled.json()["status"] == "annulee"


def test_invalid_payment_method_rejected():
    admin_token = _register_and_login(ADMIN_EMAIL)
    plan = _create_plan(admin_token)
    user_token = _register_and_login("client_paiement5@example.com")
    response = client.post(
        "/payments/subscribe",
        json={"plan_id": plan["id"], "payment_method": "bitcoin"},
        headers={"Authorization": f"Bearer {user_token}"},
    )
    assert response.status_code == 422


def test_payment_history_lists_all_attempts_for_user():
    admin_token = _register_and_login(ADMIN_EMAIL)
    plan = _create_plan(admin_token, "Journalier", 1, 100)
    user_token = _register_and_login("client_paiement6@example.com")
    headers = {"Authorization": f"Bearer {user_token}"}

    client.post("/payments/subscribe", json={"plan_id": plan["id"], "payment_method": "orange_money"}, headers=headers)

    response = client.get("/payments/payments/mine", headers=headers)
    assert response.status_code == 200
    body = response.json()
    assert len(body) == 1
    assert body[0]["method"] == "orange_money"


def test_payment_history_requires_authentication():
    response = client.get("/payments/payments/mine")
    assert response.status_code == 401


def test_active_subscription_is_null_before_payment_confirmed():
    admin_token = _register_and_login(ADMIN_EMAIL)
    plan = _create_plan(admin_token, "Journalier", 1, 100)
    user_token = _register_and_login("client_paiement7@example.com")
    headers = {"Authorization": f"Bearer {user_token}"}

    client.post("/payments/subscribe", json={"plan_id": plan["id"], "payment_method": "visa"}, headers=headers)

    response = client.get("/payments/subscriptions/mine/active", headers=headers)
    assert response.status_code == 200
    assert response.json() is None


def test_active_subscription_returned_after_payment_confirmed():
    admin_token = _register_and_login(ADMIN_EMAIL)
    plan = _create_plan(admin_token, "Journalier", 1, 100)
    user_token = _register_and_login("client_paiement8@example.com")
    headers = {"Authorization": f"Bearer {user_token}"}

    sub_response = client.post(
        "/payments/subscribe", json={"plan_id": plan["id"], "payment_method": "mtn_mobile_money"}, headers=headers
    ).json()

    from app.modules.payments.models import Payment

    db = TestSessionLocal()
    payment = db.query(Payment).filter(Payment.id == sub_response["payment"]["id"]).first()
    payment.provider_reference = "TEST-REF-ACTIVE"
    db.commit()
    db.close()
    client.post("/payments/webhook", json={"provider_reference": "TEST-REF-ACTIVE", "status": "reussi"})

    response = client.get("/payments/subscriptions/mine/active", headers=headers)
    assert response.status_code == 200
    assert response.json()["id"] == sub_response["subscription"]["id"]
