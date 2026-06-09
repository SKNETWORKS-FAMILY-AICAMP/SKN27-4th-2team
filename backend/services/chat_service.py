from backend.agents.rag_workflow import run_rag_workflow
from backend.integrations.rag.interface import RAGClient
from backend.integrations.rag.pgvector_client import PGVectorRAGClient
from backend.schemas.analysis import UserAnalysisResult
from backend.schemas.chat import ChatResponse


OWNED_DOG_RECALL_PATTERNS = (
    "내가 키우고 있는",
    "내가 키우는",
    "내 반려견",
    "우리 강아지",
    "우리 개",
)


def handle_chat_message(
    message: str,
    conversation_id: str | None = None,
    memory_context: dict | None = None,
    rag_client: RAGClient | None = None,
) -> ChatResponse:
    """Service entrypoint for Django views or APIs to call later."""

    memory_answer = _answer_memory_recall_question(message, memory_context)
    if memory_answer:
        return ChatResponse(
            answer=memory_answer,
            sources=[],
            analysis=UserAnalysisResult(summary=message, topics=[]),
        )

    client = rag_client or PGVectorRAGClient()

    return run_rag_workflow(
        question=message,
        conversation_id=conversation_id,
        memory_context=memory_context,
        rag_client=client,
    )


def _answer_memory_recall_question(message: str, memory_context: dict | None) -> str:
    if not memory_context:
        return ""

    normalized = " ".join(message.split())
    asks_owned_dog = any(pattern in normalized for pattern in OWNED_DOG_RECALL_PATTERNS)
    asks_identity = any(keyword in normalized for keyword in ("뭐", "무슨", "어떤", "누구", "기억"))
    if not (asks_owned_dog and asks_identity):
        return ""

    breed = _extract_owned_breed_from_memory(memory_context)
    if not breed:
        return (
            "이 대화 안에서는 아직 보호자님이 키우는 반려견의 견종을 명확히 확인하지 못했어요. "
            "견종을 한 번 알려주시면 이후 질문에서 그 정보를 이어서 참고하겠습니다."
        )

    return (
        f"이 대화에서 말씀해주신 기준으로는 보호자님이 키우고 있는 반려견은 {breed}입니다. "
        "앞으로 이어지는 질문에서는 이 정보를 참고해서 답변드릴게요."
    )


def _extract_owned_breed_from_memory(memory_context: dict) -> str:
    detected = (memory_context.get("last_user_preferences") or {}).get("detected_breeds") or []
    if detected:
        return str(detected[0])

    text_parts: list[str] = []
    context_summary = str(memory_context.get("context_summary") or "")
    if context_summary:
        text_parts.append(context_summary)

    for message in memory_context.get("recent_messages") or []:
        if message.get("role") != "user":
            continue
        text_parts.append(str(message.get("content") or ""))

    memory_text = "\n".join(text_parts)
    known_breeds = (
        "진돗개",
        "Korean Jindo Dog",
        "포메라니언",
        "Pomeranian",
        "말티즈",
        "Maltese",
        "푸들",
        "Poodle",
        "비숑",
        "Bichon Frise",
        "시츄",
        "Shih Tzu",
        "퍼그",
        "Pug",
    )
    for breed in known_breeds:
        if breed.lower() in memory_text.lower():
            return breed

    return ""
