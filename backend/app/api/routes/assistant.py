import uuid
from typing import Any

from fastapi import APIRouter, HTTPException, Response, status
from sqlalchemy import select

from app.ai.assistant import ask, assistant_status
from app.api.deps import CurrentUser, DbSession
from app.core.config import get_settings
from app.core.rate_limit import limiter
from app.models import Conversation
from app.schemas.engagement import AskIn, ConversationDetail, ConversationIn, ConversationOut, MessageOut

router = APIRouter(prefix="/assistant", tags=["assistant"])

SUGGESTED_QUESTIONS = [
    "What is causing most of my emissions?",
    "Why did my emissions change this month?",
    "How can I reduce my transportation footprint?",
    "What would happen if I reduced flights by 50%?",
    "Give me a realistic sustainability plan.",
    "Explain my carbon footprint.",
]


def _owned(db, user, conversation_id: uuid.UUID) -> Conversation:
    conv = db.get(Conversation, conversation_id)
    if conv is None or conv.user_id != user.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Conversation not found")
    return conv


@router.get("/status")
def status_endpoint(user: CurrentUser) -> dict[str, Any]:
    return {**assistant_status(), "suggested_questions": SUGGESTED_QUESTIONS}


@router.get("/conversations", response_model=list[ConversationOut])
def list_conversations(user: CurrentUser, db: DbSession) -> list[Conversation]:
    return list(db.scalars(select(Conversation).where(Conversation.user_id == user.id).order_by(Conversation.updated_at.desc())))


@router.post("/conversations", response_model=ConversationOut, status_code=status.HTTP_201_CREATED)
def create_conversation(payload: ConversationIn, user: CurrentUser, db: DbSession) -> Conversation:
    conv = Conversation(user_id=user.id, title=payload.title or "New conversation")
    db.add(conv)
    db.commit()
    db.refresh(conv)
    return conv


@router.get("/conversations/{conversation_id}", response_model=ConversationDetail)
def get_conversation(conversation_id: uuid.UUID, user: CurrentUser, db: DbSession) -> Conversation:
    return _owned(db, user, conversation_id)


@router.delete("/conversations/{conversation_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_conversation(conversation_id: uuid.UUID, user: CurrentUser, db: DbSession) -> Response:
    db.delete(_owned(db, user, conversation_id))
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/conversations/{conversation_id}/messages", response_model=MessageOut, status_code=status.HTTP_201_CREATED)
def post_message(conversation_id: uuid.UUID, payload: AskIn, user: CurrentUser, db: DbSession):
    limiter.check(f"assistant:{user.id}", get_settings().rate_limit_assistant_per_minute)
    conv = _owned(db, user, conversation_id)
    if conv.title == "New conversation":
        conv.title = payload.question.strip()[:80]
    return ask(db, user, conv, payload.question.strip())
