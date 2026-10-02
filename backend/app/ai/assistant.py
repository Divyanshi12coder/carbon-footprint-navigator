"""Assistant orchestration: context builder -> LLM (or demo) -> numeric validation -> persistence.

user -> FastAPI -> context builder (DB, carbon engine, ML) -> LLM -> validation -> client
"""

import json
import logging
from datetime import UTC, datetime

from sqlalchemy.orm import Session

from app.ai import demo_responder, prompts
from app.ai.context_builder import build_context
from app.ai.providers import ProviderError, get_provider
from app.ai.validation import validate_numbers
from app.core.config import get_settings
from app.models import Conversation, Message, User

logger = logging.getLogger(__name__)
HISTORY_TURNS = 6


def assistant_status() -> dict:
    settings = get_settings()
    live = get_provider(settings) is not None
    return {
        "mode": "llm" if live else "demo",
        "provider": settings.ai_provider if live else None,
        "model": settings.ai_model if live else None,
        "description": (
            "Answers are written by a language model from facts computed by the carbon engine; every figure is validated."
            if live
            else "No AI API key is configured, so answers are deterministic templates filled with your computed data."
        ),
    }


def ask(db: Session, user: User, conversation: Conversation, question: str) -> Message:
    settings = get_settings()
    # Prior turns (captured before this question is stored), oldest first, starting on a user turn.
    history = list(conversation.messages)[-HISTORY_TURNS:]
    while history and history[0].role != "user":
        history.pop(0)
    db.add(Message(conversation_id=conversation.id, role="user", content=question))
    db.flush()

    context = build_context(db, user, question)
    facts = context["facts"]
    provider = get_provider(settings)
    mode, model, text, note = "demo", None, "", None

    if provider is not None:
        messages = [{"role": m.role, "content": m.content} for m in history]
        messages.append({"role": "user", "content": prompts.user_turn(question, json.dumps(facts, default=str), context["intents"])})
        try:
            completion = provider.complete(prompts.SYSTEM_PROMPT, messages)
            mode, model, text = "llm", completion.model, completion.text
        except ProviderError as exc:
            note = str(exc)
            logger.warning("Falling back to demo responder: %s", exc)

    if mode == "demo":
        text = demo_responder.respond(question, context)
        if note:
            text += f"\n\n_The AI provider was unavailable ({note}); showing a data-grounded demo answer instead._"

    validation = validate_numbers(text, facts, question)
    if mode == "llm" and validation["unverified"]:
        text += (
            "\n\n_⚠ Some figures above could not be matched to your computed data "
            f"({', '.join(validation['unverified'][:5])}). Treat them with caution._"
        )

    reply = Message(
        conversation_id=conversation.id,
        role="assistant",
        content=text,
        mode=mode,
        model=model,
        context_used={"intents": context["intents"], "topics": context["topics"], "facts": facts},
        validation=validation,
    )
    db.add(reply)
    conversation.updated_at = datetime.now(UTC)
    db.commit()
    db.refresh(reply)
    return reply
