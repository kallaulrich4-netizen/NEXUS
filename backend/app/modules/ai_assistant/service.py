from sqlalchemy.orm import Session

from app.modules.ai_assistant.models import Conversation, Message
from app.modules.ai_assistant.provider import AIProvider


class ConversationNotFoundError(Exception):
    """Levée quand une conversation n'existe pas ou n'appartient pas à l'utilisateur."""


def get_conversation(db: Session, conversation_id: str, user_id: str) -> Conversation:
    conversation = (
        db.query(Conversation)
        .filter(Conversation.id == conversation_id, Conversation.user_id == user_id)
        .first()
    )
    if conversation is None:
        raise ConversationNotFoundError("Conversation introuvable.")
    return conversation


def list_conversations(db: Session, user_id: str) -> list[Conversation]:
    return (
        db.query(Conversation)
        .filter(Conversation.user_id == user_id)
        .order_by(Conversation.updated_at.desc())
        .all()
    )


def _make_title_from_first_message(content: str) -> str:
    cleaned = content.strip().replace("\n", " ")
    return cleaned[:60] + ("…" if len(cleaned) > 60 else "")


def send_message(
    db: Session,
    user_id: str,
    content: str,
    conversation_id: str | None,
    user_language: str,
    provider: AIProvider,
) -> tuple[Conversation, Message, Message]:
    """
    Enregistre le message utilisateur, appelle le moteur IA, enregistre
    la réponse, et retourne (conversation, message_utilisateur, message_assistant).
    """
    if conversation_id:
        conversation = get_conversation(db, conversation_id, user_id)
    else:
        conversation = Conversation(user_id=user_id, title=_make_title_from_first_message(content))
        db.add(conversation)
        db.flush()  # récupère conversation.id sans committer

    user_message = Message(conversation_id=conversation.id, role="user", content=content)
    db.add(user_message)
    db.flush()

    history = [{"role": m.role, "content": m.content} for m in conversation.messages] + [
        {"role": "user", "content": content}
    ]
    reply_text = provider.generate_reply(history, user_language=user_language)

    assistant_message = Message(conversation_id=conversation.id, role="assistant", content=reply_text)
    db.add(assistant_message)

    db.commit()
    db.refresh(conversation)
    db.refresh(user_message)
    db.refresh(assistant_message)

    return conversation, user_message, assistant_message
