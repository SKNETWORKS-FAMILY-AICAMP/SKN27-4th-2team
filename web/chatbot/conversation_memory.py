from __future__ import annotations

from typing import Any

from .models import ChatSession


DEFAULT_RECENT_MESSAGE_LIMIT = 6
MAX_MESSAGE_CHARS = 800


def build_memory_context(
    session: ChatSession | None,
    *,
    limit: int = DEFAULT_RECENT_MESSAGE_LIMIT,
) -> dict[str, Any] | None:
    """Build a compact conversation memory payload for the backend RAG workflow."""

    if session is None:
        return None

    recent_messages = list(session.messages.order_by('-created_at')[:limit])
    recent_messages.reverse()

    return {
        'conversation_id': str(session.id),
        'context_summary': session.context_summary or '',
        'recent_messages': [
            {
                'role': message.role,
                'content': _compact_text(message.content),
            }
            for message in recent_messages
        ],
        'last_user_preferences': session.last_user_preferences or {},
        'last_recommended_breeds': session.last_recommended_breeds or [],
    }


def _compact_text(value: str) -> str:
    text = ' '.join((value or '').split())
    if len(text) <= MAX_MESSAGE_CHARS:
        return text
    return f'{text[:MAX_MESSAGE_CHARS].rstrip()}...'
