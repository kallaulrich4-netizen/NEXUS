"""
Modèles du module Éducation.

`discipline` est un champ TEXTE LIBRE, comme `species` (Élevage) et
`sector` (Gestion d'entreprise) : primaire, secondaire, université,
formation professionnelle, informatique, médecine, droit, ingénierie,
langues, intelligence artificielle, cybersécurité, ou absolument toute
autre discipline sont couvertes sans exception et sans modification de
code. Les cours suivent le même système premium/gratuit que le Studio
créatif (essai de 24h puis abonnement), via `has_premium_access`.
"""
import uuid
from datetime import datetime, timezone

from sqlalchemy import String, DateTime, ForeignKey, Text, Integer, Boolean, Float, CheckConstraint, Index, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

COURSE_LEVELS = {"debutant", "intermediaire", "avance"}

# Suggestions pour guider l'interface — n'importe quelle autre valeur reste acceptée.
SUGGESTED_DISCIPLINES = [
    "primaire", "secondaire", "universite", "formation_professionnelle",
    "informatique", "medecine", "droit", "ingenierie", "langues",
    "intelligence_artificielle", "cybersecurite", "commerce", "arts",
]


def generate_uuid() -> str:
    return str(uuid.uuid4())


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Course(Base):
    __tablename__ = "education_courses"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    author_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), nullable=False, index=True)

    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    discipline: Mapped[str] = mapped_column(String(100), nullable=False, index=True)  # texte libre
    level: Mapped[str] = mapped_column(String(20), nullable=False)
    language: Mapped[str] = mapped_column(String(10), default="fr")

    is_premium: Mapped[bool] = mapped_column(Boolean, default=False)
    is_reviewed: Mapped[bool] = mapped_column(Boolean, default=False)
    is_published: Mapped[bool] = mapped_column(Boolean, default=False)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    lessons: Mapped[list["Lesson"]] = relationship(
        back_populates="course", cascade="all, delete-orphan", order_by="Lesson.order_index"
    )

    __table_args__ = (Index("ix_education_courses_discipline_level", "discipline", "level"),)


class Lesson(Base):
    __tablename__ = "education_lessons"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    course_id: Mapped[str] = mapped_column(String(36), ForeignKey("education_courses.id"), nullable=False, index=True)

    title: Mapped[str] = mapped_column(String(255), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    order_index: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    duration_minutes: Mapped[int | None] = mapped_column(Integer, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    course: Mapped["Course"] = relationship(back_populates="lessons")

    __table_args__ = (UniqueConstraint("course_id", "order_index", name="uq_lesson_course_order"),)


class Enrollment(Base):
    """Un utilisateur inscrit à un cours."""

    __tablename__ = "education_enrollments"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    student_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), nullable=False, index=True)
    course_id: Mapped[str] = mapped_column(String(36), ForeignKey("education_courses.id"), nullable=False, index=True)

    enrolled_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    __table_args__ = (UniqueConstraint("student_id", "course_id", name="uq_enrollment_student_course"),)


class LessonCompletion(Base):
    """Marque qu'un étudiant a terminé une leçon précise — base du calcul de progression."""

    __tablename__ = "education_lesson_completions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    enrollment_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("education_enrollments.id"), nullable=False, index=True
    )
    lesson_id: Mapped[str] = mapped_column(String(36), ForeignKey("education_lessons.id"), nullable=False, index=True)

    completed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    __table_args__ = (UniqueConstraint("enrollment_id", "lesson_id", name="uq_completion_enrollment_lesson"),)


class Assessment(Base):
    """
    Une évaluation obligatoire de fin de cours. Si elle existe pour un
    cours, l'étudiant DOIT l'atteindre le seuil de réussite pour que le
    cours soit considéré comme terminé — pas seulement avoir vu toutes
    les leçons. Reprises illimitées jusqu'à réussite, comme demandé.
    """

    __tablename__ = "education_assessments"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    course_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("education_courses.id"), nullable=False, unique=True, index=True
    )

    title: Mapped[str] = mapped_column(String(255), nullable=False)
    passing_score_percent: Mapped[float] = mapped_column(Float, nullable=False, default=50.0)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    questions: Mapped[list["Question"]] = relationship(
        back_populates="assessment", cascade="all, delete-orphan", order_by="Question.order_index"
    )

    __table_args__ = (
        CheckConstraint(
            "passing_score_percent > 0 AND passing_score_percent <= 100",
            name="ck_assessment_passing_score_range",
        ),
    )


class Question(Base):
    __tablename__ = "education_questions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    assessment_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("education_assessments.id"), nullable=False, index=True
    )

    text: Mapped[str] = mapped_column(Text, nullable=False)
    order_index: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    assessment: Mapped["Assessment"] = relationship(back_populates="questions")
    options: Mapped[list["AnswerOption"]] = relationship(back_populates="question", cascade="all, delete-orphan")

    __table_args__ = (UniqueConstraint("assessment_id", "order_index", name="uq_question_assessment_order"),)


class AnswerOption(Base):
    __tablename__ = "education_answer_options"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    question_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("education_questions.id"), nullable=False, index=True
    )

    text: Mapped[str] = mapped_column(String(500), nullable=False)
    # Jamais renvoyé à l'étudiant avant correction — voir schémas et service.
    is_correct: Mapped[bool] = mapped_column(Boolean, default=False)

    question: Mapped["Question"] = relationship(back_populates="options")


class AssessmentAttempt(Base):
    """Une tentative d'un étudiant sur une évaluation. Plusieurs tentatives possibles."""

    __tablename__ = "education_assessment_attempts"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    assessment_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("education_assessments.id"), nullable=False, index=True
    )
    student_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), nullable=False, index=True)

    attempt_number: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    score_percent: Mapped[float] = mapped_column(Float, nullable=False)
    passed: Mapped[bool] = mapped_column(Boolean, nullable=False)

    submitted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    __table_args__ = (
        Index("ix_assessment_attempts_student_assessment", "student_id", "assessment_id"),
    )
