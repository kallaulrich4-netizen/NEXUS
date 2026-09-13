from datetime import datetime

from pydantic import BaseModel, ConfigDict, field_validator


class MessageOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    role: str
    content: str
    created_at: datetime


class ConversationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    title: str
    created_at: datetime
    updated_at: datetime


class ConversationDetailOut(ConversationOut):
    messages: list[MessageOut] = []


class SendMessageRequest(BaseModel):
    content: str
    conversation_id: str | None = None  # None => crée une nouvelle conversation

    @field_validator("content")
    @classmethod
    def content_not_empty(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("Le message ne peut pas être vide.")
        if len(cleaned) > 8000:
            raise ValueError("Le message dépasse la longueur maximale autorisée.")
        return cleaned


class SendMessageResponse(BaseModel):
    conversation_id: str
    user_message: MessageOut
    assistant_message: MessageOut
