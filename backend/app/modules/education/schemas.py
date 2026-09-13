from datetime import datetime

from pydantic import BaseModel, ConfigDict, field_validator

from app.modules.education.models import COURSE_LEVELS


class CourseCreate(BaseModel):
    title: str
    description: str
    discipline: str
    level: str
    language: str = "fr"
    is_premium: bool = False

    @field_validator("title")
    @classmethod
    def title_valid(cls, value: str) -> str:
        cleaned = value.strip()
        if not (5 <= len(cleaned) <= 255):
            raise ValueError("Le titre doit contenir entre 5 et 255 caractères.")
        return cleaned

    @field_validator("description")
    @classmethod
    def description_valid(cls, value: str) -> str:
        cleaned = value.strip()
        if len(cleaned) < 20:
            raise ValueError("La description doit contenir au moins 20 caractères.")
        return cleaned

    @field_validator("discipline")
    @classmethod
    def discipline_valid(cls, value: str) -> str:
        cleaned = value.strip().lower()
        if not (2 <= len(cleaned) <= 100):
            raise ValueError("La discipline doit contenir entre 2 et 100 caractères.")
        return cleaned

    @field_validator("level")
    @classmethod
    def level_valid(cls, value: str) -> str:
        if value not in COURSE_LEVELS:
            raise ValueError(f"Niveau invalide. Niveaux valides : {', '.join(sorted(COURSE_LEVELS))}.")
        return value


class CourseOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    author_id: str
    title: str
    description: str
    discipline: str
    level: str
    language: str
    is_premium: bool
    is_reviewed: bool
    is_published: bool
    created_at: datetime
    updated_at: datetime


class CourseListOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    title: str
    discipline: str
    level: str
    language: str
    is_premium: bool
    created_at: datetime


class LessonCreate(BaseModel):
    title: str
    content: str
    order_index: int
    duration_minutes: int | None = None

    @field_validator("title")
    @classmethod
    def title_valid(cls, value: str) -> str:
        cleaned = value.strip()
        if not (2 <= len(cleaned) <= 255):
            raise ValueError("Le titre de la leçon doit contenir entre 2 et 255 caractères.")
        return cleaned

    @field_validator("content")
    @classmethod
    def content_valid(cls, value: str) -> str:
        cleaned = value.strip()
        if len(cleaned) < 20:
            raise ValueError("Le contenu de la leçon doit contenir au moins 20 caractères.")
        return cleaned

    @field_validator("order_index")
    @classmethod
    def order_non_negative(cls, value: int) -> int:
        if value < 0:
            raise ValueError("L'ordre de la leçon ne peut pas être négatif.")
        return value

    @field_validator("duration_minutes")
    @classmethod
    def duration_positive(cls, value: int | None) -> int | None:
        if value is not None and value <= 0:
            raise ValueError("La durée doit être supérieure à zéro.")
        return value


class LessonOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    course_id: str
    title: str
    content: str
    order_index: int
    duration_minutes: int | None
    created_at: datetime


class EnrollmentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    student_id: str
    course_id: str
    enrolled_at: datetime
    completed_at: datetime | None


class CourseProgress(BaseModel):
    course_id: str
    total_lessons: int
    completed_lessons: int
    progress_percent: float
    is_course_completed: bool
    has_mandatory_assessment: bool
    assessment_passed: bool | None = None


class AnswerOptionCreate(BaseModel):
    text: str
    is_correct: bool = False

    @field_validator("text")
    @classmethod
    def text_valid(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("Le texte de l'option ne peut pas être vide.")
        return cleaned


class QuestionCreate(BaseModel):
    text: str
    order_index: int
    options: list[AnswerOptionCreate]

    @field_validator("text")
    @classmethod
    def text_valid(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("Le texte de la question ne peut pas être vide.")
        return cleaned

    @field_validator("options")
    @classmethod
    def options_valid(cls, value: list[AnswerOptionCreate]) -> list[AnswerOptionCreate]:
        if len(value) < 2:
            raise ValueError("Une question doit avoir au moins 2 options de réponse.")
        if sum(1 for o in value if o.is_correct) != 1:
            raise ValueError("Une question doit avoir exactement une option correcte.")
        return value


class AssessmentCreate(BaseModel):
    title: str
    passing_score_percent: float = 50.0
    questions: list[QuestionCreate]

    @field_validator("title")
    @classmethod
    def title_valid(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("Le titre de l'évaluation ne peut pas être vide.")
        return cleaned

    @field_validator("passing_score_percent")
    @classmethod
    def passing_score_valid(cls, value: float) -> float:
        if not (0 < value <= 100):
            raise ValueError("Le seuil de réussite doit être compris entre 0 (exclu) et 100.")
        return value

    @field_validator("questions")
    @classmethod
    def questions_not_empty(cls, value: list[QuestionCreate]) -> list[QuestionCreate]:
        if not value:
            raise ValueError("Une évaluation doit contenir au moins une question.")
        return value


class AnswerOptionForStudent(BaseModel):
    """Vue étudiant : ne révèle JAMAIS quelle option est correcte avant correction."""
    id: str
    text: str


class QuestionForStudent(BaseModel):
    id: str
    text: str
    order_index: int
    options: list[AnswerOptionForStudent]


class AssessmentForStudent(BaseModel):
    id: str
    course_id: str
    title: str
    passing_score_percent: float
    questions: list[QuestionForStudent]


class SubmittedAnswer(BaseModel):
    question_id: str
    selected_option_id: str


class AssessmentSubmission(BaseModel):
    answers: list[SubmittedAnswer]

    @field_validator("answers")
    @classmethod
    def answers_not_empty(cls, value: list[SubmittedAnswer]) -> list[SubmittedAnswer]:
        if not value:
            raise ValueError("Vous devez répondre à au moins une question.")
        return value


class AssessmentAttemptOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    assessment_id: str
    student_id: str
    attempt_number: int
    score_percent: float
    passed: bool
    submitted_at: datetime
