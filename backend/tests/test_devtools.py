"""
Tests du module Développement logiciel. Nécessitent : pip install -r requirements.txt
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


PROJECT = {
    "name": "Nexus Mobile App",
    "description": "Application mobile compagnon de la plateforme Nexus.",
    "project_type": "application_mobile",
    "tech_stack": "React Native, TypeScript",
}


def test_create_project():
    token = _register_and_login("dev1@example.com")
    response = client.post("/devtools/projects", json=PROJECT, headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 201
    assert response.json()["status"] == "planification"


def test_project_isolated_between_users():
    token_a = _register_and_login("dev2@example.com")
    token_b = _register_and_login("dev3@example.com")
    project = client.post(
        "/devtools/projects", json=PROJECT, headers={"Authorization": f"Bearer {token_a}"}
    ).json()
    response = client.get(
        f"/devtools/projects/{project['id']}", headers={"Authorization": f"Bearer {token_b}"}
    )
    assert response.status_code == 404


def test_add_task_and_update_status():
    token = _register_and_login("dev4@example.com")
    headers = {"Authorization": f"Bearer {token}"}
    project = client.post("/devtools/projects", json=PROJECT, headers=headers).json()

    task = client.post(
        f"/devtools/projects/{project['id']}/tasks",
        json={"title": "Mettre en place l'authentification", "priority": "haute"},
        headers=headers,
    ).json()
    assert task["status"] == "a_faire"

    updated = client.patch(
        f"/devtools/tasks/{task['id']}/status", json={"status": "en_cours"}, headers=headers
    )
    assert updated.json()["status"] == "en_cours"


def test_invalid_task_priority_rejected():
    token = _register_and_login("dev5@example.com")
    headers = {"Authorization": f"Bearer {token}"}
    project = client.post("/devtools/projects", json=PROJECT, headers=headers).json()
    response = client.post(
        f"/devtools/projects/{project['id']}/tasks",
        json={"title": "Tâche test", "priority": "extreme"},
        headers=headers,
    )
    assert response.status_code == 422


def test_project_dashboard_counts_by_status():
    token = _register_and_login("dev6@example.com")
    headers = {"Authorization": f"Bearer {token}"}
    project = client.post("/devtools/projects", json=PROJECT, headers=headers).json()

    client.post(f"/devtools/projects/{project['id']}/tasks", json={"title": "Tâche 1"}, headers=headers)
    task2 = client.post(
        f"/devtools/projects/{project['id']}/tasks", json={"title": "Tâche 2"}, headers=headers
    ).json()
    client.patch(f"/devtools/tasks/{task2['id']}/status", json={"status": "termine"}, headers=headers)

    dashboard = client.get(f"/devtools/projects/{project['id']}/dashboard", headers=headers).json()
    assert dashboard["total_tasks"] == 2
    assert dashboard["tasks_by_status"]["a_faire"] == 1
    assert dashboard["tasks_by_status"]["termine"] == 1


def test_create_and_list_snippet():
    token = _register_and_login("dev7@example.com")
    headers = {"Authorization": f"Bearer {token}"}
    snippet = client.post(
        "/devtools/snippets",
        json={
            "title": "Décorateur de rate limiting FastAPI",
            "language": "python",
            "code": "def rate_limit(): pass",
            "tags": "fastapi, securite",
        },
        headers=headers,
    )
    assert snippet.status_code == 201

    snippets = client.get("/devtools/snippets", params={"language": "python"}, headers=headers).json()
    assert len(snippets) == 1


def test_empty_snippet_code_rejected():
    token = _register_and_login("dev8@example.com")
    response = client.post(
        "/devtools/snippets",
        json={"title": "Snippet vide", "language": "python", "code": "   "},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 422


def test_api_endpoint_documentation_and_duplicate_rejection():
    token = _register_and_login("dev9@example.com")
    headers = {"Authorization": f"Bearer {token}"}
    project = client.post("/devtools/projects", json=PROJECT, headers=headers).json()

    endpoint = {
        "method": "post",
        "path": "/auth/login",
        "description": "Authentifie un utilisateur et retourne un jeton.",
        "request_schema": '{"email": "string", "password": "string"}',
    }
    first = client.post(
        f"/devtools/projects/{project['id']}/api-endpoints", json=endpoint, headers=headers
    )
    assert first.status_code == 201
    assert first.json()["method"] == "POST"

    duplicate = client.post(
        f"/devtools/projects/{project['id']}/api-endpoints", json=endpoint, headers=headers
    )
    assert duplicate.status_code == 409


def test_invalid_json_schema_rejected():
    token = _register_and_login("dev10@example.com")
    headers = {"Authorization": f"Bearer {token}"}
    project = client.post("/devtools/projects", json=PROJECT, headers=headers).json()
    response = client.post(
        f"/devtools/projects/{project['id']}/api-endpoints",
        json={
            "method": "GET",
            "path": "/users",
            "description": "Liste les utilisateurs.",
            "response_schema": "ceci n'est pas du JSON valide",
        },
        headers=headers,
    )
    assert response.status_code == 422


def test_path_must_start_with_slash():
    token = _register_and_login("dev11@example.com")
    headers = {"Authorization": f"Bearer {token}"}
    project = client.post("/devtools/projects", json=PROJECT, headers=headers).json()
    response = client.post(
        f"/devtools/projects/{project['id']}/api-endpoints",
        json={"method": "GET", "path": "users", "description": "Chemin invalide."},
        headers=headers,
    )
    assert response.status_code == 422
