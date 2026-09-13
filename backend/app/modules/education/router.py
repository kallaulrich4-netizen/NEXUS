from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.rate_limit import rate_limit
from app.modules.auth.router import get_current_user
from app.modules.auth.models import User
from app.modules.education import service
from app.modules.education.models import SUGGESTED_DISCIPLINES
from app.modules.education.schemas import (
    CourseCreate, CourseOut, CourseListOut,
    LessonCreate, LessonOut,
    EnrollmentOut, CourseProgress,
    AssessmentCreate, AssessmentForStudent, AssessmentSubmission, AssessmentAttemptOut,
)

router = APIRouter(prefix="/education", tags=["Éducation"])


@router.get("/disciplines/suggestions", response_model=list[str])
def get_discipline_suggestions():
    """Suggestions pour l'interface — toute autre discipline reste acceptée à la création."""
    return SUGGESTED_DISCIPLINES


# --- Cours ---

@router.post(
    "/courses",
    response_model=CourseOut,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(rate_limit(max_requests=10, window_seconds=60))],
)
def submit_course(
    data: CourseCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return service.submit_course(db, current_user.id, data)


@router.get("/courses/search", response_model=list[CourseListOut])
def search_courses(
    discipline: str | None = Query(None),
    level: str | None = Query(None),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
):
    return service.search_published_courses(db, discipline=discipline, level=level, limit=limit, offset=offset)


@router.get("/courses/mine", response_model=list[CourseOut])
def list_my_authored_courses(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return service.list_my_authored_courses(db, current_user.id)


@router.get("/courses/{course_id}", response_model=CourseOut)
def get_course(course_id: str, db: Session = Depends(get_db)):
    try:
        return service.get_published_course(db, course_id)
    except service.CourseNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))


# --- Leçons (gestion, réservée à l'auteur) ---

@router.post(
    "/courses/{course_id}/lessons",
    response_model=LessonOut,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(rate_limit(max_requests=30, window_seconds=60))],
)
def add_lesson(
    course_id: str,
    data: LessonCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        return service.add_lesson(db, course_id, current_user.id, data)
    except service.CourseNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))


# --- Inscriptions et progression ---

@router.post(
    "/courses/{course_id}/enroll",
    response_model=EnrollmentOut,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(rate_limit(max_requests=20, window_seconds=60))],
)
def enroll_in_course(
    course_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        return service.enroll_in_course(db, current_user, course_id)
    except service.CourseNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    except service.PremiumRequiredError as exc:
        raise HTTPException(status_code=status.HTTP_402_PAYMENT_REQUIRED, detail=str(exc))
    except service.AlreadyEnrolledError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))


@router.get("/enrollments/mine", response_model=list[EnrollmentOut])
def list_my_enrollments(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return service.list_my_enrollments(db, current_user.id)


@router.get("/courses/{course_id}/lessons", response_model=list[LessonOut])
def get_course_lessons(
    course_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Contenu des leçons — réservé aux étudiants inscrits au cours."""
    try:
        return service.get_course_lessons(db, course_id, current_user.id)
    except service.NotEnrolledError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc))


@router.post("/courses/{course_id}/lessons/{lesson_id}/complete", status_code=status.HTTP_204_NO_CONTENT)
def mark_lesson_complete(
    course_id: str,
    lesson_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        service.mark_lesson_complete(db, course_id, lesson_id, current_user.id)
    except service.NotEnrolledError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc))
    except service.LessonNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))


@router.get("/courses/{course_id}/progress", response_model=CourseProgress)
def get_course_progress(
    course_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        return service.get_course_progress(db, course_id, current_user.id)
    except service.NotEnrolledError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc))


# --- Évaluations obligatoires ---

@router.post(
    "/courses/{course_id}/assessment",
    response_model=AssessmentForStudent,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(rate_limit(max_requests=10, window_seconds=60))],
)
def create_assessment(
    course_id: str,
    data: AssessmentCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Réservé à l'auteur du cours. Une seule évaluation autorisée par cours."""
    try:
        return service.create_assessment(db, course_id, current_user.id, data)
    except service.CourseNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    except service.AssessmentAlreadyExistsError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))


@router.get("/courses/{course_id}/assessment", response_model=AssessmentForStudent)
def get_assessment(
    course_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Retourne les questions SANS révéler les bonnes réponses."""
    try:
        return service.get_assessment_for_student(db, course_id, current_user.id)
    except service.NotEnrolledError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc))
    except service.AssessmentNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))


@router.post(
    "/courses/{course_id}/assessment/submit",
    response_model=AssessmentAttemptOut,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(rate_limit(max_requests=10, window_seconds=60))],
)
def submit_assessment(
    course_id: str,
    data: AssessmentSubmission,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Corrige la tentative et retourne le score. Si le seuil de réussite
    n'est pas atteint, l'étudiant peut soumettre une nouvelle tentative
    autant de fois que nécessaire — le cours ne sera marqué terminé
    qu'après une tentative réussie.
    """
    try:
        return service.submit_assessment_attempt(db, course_id, current_user.id, data)
    except service.NotEnrolledError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc))
    except service.AssessmentNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    except service.InvalidSubmissionError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))


@router.get("/courses/{course_id}/assessment/attempts", response_model=list[AssessmentAttemptOut])
def list_my_attempts(
    course_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        return service.list_my_attempts(db, course_id, current_user.id)
    except service.AssessmentNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
