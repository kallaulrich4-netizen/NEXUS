"""
Tests du module Studio créatif. Nécessitent : pip install -r requirements.txt
Lancer avec : pytest tests/ -v
"""
import json
import os
from datetime import datetime, timedelta, timezone

os.environ.setdefault("SECRET_KEY", "test-secret-key-not-for-production")

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.database import Base, get_db
from app.core.rate_limit import _limiter
from app.main import app
from app.modules.auth.models import User
from app.modules.studio.models import Template, Filter

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


def _expire_trial(user_id: str) -> None:
    """Simule un compte dont l'essai gratuit de 24h est terminé, sans abonnement actif."""
    db = TestSessionLocal()
    user = db.query(User).filter(User.id == user_id).first()
    user.trial_ends_at = datetime.now(timezone.utc) - timedelta(days=1)
    user.premium_until = None
    db.commit()
    db.close()


def _publish_template(template_id: str) -> None:
    db = TestSessionLocal()
    template = db.query(Template).filter(Template.id == template_id).first()
    template.is_published = True
    db.commit()
    db.close()


def test_new_account_has_premium_access_during_trial():
    token, _ = _register_and_login("designer1@example.com")
    response = client.get("/studio/account/premium-status", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    assert response.json()["has_premium_access"] is True


def test_expired_trial_loses_premium_access():
    token, user_id = _register_and_login("designer2@example.com")
    _expire_trial(user_id)
    response = client.get("/studio/account/premium-status", headers={"Authorization": f"Bearer {token}"})
    assert response.json()["has_premium_access"] is False


DESIGN_PROJECT = {
    "title": "Affiche promotionnelle",
    "category": "affiche",
    "width": 1080,
    "height": 1350,
    "canvas_data": json.dumps({"layers": [{"type": "text", "content": "Promo"}]}),
}


def test_create_design_project():
    token, _ = _register_and_login("designer3@example.com")
    response = client.post(
        "/studio/design-projects", json=DESIGN_PROJECT, headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 201


def test_invalid_json_canvas_data_rejected():
    token, _ = _register_and_login("designer4@example.com")
    response = client.post(
        "/studio/design-projects",
        json={**DESIGN_PROJECT, "canvas_data": "ceci n'est pas du JSON"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 422


def test_premium_template_blocked_after_trial_expires():
    author_token, author_id = _register_and_login("createur_modele@example.com")
    template = client.post(
        "/studio/templates",
        json={
            "name": "Modèle Premium Luxe",
            "category": "flyer",
            "width": 1080,
            "height": 1080,
            "canvas_data": "{}",
            "is_premium": True,
        },
        headers={"Authorization": f"Bearer {author_token}"},
    ).json()
    _publish_template(template["id"])

    user_token, user_id = _register_and_login("utilisateur_gratuit@example.com")
    _expire_trial(user_id)

    response = client.post(
        "/studio/design-projects",
        json={**DESIGN_PROJECT, "template_id": template["id"]},
        headers={"Authorization": f"Bearer {user_token}"},
    )
    assert response.status_code == 402  # Payment Required


def test_premium_template_accessible_during_trial():
    author_token, _ = _register_and_login("createur_modele2@example.com")
    template = client.post(
        "/studio/templates",
        json={
            "name": "Modèle Premium Deluxe",
            "category": "logo",
            "width": 500,
            "height": 500,
            "canvas_data": "{}",
            "is_premium": True,
        },
        headers={"Authorization": f"Bearer {author_token}"},
    ).json()
    _publish_template(template["id"])

    user_token, _ = _register_and_login("utilisateur_essai@example.com")
    response = client.post(
        "/studio/design-projects",
        json={**DESIGN_PROJECT, "template_id": template["id"]},
        headers={"Authorization": f"Bearer {user_token}"},
    )
    assert response.status_code == 201


def test_free_template_always_accessible():
    author_token, _ = _register_and_login("createur_modele3@example.com")
    template = client.post(
        "/studio/templates",
        json={
            "name": "Modèle Gratuit",
            "category": "post_reseau_social",
            "width": 1080,
            "height": 1080,
            "canvas_data": "{}",
            "is_premium": False,
        },
        headers={"Authorization": f"Bearer {author_token}"},
    ).json()
    _publish_template(template["id"])

    user_token, user_id = _register_and_login("utilisateur_gratuit2@example.com")
    _expire_trial(user_id)

    response = client.post(
        "/studio/design-projects",
        json={**DESIGN_PROJECT, "template_id": template["id"]},
        headers={"Authorization": f"Bearer {user_token}"},
    )
    assert response.status_code == 201


def test_only_owner_can_access_design_project():
    token_a, _ = _register_and_login("designer5@example.com")
    token_b, _ = _register_and_login("designer6@example.com")
    project = client.post(
        "/studio/design-projects", json=DESIGN_PROJECT, headers={"Authorization": f"Bearer {token_a}"}
    ).json()
    response = client.get(
        f"/studio/design-projects/{project['id']}", headers={"Authorization": f"Bearer {token_b}"}
    )
    assert response.status_code == 404


def test_video_project_with_premium_filter_blocked_after_trial():
    filter_token, _ = _register_and_login("createur_filtre@example.com")
    premium_filter = client.post(
        "/studio/filters",
        params={"name": "Glow Cinéma Premium", "category": "glow", "is_premium": True},
        headers={"Authorization": f"Bearer {filter_token}"},
    ).json()

    user_token, user_id = _register_and_login("monteur1@example.com")
    _expire_trial(user_id)

    timeline = json.dumps({"clips": [{"filter_id": premium_filter["id"]}]})
    response = client.post(
        "/studio/video-projects",
        json={"title": "Ma vidéo", "timeline_data": timeline},
        headers={"Authorization": f"Bearer {user_token}"},
    )
    assert response.status_code == 402


def test_video_project_with_free_filter_always_allowed():
    filter_token, _ = _register_and_login("createur_filtre2@example.com")
    free_filter = client.post(
        "/studio/filters",
        params={"name": "Noir et blanc classique", "category": "noir_et_blanc", "is_premium": False},
        headers={"Authorization": f"Bearer {filter_token}"},
    ).json()

    user_token, user_id = _register_and_login("monteur2@example.com")
    _expire_trial(user_id)

    timeline = json.dumps({"clips": [{"filter_id": free_filter["id"]}]})
    response = client.post(
        "/studio/video-projects",
        json={"title": "Ma vidéo gratuite", "timeline_data": timeline},
        headers={"Authorization": f"Bearer {user_token}"},
    )
    assert response.status_code == 201


def test_unknown_filter_id_rejected():
    token, _ = _register_and_login("monteur3@example.com")
    timeline = json.dumps({"clips": [{"filter_id": "id-inexistant"}]})
    response = client.post(
        "/studio/video-projects",
        json={"title": "Vidéo test", "timeline_data": timeline},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 404


def test_publish_template_requires_superuser():
    os.environ["INITIAL_SUPERUSER_EMAIL"] = "patron_studio@example.com"
    from app.core.config import get_settings
    get_settings.cache_clear()

    regular_token, _ = _register_and_login("designer_normal@example.com")
    template = client.post(
        "/studio/templates",
        json={
            "name": "Modèle à publier",
            "category": "carte_visite",
            "width": 1050,
            "height": 600,
            "canvas_data": "{}",
            "is_premium": False,
        },
        headers={"Authorization": f"Bearer {regular_token}"},
    ).json()

    forbidden = client.post(
        f"/studio/templates/{template['id']}/publish",
        headers={"Authorization": f"Bearer {regular_token}"},
    )
    assert forbidden.status_code == 403

    admin_token, _ = _register_and_login("patron_studio@example.com")
    allowed = client.post(
        f"/studio/templates/{template['id']}/publish",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert allowed.status_code == 200
    assert allowed.json()["is_published"] is True

    now_visible = client.get("/studio/templates/search", params={"category": "carte_visite"}).json()
    assert any(t["id"] == template["id"] for t in now_visible)
