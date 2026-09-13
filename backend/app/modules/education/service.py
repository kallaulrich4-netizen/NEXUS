from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.core.entitlements import has_premium_access
from app.modules.auth.models import User
from app.modules.education.models import Course, Lesson, Enrollment, LessonCompletion, Assessment, Question, AnswerOption, AssessmentAttempt


class CourseNotFoundError(Exception):
    """Levée quand un cours n'existe pas, n'est pas publié, ou n'appartient pas à l'auteur demandé."""


class NotAuthorError(Exception):
    """Levée quand un utilisateur tente de modifier un cours qui n'est pas le sien."""


class PremiumRequiredError(Exception):
    """Levée quand un cours premium est demandé sans accès actif."""


class AlreadyEnrolledError(Exception):
    """Levée quand un étudiant tente de s'inscrire deux fois au même cours."""


class NotEnrolledError(Exception):
    """Levée quand un étudiant tente d'accéder au contenu d'un cours sans y être inscrit."""


class LessonNotFoundError(Exception):
    """Levée quand une leçon n'existe pas ou n'appartient pas au cours indiqué."""


class AssessmentAlreadyExistsError(Exception):
    """Levée quand une évaluation existe déjà pour ce cours (une seule autorisée)."""


class AssessmentNotFoundError(Exception):
    """Levée quand un cours n'a pas d'évaluation obligatoire."""


class InvalidSubmissionError(Exception):
    """Levée quand une soumission d'évaluation référence des questions/options invalides."""


# --- Cours ---

def submit_course(db: Session, author_id: str, data) -> Course:
    course = Course(author_id=author_id, is_reviewed=False, is_published=False, **data.model_dump())
    db.add(course)
    db.commit()
    db.refresh(course)
    return course


def get_published_course(db: Session, course_id: str) -> Course:
    course = db.query(Course).filter(Course.id == course_id, Course.is_published.is_(True)).first()
    if course is None:
        raise CourseNotFoundError("Cours introuvable ou non publié.")
    return course


def search_published_courses(
    db: Session, discipline: str | None = None, level: str | None = None, limit: int = 20, offset: int = 0
) -> list[Course]:
    q = db.query(Course).filter(Course.is_published.is_(True))
    if discipline:
        q = q.filter(Course.discipline == discipline)
    if level:
        q = q.filter(Course.level == level)
    return q.order_by(Course.created_at.desc()).offset(offset).limit(limit).all()


def list_my_authored_courses(db: Session, author_id: str) -> list[Course]:
    return db.query(Course).filter(Course.author_id == author_id).order_by(Course.created_at.desc()).all()


def _get_course_for_author(db: Session, course_id: str, author_id: str) -> Course:
    course = db.query(Course).filter(Course.id == course_id, Course.author_id == author_id).first()
    if course is None:
        raise CourseNotFoundError("Cours introuvable.")
    return course


# --- Leçons ---

def add_lesson(db: Session, course_id: str, author_id: str, data) -> Lesson:
    _get_course_for_author(db, course_id, author_id)  # seul l'auteur peut ajouter des leçons
    lesson = Lesson(course_id=course_id, **data.model_dump())
    db.add(lesson)
    db.commit()
    db.refresh(lesson)
    return lesson


# --- Inscriptions ---

def enroll_in_course(db: Session, student: User, course_id: str) -> Enrollment:
    course = get_published_course(db, course_id)

    if course.is_premium and not has_premium_access(student):
        raise PremiumRequiredError(
            "Ce cours est réservé aux comptes premium ou en période d'essai active."
        )

    existing = (
        db.query(Enrollment)
        .filter(Enrollment.student_id == student.id, Enrollment.course_id == course_id)
        .first()
    )
    if existing is not None:
        raise AlreadyEnrolledError("Vous êtes déjà inscrit à ce cours.")

    enrollment = Enrollment(student_id=student.id, course_id=course_id)
    db.add(enrollment)
    db.commit()
    db.refresh(enrollment)
    return enrollment


