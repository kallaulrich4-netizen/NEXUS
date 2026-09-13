from datetime import datetime

from pydantic import BaseModel, ConfigDict, field_validator


class PostCreate(BaseModel):
    content: str
    media_url: str | None = None
    visibility: str = "public"

    @field_validator("content")
    @classmethod
    def content_not_empty(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("La publication ne peut pas être vide.")
        if len(cleaned) > 5000:
            raise ValueError("La publication dépasse la longueur maximale autorisée.")
        return cleaned

    @field_validator("visibility")
    @classmethod
    def visibility_valid(cls, value: str) -> str:
        allowed = {"public", "followers", "private"}
        if value not in allowed:
            raise ValueError(f"La visibilité doit être l'une de : {', '.join(allowed)}.")
        return value


class AuthorOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    full_name: str


class PostOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    author_id: str
    content: str
    media_url: str | None
    visibility: str
    created_at: datetime
    updated_at: datetime
    likes_count: int = 0
    comments_count: int = 0
    liked_by_current_user: bool = False


class CommentCreate(BaseModel):
    content: str

    @field_validator("content")
    @classmethod
    def content_not_empty(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("Le commentaire ne peut pas être vide.")
        if len(cleaned) > 2000:
            raise ValueError("Le commentaire dépasse la longueur maximale autorisée.")
        return cleaned


class CommentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    post_id: str
    author_id: str
    content: str
    created_at: datetime


class FollowOut(BaseModel):
    is_following: bool
    followers_count: int
    following_count: int
