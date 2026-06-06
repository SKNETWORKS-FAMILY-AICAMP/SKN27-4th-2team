from __future__ import annotations

import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]


def _ensure_project_root_on_path() -> None:
    project_root = str(PROJECT_ROOT)
    if project_root not in sys.path:
        sys.path.insert(0, project_root)


def get_rag_response(message: str):
    """Call the backend RAG service from the Django chatbot app."""

    _ensure_project_root_on_path()

    from backend.services.chat_service import handle_chat_message

    return handle_chat_message(message)
