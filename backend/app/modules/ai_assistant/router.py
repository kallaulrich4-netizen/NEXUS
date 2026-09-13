from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.database import get_db
from app.core.rate_limit import rate_limit
from app.modules.auth.router import get_current_user
from app.modules.auth.models import User
from app.modules.ai_assistant import service
from app.modules.ai_assistant.provider import AIProvider, get_ai_provider
from app.modules.ai_assistant.schemas import (
    ConversationOut,
    ConversationDetailOut,
    SendMessageRequest,
    SendMessageResponse,
)

router = APIRouter(prefix="/ai", tags=["Nexus AI"])
_settings = get_settings()


@router.get("/conversations", response_model=list[ConversationOut])
def list_conversations(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return service.list_conversations(db, current_user.id)


@router.get("/conversations/{conversation_id}", response_model=ConversationDetailOut)
def get_conversation(
    conversation_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        return service.get_conversation(db, conversation_id, current_user.id)
    except service.ConversationNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))


@router.post(
    "/messages",
    response_model=SendMessageResponse,
    dependencies=[Depends(rate_limit(max_requests=_settings.ai_rate_limit_per_minute, window_seconds=60))],
)
def send_message(
    data: SendMessageRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    provider: AIProvider = Depends(get_ai_provider),
):
    try:
        conversation, user_message, assistant_message = service.send_message(
            db=db,
            user_id=current_user.id,
            content=data.content,
            conversation_id=data.conversation_id,
            user_language=current_user.preferred_language,
            provider=provider,
        )
    except service.ConversationNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))

    return SendMessageResponse(
        conversation_id=conversation.id,
        user_message=user_message,
        assistant_message=assistant_message,
    )
