"""
Tests du module Réseau social. Nécessitent : pip install -r requirements.txt
Lancer avec : pytest tests/ -v
"""
import os

os.environ.setdefault("SECRET_KEY", "test-secret-key-not-for-production")

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.database import Base, get_db
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
    yield
    Base.metadata.drop_all(bind=TEST_ENGINE)


app.dependency_overrides[get_db] = override_get_db
client = TestClient(app)


def _register_and_login(email: str) -> tuple[str, str]:
    user = {
        "email": email,
        "password": "MotDePasse123",
        "full_name": f"Utilisateur {email}",
    }
    client.post("/auth/register", json=user)
    login = client.post("/auth/login", json={"email": email, "password": user["password"]})
    token = login.json()["access_token"]
    me = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
    return token, me.json()["id"]


def test_create_post_requires_authentication():
    response = client.post("/social/posts", json={"content": "Bonjour"})
    assert response.status_code == 401


def test_create_and_read_post():
    token, _ = _register_and_login("fatou@example.com")
    headers = {"Authorization": f"Bearer {token}"}
    response = client.post("/social/posts", json={"content": "Ma première publication"}, headers=headers)
    assert response.status_code == 201
    body = response.json()
    assert body["content"] == "Ma première publication"
    assert body["likes_count"] == 0
    assert body["comments_count"] == 0


def test_empty_post_rejected():
    token, _ = _register_and_login("koffi@example.com")
    headers = {"Authorization": f"Bearer {token}"}
    response = client.post("/social/posts", json={"content": "   "}, headers=headers)
    assert response.status_code == 422


def test_like_toggle():
    token, _ = _register_and_login("nadia@example.com")
    headers = {"Authorization": f"Bearer {token}"}
    post = client.post("/social/posts", json={"content": "Un post"}, headers=headers).json()

    like_response = client.post(f"/social/posts/{post['id']}/like", headers=headers)
    assert like_response.json() == {"liked": True, "likes_count": 1}

    unlike_response = client.post(f"/social/posts/{post['id']}/like", headers=headers)
    assert unlike_response.json() == {"liked": False, "likes_count": 0}


def test_comment_on_post():
    token, _ = _register_and_login("hassan@example.com")
    headers = {"Authorization": f"Bearer {token}"}
    post = client.post("/social/posts", json={"content": "Un post"}, headers=headers).json()

    comment = client.post(
        f"/social/posts/{post['id']}/comments", json={"content": "Beau post !"}, headers=headers
    )
    assert comment.status_code == 201
    assert comment.json()["content"] == "Beau post !"

    comments = client.get(f"/social/posts/{post['id']}/comments")
    assert len(comments.json()) == 1


def test_delete_post_only_by_author():
    token_a, _ = _register_and_login("lucas@example.com")
    token_b, _ = _register_and_login("emma@example.com")
    post = client.post(
        "/social/posts", json={"content": "Post de Lucas"}, headers={"Authorization": f"Bearer {token_a}"}
    ).json()

    forbidden = client.delete(
        f"/social/posts/{post['id']}", headers={"Authorization": f"Bearer {token_b}"}
    )
    assert forbidden.status_code == 403

    allowed = client.delete(
        f"/social/posts/{post['id']}", headers={"Authorization": f"Bearer {token_a}"}
    )
    assert allowed.status_code == 204


def test_follow_and_feed():
    token_a, id_a = _register_and_login("sofia@example.com")
    token_b, id_b = _register_and_login("marco@example.com")
    headers_a = {"Authorization": f"Bearer {token_a}"}
    headers_b = {"Authorization": f"Bearer {token_b}"}

    client.post("/social/posts", json={"content": "Post de Marco"}, headers=headers_b)

    # Sofia ne suit pas encore Marco : son fil est vide
    feed_before = client.get("/social/feed", headers=headers_a).json()
    assert len(feed_before) == 0

    follow = client.post(f"/social/users/{id_b}/follow", headers=headers_a)
    assert follow.status_code == 200
    assert follow.json()["is_following"] is True

    feed_after = client.get("/social/feed", headers=headers_a).json()
    assert len(feed_after) == 1
    assert feed_after[0]["content"] == "Post de Marco"


def test_cannot_follow_self():
    token, user_id = _register_and_login("zara@example.com")
    headers = {"Authorization": f"Bearer {token}"}
    response = client.post(f"/social/users/{user_id}/follow", headers=headers)
    assert response.status_code == 400


def test_private_post_hidden_from_non_followers():
    token_a, id_a = _register_and_login("ines@example.com")
    token_b, _ = _register_and_login("paul@example.com")
    client.post(
        "/social/posts",
        json={"content": "Post privé", "visibility": "private"},
        headers={"Authorization": f"Bearer {token_a}"},
    )
    visible_to_b = client.get(
        f"/social/users/{id_a}/posts", headers={"Authorization": f"Bearer {token_b}"}
    ).json()
    assert len(visible_to_b) == 0
