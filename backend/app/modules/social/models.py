"""
Modèles du module Réseau social.

Comme pour le module IA, chaque table pointe vers `users.id`, ce qui
garantit que le réseau social utilise le même compte que tout le reste
de la plateforme Nexus.
"""
import uuid
from datetime import datetime, timezone

from sqlalchemy import String, DateTime, ForeignKey, Text, UniqueConstraint, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


def generate_uuid() -> str:
    return str(uuid.uuid4())


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Post(Base):
    __tablename__ = "social_posts"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    author_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), nullable=False, index=True)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    # URL vers un média déjà hébergé (image/vidéo). Le stockage réel des
    # fichiers sera géré par un service de stockage dédié, pas cette table.
    media_url: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    visibility: Mapped[str] = mapped_column(String(20), default="public")  # public | followers | private

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    comments: Mapped[list["Comment"]] = relationship(back_populates="post", cascade="all, delete-orphan")
    likes: Mapped[list["Like"]] = relationship(back_populates="post", cascade="all, delete-orphan")

    __table_args__ = (Index("ix_social_posts_author_created", "author_id", "created_at"),)


class Comment(Base):
    __tablename__ = "social_comments"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    post_id: Mapped[str] = mapped_column(String(36), ForeignKey("social_posts.id"), nullable=False, index=True)
    author_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), nullable=False, index=True)
    content: Mapped[str] = mapped_column(Text, nullable=False)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    post: Mapped["Post"] = relationship(back_populates="comments")


class Like(Base):
    __tablename__ = "social_likes"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    post_id: Mapped[str] = mapped_column(String(36), ForeignKey("social_posts.id"), nullable=False, index=True)
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), nullable=False, index=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    post: Mapped["Post"] = relationship(back_populates="likes")

    __table_args__ = (UniqueConstraint("post_id", "user_id", name="uq_like_post_user"),)


class Follow(Base):
    """Relation d'abonnement : `follower_id` suit `followed_id`."""

    __tablename__ = "social_follows"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    follower_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), nullable=False, index=True)
    followed_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), nullable=False, index=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    __table_args__ = (UniqueConstraint("follower_id", "followed_id", name="uq_follow_pair"),)
