from backend.agents.rag_workflow import run_rag_workflow
from backend.integrations.rag.interface import RAGClient
from backend.schemas.chat import ChatResponse


def handle_chat_message(
    message: str,
    conversation_id: str | None = None,
    rag_client: RAGClient | None = None,
) -> ChatResponse:
    """Service entrypoint for Django views or APIs to call later."""

    # conversation_id is reserved for the later memory layer.
    _ = conversation_id

    return run_rag_workflow(
        question=message,
        rag_client=rag_client,
    )
