"""
Tests du rendu vidéo réel du Studio créatif (montage façon CapCut/InShot).
Nécessitent : pip install -r requirements.txt, et FFmpeg installé sur la
machine (déjà requis par le projet — voir Dockerfile / deploy.sh).
Lancer avec : pytest tests/test_studio_render.py -v

Note : la logique de rendu elle-même (app/modules/studio/render.py) a
été validée séparément avec de vrais appels FFmpeg (clips synthétiques,
vérification de la durée exacte et des couleurs de pixels après filtre)
pendant le développement de cette fonctionnalité. Ces tests-ci valident
le chemin complet HTTP (upload -> création -> rendu -> téléchargement),
que cet environnement d'audit ne peut pas exécuter (FastAPI/SQLAlchemy
non installés ici, voir rapport d'audit).
"""
import io
import json
import os
import shutil
import tempfile

os.environ.setdefault("SECRET_KEY", "test-secret-key-not-for-production")

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.config import get_settings
from app.core.database import Base, get_db
from app.core.rate_limit import _limiter

_TEST_MEDIA_DIR = tempfile.mkdtemp(prefix="nexus_media_test_")
os.environ["MEDIA_STORAGE_PATH"] = _TEST_MEDIA_DIR
get_settings.cache_clear()

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


@pytest.fixture(scope="module", autouse=True)
def cleanup_media_dir():
    yield
    shutil.rmtree(_TEST_MEDIA_DIR, ignore_errors=True)


app.dependency_overrides[get_db] = override_get_db
client = TestClient(app)


def _register_and_login(email="createur@example.com") -> str:
    client.post("/auth/register", json={"email": email, "password": "MotDePasse1", "full_name": "Créateur Test"})
    response = client.post("/auth/login", json={"email": email, "password": "MotDePasse1"})
    return response.json()["access_token"]


def _tiny_png_bytes() -> bytes:
    # PNG 1x1 pixel valide minimal (rouge), pour tester l'upload sans dépendance externe.
    return bytes.fromhex(
        "89504e470d0a1a0a0000000d4948445200000001000000010802000000907753"
        "de0000000c4944415408d763f8cfc0c00000030101007f9f79c30000000049454e44ae426082"
    )


def test_upload_rejects_unsupported_extension():
    token = _register_and_login()
    response = client.post(
        "/studio/media",
        files={"file": ("virus.exe", b"contenu", "application/octet-stream")},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 415


def test_upload_and_list_media():
    token = _register_and_login("createur2@example.com")
    response = client.post(
        "/studio/media",
        files={"file": ("photo.png", _tiny_png_bytes(), "image/png")},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 201
    body = response.json()
    assert body["media_type"] == "image"
    assert body["original_filename"] == "photo.png"

    listed = client.get("/studio/media", headers={"Authorization": f"Bearer {token}"}).json()
    assert len(listed) == 1


def test_render_video_project_without_media_using_color_clips():
    """
    Le cas le plus simple à tester sans dépendance externe : une timeline
    faite uniquement de clips "color" (fonds unis + texte), qui ne
    nécessite aucun fichier importé au préalable.
    """
    token = _register_and_login("createur3@example.com")
    headers = {"Authorization": f"Bearer {token}"}

    timeline = json.dumps({
        "clips": [
            {"type": "color", "color": "black", "duration_seconds": 1, "text_overlay": "Bienvenue sur Nexus"},
            {"type": "color", "color": "blue", "duration_seconds": 1, "text_overlay": "Montage automatique"},
        ]
    })
    create_response = client.post(
        "/studio/video-projects",
        json={"title": "Ma première vidéo", "resolution": "320x240", "timeline_data": timeline},
        headers=headers,
    )
    assert create_response.status_code == 201
    project_id = create_response.json()["id"]
    assert create_response.json()["download_available"] is False

    render_response = client.post(f"/studio/video-projects/{project_id}/render", headers=headers)
    assert render_response.status_code == 200
    rendered = render_response.json()
    assert rendered["render_status"] == "pret", rendered.get("render_error")
    assert rendered["download_available"] is True

    download_response = client.get(f"/studio/video-projects/{project_id}/download", headers=headers)
    assert download_response.status_code == 200
    assert download_response.headers["content-type"] == "video/mp4"
    assert len(download_response.content) > 0  # un vrai fichier vidéo non vide


def test_download_before_render_returns_conflict():
    token = _register_and_login("createur4@example.com")
    headers = {"Authorization": f"Bearer {token}"}
    create_response = client.post(
        "/studio/video-projects",
        json={"title": "Pas encore rendue", "resolution": "320x240", "timeline_data": '{"clips": []}'},
        headers=headers,
    )
    project_id = create_response.json()["id"]
    response = client.get(f"/studio/video-projects/{project_id}/download", headers=headers)
    assert response.status_code == 409


def test_render_fails_gracefully_with_empty_timeline():
    token = _register_and_login("createur5@example.com")
    headers = {"Authorization": f"Bearer {token}"}
    create_response = client.post(
        "/studio/video-projects",
        json={"title": "Timeline vide", "resolution": "320x240", "timeline_data": '{"clips": []}'},
        headers=headers,
    )
    project_id = create_response.json()["id"]
    render_response = client.post(f"/studio/video-projects/{project_id}/render", headers=headers)
    assert render_response.status_code == 200
    assert render_response.json()["render_status"] == "echoue"
    assert render_response.json()["render_error"]


def test_cannot_render_or_download_another_users_project():
    token_a = _register_and_login("createur6a@example.com")
    token_b = _register_and_login("createur6b@example.com")
    create_response = client.post(
        "/studio/video-projects",
        json={"title": "Privée", "resolution": "320x240", "timeline_data": '{"clips": []}'},
        headers={"Authorization": f"Bearer {token_a}"},
    )
    project_id = create_response.json()["id"]

    render_response = client.post(
        f"/studio/video-projects/{project_id}/render", headers={"Authorization": f"Bearer {token_b}"}
    )
    assert render_response.status_code == 404

    download_response = client.get(
        f"/studio/video-projects/{project_id}/download", headers={"Authorization": f"Bearer {token_b}"}
    )
    assert download_response.status_code == 404
