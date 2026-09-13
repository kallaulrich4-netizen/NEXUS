"""
Tests du module Éducation. Nécessitent : pip install -r requirements.txt
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
from app.modules.education.models import Course

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


def _publish_course(course_id: str) -> None:
    db = TestSessionLocal()
    course = db.query(Course).filter(Course.id == course_id).first()
    course.is_published = True
    db.commit()
    db.close()


COURSE = {
    "title": "Introduction à la cybersécurité pour débutants",
    "description": "Un cours d'introduction couvrant les bases de la sécurité informatique.",
    "discipline": "cybersecurite",
    "level": "debutant",
}


def test_course_not_published_by_default():
    token, _ = _register_and_login("prof1@example.com")
    response = client.post("/education/courses", json=COURSE, headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 201
    assert response.json()["is_published"] is False


def test_unpublished_course_not_searchable():
    token, _ = _register_and_login("prof2@example.com")
    client.post("/education/courses", json=COURSE, headers={"Authorization": f"Bearer {token}"})
    results = client.get("/education/courses/search").json()
    assert len(results) == 0


def test_discipline_is_free_text():
    token, _ = _register_and_login("prof3@example.com")
    response = client.post(
        "/education/courses",
        json={**COURSE, "discipline": "apiculture_avancee", "title": "Apiculture avancée pour tous"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 201
    assert response.json()["discipline"] == "apiculture_avancee"


def test_only_author_can_add_lessons():
    token_a, _ = _register_and_login("prof4@example.com")
    token_b, _ = _register_and_login("prof5@example.com")
    course = client.post(
        "/education/courses", json=COURSE, headers={"Authorization": f"Bearer {token_a}"}
    ).json()

    response = client.post(
        f"/education/courses/{course['id']}/lessons",
        json={"title": "Leçon 1", "content": "Contenu suffisamment long pour la validation.", "order_index": 0},
        headers={"Authorization": f"Bearer {token_b}"},
    )
    assert response.status_code == 404


def test_lessons_require_enrollment():
    author_token, _ = _register_and_login("prof6@example.com")
    course = client.post(
        "/education/courses", json=COURSE, headers={"Authorization": f"Bearer {author_token}"}
    ).json()
    client.post(
        f"/education/courses/{course['id']}/lessons",
        json={"title": "Leçon 1", "content": "Contenu suffisamment long pour la validation.", "order_index": 0},
        headers={"Authorization": f"Bearer {author_token}"},
    )
    _publish_course(course["id"])

    student_token, _ = _register_and_login("etudiant1@example.com")
    response = client.get(
        f"/education/courses/{course['id']}/lessons", headers={"Authorization": f"Bearer {student_token}"}
    )
    assert response.status_code == 403


def test_full_enrollment_and_progress_workflow():
    author_token, _ = _register_and_login("prof7@example.com")
    course = client.post(
        "/education/courses", json=COURSE, headers={"Authorization": f"Bearer {author_token}"}
    ).json()
    lesson1 = client.post(
        f"/education/courses/{course['id']}/lessons",
        json={"title": "Leçon 1", "content": "Contenu suffisamment long pour la validation.", "order_index": 0},
        headers={"Authorization": f"Bearer {author_token}"},
    ).json()
    lesson2 = client.post(
        f"/education/courses/{course['id']}/lessons",
        json={"title": "Leçon 2", "content": "Autre contenu suffisamment long pour valider.", "order_index": 1},
        headers={"Authorization": f"Bearer {author_token}"},
    ).json()
    _publish_course(course["id"])

    student_token, _ = _register_and_login("etudiant2@example.com")
    headers = {"Authorization": f"Bearer {student_token}"}

    enroll = client.post(f"/education/courses/{course['id']}/enroll", headers=headers)
    assert enroll.status_code == 201

    lessons = client.get(f"/education/courses/{course['id']}/lessons", headers=headers).json()
    assert len(lessons) == 2

    progress_before = client.get(f"/education/courses/{course['id']}/progress", headers=headers).json()
    assert progress_before["progress_percent"] == 0.0

    client.post(f"/education/courses/{course['id']}/lessons/{lesson1['id']}/complete", headers=headers)
    progress_mid = client.get(f"/education/courses/{course['id']}/progress", headers=headers).json()
    assert progress_mid["progress_percent"] == 50.0
    assert progress_mid["is_course_completed"] is False

    client.post(f"/education/courses/{course['id']}/lessons/{lesson2['id']}/complete", headers=headers)
    progress_final = client.get(f"/education/courses/{course['id']}/progress", headers=headers).json()
    assert progress_final["progress_percent"] == 100.0
    assert progress_final["is_course_completed"] is True


def test_cannot_enroll_twice():
    author_token, _ = _register_and_login("prof8@example.com")
    course = client.post(
        "/education/courses", json=COURSE, headers={"Authorization": f"Bearer {author_token}"}
    ).json()
    _publish_course(course["id"])

    student_token, _ = _register_and_login("etudiant3@example.com")
    headers = {"Authorization": f"Bearer {student_token}"}
    client.post(f"/education/courses/{course['id']}/enroll", headers=headers)
    second = client.post(f"/education/courses/{course['id']}/enroll", headers=headers)
    assert second.status_code == 409


def test_premium_course_blocked_after_trial_expires():
    author_token, _ = _register_and_login("prof9@example.com")
    course = client.post(
        "/education/courses",
        json={**COURSE, "is_premium": True},
        headers={"Authorization": f"Bearer {author_token}"},
    ).json()
    _publish_course(course["id"])

    student_token, student_id = _register_and_login("etudiant4@example.com")
    _expire_trial(student_id)

    response = client.post(
        f"/education/courses/{course['id']}/enroll", headers={"Authorization": f"Bearer {student_token}"}
    )
    assert response.status_code == 402


def test_premium_course_accessible_during_trial():
    author_token, _ = _register_and_login("prof10@example.com")
    course = client.post(
        "/education/courses",
        json={**COURSE, "is_premium": True},
        headers={"Authorization": f"Bearer {author_token}"},
    ).json()
    _publish_course(course["id"])

    student_token, _ = _register_and_login("etudiant5@example.com")
    response = client.post(
        f"/education/courses/{course['id']}/enroll", headers={"Authorization": f"Bearer {student_token}"}
    )
    assert response.status_code == 201
