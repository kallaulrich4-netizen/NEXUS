"""
Tests des briques transversales ajoutées : notifications, journal
d'activité, centre d'administration, sauvegardes, monitoring système,
et génération de documents (CSV).
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


def _make_superuser(email: str):
    from app.modules.auth.models import User

    db = TestSessionLocal()
    user = db.query(User).filter(User.email == email).first()
    user.is_superuser = True
    db.commit()
    db.close()


# --- Notifications ---

def test_registration_creates_welcome_notification():
    token = _register_and_login("notif1@example.com")
    response = client.get("/notifications", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    body = response.json()
    assert len(body) >= 1
    assert any(n["category"] == "confirmation" for n in body)


def test_unread_count_and_mark_read():
    token = _register_and_login("notif2@example.com")
    headers = {"Authorization": f"Bearer {token}"}

    unread_before = client.get("/notifications/unread-count", headers=headers).json()["unread_count"]
    assert unread_before >= 1

    notifications = client.get("/notifications", headers=headers).json()
    notification_id = notifications[0]["id"]

    mark_response = client.post(f"/notifications/{notification_id}/read", headers=headers)
    assert mark_response.status_code == 200
    assert mark_response.json()["is_read"] is True


def test_mark_all_read():
    token = _register_and_login("notif3@example.com")
    headers = {"Authorization": f"Bearer {token}"}
    response = client.post("/notifications/read-all", headers=headers)
    assert response.status_code == 200
    unread_after = client.get("/notifications/unread-count", headers=headers).json()["unread_count"]
    assert unread_after == 0


def test_notifications_require_authentication():
    response = client.get("/notifications")
    assert response.status_code == 401


# --- Journal d'activité ---

def test_activity_log_records_registration_and_login():
    token = _register_and_login("audit1@example.com")
    response = client.get("/activity-log/mine", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    actions = [entry["action"] for entry in response.json()]
    assert "creation" in actions
    assert "connexion" in actions


def test_activity_log_all_requires_superuser():
    token = _register_and_login("audit2@example.com")
    response = client.get("/activity-log/all", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 403


def test_activity_log_all_accessible_to_superuser():
    email = "audit3@example.com"
    token = _register_and_login(email)
    _make_superuser(email)
    # Un nouveau token n'est pas nécessaire : is_superuser est relu depuis la base à chaque requête.
    response = client.get("/activity-log/all", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200


# --- Centre d'administration ---

def test_admin_endpoints_reject_non_superuser():
    token = _register_and_login("admin1@example.com")
    headers = {"Authorization": f"Bearer {token}"}
    assert client.get("/auth/admin/users", headers=headers).status_code == 403
    assert client.get("/auth/admin/stats", headers=headers).status_code == 403


def test_admin_can_list_users_and_view_stats():
    email = "admin2@example.com"
    token = _register_and_login(email)
    _make_superuser(email)
    headers = {"Authorization": f"Bearer {token}"}

    users_response = client.get("/auth/admin/users", headers=headers)
    assert users_response.status_code == 200
    assert len(users_response.json()) >= 1

    stats_response = client.get("/auth/admin/stats", headers=headers)
    assert stats_response.status_code == 200
    assert stats_response.json()["total_users"] >= 1


def test_admin_can_deactivate_another_user():
    admin_email = "admin3@example.com"
    admin_token = _register_and_login(admin_email)
    _make_superuser(admin_email)

    target_email = "target3@example.com"
    _register_and_login(target_email)

    from app.modules.auth.models import User

    db = TestSessionLocal()
    target_user = db.query(User).filter(User.email == target_email).first()
    target_id = target_user.id
    db.close()

    response = client.patch(
        f"/auth/admin/users/{target_id}",
        json={"is_active": False},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 200
    assert response.json()["is_active"] is False

    login_attempt = client.post("/auth/login", json={"email": target_email, "password": "MotDePasse123"})
    assert login_attempt.status_code == 401


# --- Sauvegardes ---

def test_schedule_and_run_backup():
    token = _register_and_login("backup1@example.com")
    headers = {"Authorization": f"Bearer {token}"}

    scheduled = client.post("/devops/backups", json={"backup_type": "complete"}, headers=headers)
    assert scheduled.status_code == 201
    assert scheduled.json()["status"] == "planifiee"

    backup_id = scheduled.json()["id"]
    executed = client.post(f"/devops/backups/{backup_id}/run", headers=headers)
    assert executed.status_code == 200
    assert executed.json()["status"] == "reussie"
    assert executed.json()["file_reference"] is not None


def test_list_backups_returns_only_mine():
    token1 = _register_and_login("backup2@example.com")
    token2 = _register_and_login("backup2b@example.com")

    client.post("/devops/backups", json={"backup_type": "complete"}, headers={"Authorization": f"Bearer {token1}"})

    response = client.get("/devops/backups", headers={"Authorization": f"Bearer {token2}"})
    assert response.status_code == 200
    assert response.json() == []


# --- Monitoring système ---

def test_system_health_returns_valid_status():
    token = _register_and_login("health1@example.com")
    response = client.get("/devops/system-health", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    body = response.json()
    assert body["status"] in {"operationnel", "degrade", "indisponible"}
    assert body["database_reachable"] is True


# --- Génération de documents : export CSV réutilisable ---

def test_agriculture_field_report_csv():
    token = _register_and_login("report1@example.com")
    headers = {"Authorization": f"Bearer {token}"}
    field = client.post(
        "/agriculture/fields",
        json={"name": "Parcelle Rapport", "area_hectares": 1.5, "country": "Cameroun"},
        headers=headers,
    ).json()

    response = client.get(f"/agriculture/fields/{field['id']}/report?file_format=csv", headers=headers)
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/csv")
    assert b"Parcelle Rapport" in response.content


def test_agriculture_field_report_rejects_invalid_format():
    token = _register_and_login("report2@example.com")
    headers = {"Authorization": f"Bearer {token}"}
    field = client.post(
        "/agriculture/fields",
        json={"name": "Parcelle Rapport 2", "area_hectares": 1.0, "country": "Cameroun"},
        headers=headers,
    ).json()

    response = client.get(f"/agriculture/fields/{field['id']}/report?file_format=powerpoint_invalide", headers=headers)
    assert response.status_code == 400


def test_livestock_animal_report_csv():
    token = _register_and_login("report3@example.com")
    headers = {"Authorization": f"Bearer {token}"}
    herd = client.post(
        "/livestock/herds",
        json={"name": "Troupeau Rapport", "species": "bovins", "current_count": 2, "country": "Cameroun"},
        headers=headers,
    ).json()
    animal = client.post(
        f"/livestock/herds/{herd['id']}/animals", json={"tag": "R-001"}, headers=headers
    ).json()

    response = client.get(f"/livestock/animals/{animal['id']}/report?file_format=csv", headers=headers)
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/csv")
    assert b"R-001" in response.content