def list_my_enrollments(db: Session, student_id: str) -> list[Enrollment]:
    return (
        db.query(Enrollment)
        .filter(Enrollment.student_id == student_id)
        .order_by(Enrollment.enrolled_at.desc())
        .all()
    )


def _get_enrollment(db: Session, course_id: str, student_id: str) -> Enrollment:
    enrollment = (
        db.query(Enrollment)
        .filter(Enrollment.course_id == course_id, Enrollment.student_id == student_id)
        .first()
    )
    if enrollment is None:
        raise NotEnrolledError("Vous devez être inscrit à ce cours pour accéder à son contenu.")
    return enrollment


def get_course_lessons(db: Session, course_id: str, student_id: str) -> list[Lesson]:
    """Le contenu des leçons n'est accessible qu'aux étudiants inscrits."""
    _get_enrollment(db, course_id, student_id)
    return (
        db.query(Lesson)
        .filter(Lesson.course_id == course_id)
        .order_by(Lesson.order_index)
        .all()
    )


def mark_lesson_complete(db: Session, course_id: str, lesson_id: str, student_id: str) -> None:
    enrollment = _get_enrollment(db, course_id, student_id)

    lesson = db.query(Lesson).filter(Lesson.id == lesson_id, Lesson.course_id == course_id).first()
    if lesson is None:
        raise LessonNotFoundError("Leçon introuvable pour ce cours.")

    existing = (
        db.query(LessonCompletion)
        .filter(LessonCompletion.enrollment_id == enrollment.id, LessonCompletion.lesson_id == lesson_id)
        .first()
    )
    if existing is None:
        db.add(LessonCompletion(enrollment_id=enrollment.id, lesson_id=lesson_id))
        db.commit()

    _update_completion_status(db, enrollment)


def _update_completion_status(db: Session, enrollment: Enrollment) -> None:
    """
    Un cours n'est marqué terminé que si TOUTES les leçons sont vues ET,
    s'il existe une évaluation obligatoire, qu'elle a été réussie. Voir
    `submit_assessment_attempt` pour l'autre déclencheur de ce contrôle.
    """
    total_lessons = db.query(Lesson).filter(Lesson.course_id == enrollment.course_id).count()
    completed_lessons = (
        db.query(LessonCompletion).filter(LessonCompletion.enrollment_id == enrollment.id).count()
    )
    if total_lessons == 0 or completed_lessons < total_lessons:
        return

    assessment = db.query(Assessment).filter(Assessment.course_id == enrollment.course_id).first()
    if assessment is not None:
        passed_attempt = (
            db.query(AssessmentAttempt)
            .filter(
                AssessmentAttempt.assessment_id == assessment.id,
                AssessmentAttempt.student_id == enrollment.student_id,
                AssessmentAttempt.passed.is_(True),
            )
            .first()
        )
        if passed_attempt is None:
            return  # leçons finies mais évaluation pas encore réussie : cours PAS terminé

    if enrollment.completed_at is None:
        enrollment.completed_at = datetime.now(timezone.utc)
        db.commit()


def get_course_progress(db: Session, course_id: str, student_id: str) -> dict:
    enrollment = _get_enrollment(db, course_id, student_id)
    total_lessons = db.query(Lesson).filter(Lesson.course_id == course_id).count()
    completed_lessons = (
        db.query(LessonCompletion).filter(LessonCompletion.enrollment_id == enrollment.id).count()
    )
    progress_percent = (completed_lessons / total_lessons * 100) if total_lessons > 0 else 0.0

    assessment = db.query(Assessment).filter(Assessment.course_id == course_id).first()
    assessment_passed = None
    if assessment is not None:
        assessment_passed = (
            db.query(AssessmentAttempt)
            .filter(
                AssessmentAttempt.assessment_id == assessment.id,
                AssessmentAttempt.student_id == student_id,
                AssessmentAttempt.passed.is_(True),
            )
            .first()
            is not None
        )

    return {
        "course_id": course_id,
        "total_lessons": total_lessons,
        "completed_lessons": completed_lessons,
        "progress_percent": round(progress_percent, 1),
        "is_course_completed": enrollment.completed_at is not None,
        "has_mandatory_assessment": assessment is not None,
        "assessment_passed": assessment_passed,
    }


