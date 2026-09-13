"""
Tests du système d'évaluation obligatoire (module Éducation).
Nécessitent : pip install -r requirements.txt
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


def _register_and_login(email: str) -> str:
    user = {"email": email, "password": "MotDePasse123", "full_name": f"Utilisateur {email}"}
    client.post("/auth/register", json=user)
    login = client.post("/auth/login", json={"email": email, "password": user["password"]})
    return login.json()["access_token"]


def _publish_course(course_id: str) -> None:
    db = TestSessionLocal()
    course = db.query(Course).filter(Course.id == course_id).first()
    course.is_published = True
    db.commit()
    db.close()


COURSE = {
    "title": "Bases de la comptabilité pour PME",
    "description": "Un cours pratique sur les fondamentaux de la comptabilité d'entreprise.",
    "discipline": "commerce",
    "level": "debutant",
}

ASSESSMENT = {
    "title": "Évaluation finale - Comptabilité",
    "passing_score_percent": 50.0,
    "questions": [
        {
            "text": "Que signifie l'acronyme 'TVA' ?",
            "order_index": 0,
            "options": [
                {"text": "Taxe sur la Valeur Ajoutée", "is_correct": True},
                {"text": "Taux Variable Annuel", "is_correct": False},
            ],
        },
        {
            "text": "Un bilan comptable présente...",
            "order_index": 1,
            "options": [
                {"text": "Les recettes du mois", "is_correct": False},
                {"text": "L'actif et le passif d'une entreprise", "is_correct": True},
            ],
        },
    ],
}


def _setup_course_with_assessment(author_email: str, student_email: str):
    author_token = _register_and_login(author_email)
    course = client.post(
        "/education/courses", json=COURSE, headers={"Authorization": f"Bearer {author_token}"}
    ).json()
    client.post(
        f"/education/courses/{course['id']}/lessons",
        json={"title": "Leçon unique", "content": "Contenu suffisamment long pour la validation.", "order_index": 0},
        headers={"Authorization": f"Bearer {author_token}"},
    )
    client.post(
        f"/education/courses/{course['id']}/assessment",
        json=ASSESSMENT,
        headers={"Authorization": f"Bearer {author_token}"},
    )
    _publish_course(course["id"])

    student_token = _register_and_login(student_email)
    headers = {"Authorization": f"Bearer {student_token}"}
    client.post(f"/education/courses/{course['id']}/enroll", headers=headers)
    lessons = client.get(f"/education/courses/{course['id']}/lessons", headers=headers).json()
    client.post(f"/education/courses/{course['id']}/lessons/{lessons[0]['id']}/complete", headers=headers)

    return course, headers


def test_assessment_requires_exactly_one_correct_option():
    author_token = _register_and_login("createur1@example.com")
    course = client.post(
        "/education/courses", json=COURSE, headers={"Authorization": f"Bearer {author_token}"}
    ).json()
    bad_assessment = {
        **ASSESSMENT,
        "questions": [
            {
                "text": "Question invalide",
                "order_index": 0,
                "options": [
                    {"text": "A", "is_correct": True},
                    {"text": "B", "is_correct": True},
                ],
            }
        ],
    }
    response = client.post(
        f"/education/courses/{course['id']}/assessment",
        json=bad_assessment,
        headers={"Authorization": f"Bearer {author_token}"},
    )
    assert response.status_code == 422


def test_only_one_assessment_per_course():
    author_token = _register_and_login("createur2@example.com")
    course = client.post(
        "/education/courses", json=COURSE, headers={"Authorization": f"Bearer {author_token}"}
    ).json()
    headers = {"Authorization": f"Bearer {author_token}"}
    client.post(f"/education/courses/{course['id']}/assessment", json=ASSESSMENT, headers=headers)
    second = client.post(f"/education/courses/{course['id']}/assessment", json=ASSESSMENT, headers=headers)
    assert second.status_code == 409


def test_student_view_never_reveals_correct_answers():
    course, headers = _setup_course_with_assessment("createur3@example.com", "etudiant_eval1@example.com")
    assessment = client.get(f"/education/courses/{course['id']}/assessment", headers=headers).json()
    assert "is_correct" not in str(assessment)


def test_course_not_completed_without_passing_assessment():
    course, headers = _setup_course_with_assessment("createur4@example.com", "etudiant_eval2@example.com")

    progress = client.get(f"/education/courses/{course['id']}/progress", headers=headers).json()
    assert progress["progress_percent"] == 100.0
    assert progress["has_mandatory_assessment"] is True
    assert progress["is_course_completed"] is False


def test_failing_assessment_keeps_course_incomplete_and_allows_retake():
    course, headers = _setup_course_with_assessment("createur5@example.com", "etudiant_eval3@example.com")
    assessment = client.get(f"/education/courses/{course['id']}/assessment", headers=headers).json()

    # Réponses volontairement toutes fausses.
    wrong_submission = {
        "answers": [
            {
                "question_id": assessment["questions"][0]["id"],
                "selected_option_id": assessment["questions"][0]["options"][1]["id"],
            },
            {
                "question_id": assessment["questions"][1]["id"],
                "selected_option_id": assessment["questions"][1]["options"][0]["id"],
            },
        ]
    }
    attempt1 = client.post(
        f"/education/courses/{course['id']}/assessment/submit", json=wrong_submission, headers=headers
    )
    assert attempt1.status_code == 201
    assert attempt1.json()["score_percent"] == 0.0
    assert attempt1.json()["passed"] is False
    assert attempt1.json()["attempt_number"] == 1

    progress_after_fail = client.get(f"/education/courses/{course['id']}/progress", headers=headers).json()
    assert progress_after_fail["is_course_completed"] is False

    # Reprise avec les bonnes réponses cette fois.
    correct_submission = {
        "answers": [
            {
                "question_id": assessment["questions"][0]["id"],
                "selected_option_id": assessment["questions"][0]["options"][0]["id"],
            },
            {
                "question_id": assessment["questions"][1]["id"],
                "selected_option_id": assessment["questions"][1]["options"][1]["id"],
            },
        ]
    }
    attempt2 = client.post(
        f"/education/courses/{course['id']}/assessment/submit", json=correct_submission, headers=headers
    )
    assert attempt2.json()["score_percent"] == 100.0
    assert attempt2.json()["passed"] is True
    assert attempt2.json()["attempt_number"] == 2

    progress_after_pass = client.get(f"/education/courses/{course['id']}/progress", headers=headers).json()
    assert progress_after_pass["is_course_completed"] is True
    assert progress_after_pass["assessment_passed"] is True


def test_attempts_history_is_tracked():
    course, headers = _setup_course_with_assessment("createur6@example.com", "etudiant_eval4@example.com")
    assessment = client.get(f"/education/courses/{course['id']}/assessment", headers=headers).json()
    submission = {
        "answers": [
            {
                "question_id": assessment["questions"][0]["id"],
                "selected_option_id": assessment["questions"][0]["options"][0]["id"],
            },
            {
                "question_id": assessment["questions"][1]["id"],
                "selected_option_id": assessment["questions"][1]["options"][1]["id"],
            },
        ]
    }
    client.post(f"/education/courses/{course['id']}/assessment/submit", json=submission, headers=headers)
    client.post(f"/education/courses/{course['id']}/assessment/submit", json=submission, headers=headers)

    attempts = client.get(f"/education/courses/{course['id']}/assessment/attempts", headers=headers).json()
    assert len(attempts) == 2
    assert attempts[0]["attempt_number"] == 1
    assert attempts[1]["attempt_number"] == 2
