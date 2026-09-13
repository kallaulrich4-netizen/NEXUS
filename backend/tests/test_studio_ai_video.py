"""
Tests de la génération vidéo par IA (module Studio créatif).
Nécessitent : pip install -r requirements.txt
Lancer avec : pytest tests/ -v
"""
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
    db = TestSessionLocal()
    user = db.query(User).filter(User.id == user_id).first()
    user.trial_ends_at = datetime.now(timezone.utc) - timedelta(days=1)
    user.premium_until = None
    db.commit()
    db.close()


def test_ai_video_generation_available_during_trial():
    token, _ = _register_and_login("createur_video1@example.com")
    response = client.post(
        "/studio/ai-video-jobs",
        json={
            "prompt": "Un lion majestueux marchant dans la savane au coucher du soleil",
            "style": "ultra_realiste",
            "duration_seconds": 8,
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 201
    # Aucun fournisseur réel branché : le job reste honnêtement en attente.
    assert response.json()["status"] == "en_attente"
    assert response.json()["result_url"] is None


def test_ai_video_generation_blocked_after_trial_expires():
    token, user_id = _register_and_login("createur_video2@example.com")
    _expire_trial(user_id)
    response = client.post(
        "/studio/ai-video-jobs",
        json={"prompt": "Une ville futuriste vue du ciel la nuit", "style": "3d"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 402


def test_ai_video_prompt_too_short_rejected():
    token, _ = _register_and_login("createur_video3@example.com")
    response = client.post(
        "/studio/ai-video-jobs",
        json={"prompt": "trop court"[:5], "style": "2d"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 422


def test_invalid_video_style_rejected():
    token, _ = _register_and_login("createur_video4@example.com")
    response = client.post(
        "/studio/ai-video-jobs",
        json={"prompt": "Un prompt suffisamment long pour être valide", "style": "style_invente"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 422


def test_list_and_get_ai_video_jobs():
    token, _ = _register_and_login("createur_video5@example.com")
    headers = {"Authorization": f"Bearer {token}"}
    job = client.post(
        "/studio/ai-video-jobs",
        json={"prompt": "Un dragon volant au-dessus des montagnes enneigées", "style": "animation"},
        headers=headers,
    ).json()

    jobs = client.get("/studio/ai-video-jobs", headers=headers).json()
    assert len(jobs) == 1

    detail = client.get(f"/studio/ai-video-jobs/{job['id']}", headers=headers).json()
    assert detail["id"] == job["id"]


def test_cannot_access_another_users_ai_video_job():
    token_a, _ = _register_and_login("createur_video6@example.com")
    token_b, _ = _register_and_login("createur_video7@example.com")
    job = client.post(
        "/studio/ai-video-jobs",
        json={"prompt": "Une forêt enchantée avec des lucioles la nuit", "style": "cinematique"},
        headers={"Authorization": f"Bearer {token_a}"},
    ).json()

    response = client.get(
        f"/studio/ai-video-jobs/{job['id']}", headers={"Authorization": f"Bearer {token_b}"}
    )
    assert response.status_code == 404