# --- Évaluations obligatoires ---

def create_assessment(db: Session, course_id: str, author_id: str, data) -> Assessment:
    """Une seule évaluation par cours (contrainte unique en base)."""
    _get_course_for_author(db, course_id, author_id)

    existing = db.query(Assessment).filter(Assessment.course_id == course_id).first()
    if existing is not None:
        raise AssessmentAlreadyExistsError("Ce cours a déjà une évaluation. Modifiez-la plutôt que d'en recréer une.")

    assessment = Assessment(course_id=course_id, title=data.title, passing_score_percent=data.passing_score_percent)
    for q_data in data.questions:
        question = Question(text=q_data.text, order_index=q_data.order_index)
        for o_data in q_data.options:
            question.options.append(AnswerOption(text=o_data.text, is_correct=o_data.is_correct))
        assessment.questions.append(question)

    db.add(assessment)
    db.commit()
    db.refresh(assessment)
    return assessment


def get_assessment_for_student(db: Session, course_id: str, student_id: str) -> Assessment:
    """Vérifie l'inscription, puis retourne l'évaluation SANS révéler les bonnes réponses (voir schémas)."""
    _get_enrollment(db, course_id, student_id)
    assessment = db.query(Assessment).filter(Assessment.course_id == course_id).first()
    if assessment is None:
        raise AssessmentNotFoundError("Ce cours n'a pas d'évaluation obligatoire.")
    return assessment


def submit_assessment_attempt(db: Session, course_id: str, student_id: str, data) -> AssessmentAttempt:
    enrollment = _get_enrollment(db, course_id, student_id)
    assessment = db.query(Assessment).filter(Assessment.course_id == course_id).first()
    if assessment is None:
        raise AssessmentNotFoundError("Ce cours n'a pas d'évaluation obligatoire.")

    question_ids = {q.id for q in assessment.questions}
    submitted_question_ids = {a.question_id for a in data.answers}
    if not submitted_question_ids.issubset(question_ids):
        raise InvalidSubmissionError("Une ou plusieurs questions soumises n'appartiennent pas à cette évaluation.")

    correct_count = 0
    for answer in data.answers:
        selected_option = (
            db.query(AnswerOption)
            .filter(AnswerOption.id == answer.selected_option_id, AnswerOption.question_id == answer.question_id)
            .first()
        )
        if selected_option is None:
            raise InvalidSubmissionError(
                f"L'option sélectionnée pour la question {answer.question_id} est invalide."
            )
        if selected_option.is_correct:
            correct_count += 1

    total_questions = len(assessment.questions)
    score_percent = (correct_count / total_questions * 100) if total_questions > 0 else 0.0
    passed = score_percent >= assessment.passing_score_percent

    previous_attempts = (
        db.query(AssessmentAttempt)
        .filter(AssessmentAttempt.assessment_id == assessment.id, AssessmentAttempt.student_id == student_id)
        .count()
    )

    attempt = AssessmentAttempt(
        assessment_id=assessment.id,
        student_id=student_id,
        attempt_number=previous_attempts + 1,
        score_percent=round(score_percent, 1),
        passed=passed,
    )
    db.add(attempt)
    db.commit()
    db.refresh(attempt)

    # Réévalue si le cours peut désormais être marqué terminé (reprise réussie après échec).
    _update_completion_status(db, enrollment)

    return attempt


def list_my_attempts(db: Session, course_id: str, student_id: str) -> list[AssessmentAttempt]:
    assessment = db.query(Assessment).filter(Assessment.course_id == course_id).first()
    if assessment is None:
        raise AssessmentNotFoundError("Ce cours n'a pas d'évaluation obligatoire.")
    return (
        db.query(AssessmentAttempt)
        .filter(AssessmentAttempt.assessment_id == assessment.id, AssessmentAttempt.student_id == student_id)
        .order_by(AssessmentAttempt.attempt_number)
        .all()
    )
