from dataclasses import dataclass

from backend.agents.response_generator import generate_answer
from backend.agents.response_validator import validate_answer
from backend.agents.user_analysis_agent import analyze_user_message
from backend.integrations.rag.fake_client import FakeRAGClient
from backend.integrations.rag.interface import RAGClient
from backend.schemas.analysis import UserAnalysisResult
from backend.schemas.chat import ChatResponse


@dataclass(slots=True)
class RAGSearchRequest:
    query: str
    categories: list[str] | None = None
    breed_names: list[str] | None = None
    sections: list[str] | None = None
    top_k: int = 5


def run_basic_chat_workflow(
    user_message: str,
    rag_client: RAGClient | None = None,
    max_answer_retries: int = 1,
) -> ChatResponse:
    """Run the first linear workflow: analyze -> retrieve -> answer -> validate."""

    client = rag_client or FakeRAGClient()
    analysis = analyze_user_message(user_message)
    search_request = build_rag_search_request(user_message, analysis)

    documents = client.search_documents(
        query=search_request.query,
        categories=search_request.categories,
        breed_names=search_request.breed_names,
        sections=search_request.sections,
        top_k=search_request.top_k,
    )

    validation_issues: list[str] | None = None
    final_answer = ""

    for attempt in range(max_answer_retries + 1):
        draft_answer = generate_answer(
            user_message=user_message,
            documents=documents,
            analysis=analysis,
            validation_feedback=validation_issues,
        )
        validation_result = validate_answer(
            user_message=user_message,
            answer=draft_answer,
            has_sources=bool(documents),
        )
        final_answer = validation_result.answer

        if validation_result.is_valid or not validation_result.should_retry:
            break

        validation_issues = validation_result.issues

        if attempt >= max_answer_retries:
            break

    return ChatResponse(
        answer=final_answer,
        sources=documents,
        analysis=analysis,
    )


def build_rag_search_request(
    user_message: str,
    analysis: UserAnalysisResult,
) -> RAGSearchRequest:
    """Convert lightweight analysis into the future RAG search contract."""

    keyword_query = " ".join(analysis.keywords)
    query = f"{user_message.strip()} {keyword_query}".strip()

    return RAGSearchRequest(
        query=query,
        categories=analysis.topics or None,
        breed_names=analysis.breed_names or None,
        sections=_guess_sections(analysis.topics),
        top_k=5,
    )


def _guess_sections(topics: list[str]) -> list[str] | None:
    if not topics:
        return None

    section_map = {
        "walking": ["exercise"],
        "training": ["training"],
        "grooming": ["grooming"],
        "nutrition": ["nutrition"],
        "health": ["health"],
        "breed_recommendation": ["traits", "exercise", "training", "grooming"],
    }

    sections: list[str] = []
    for topic in topics:
        for section in section_map.get(topic, []):
            if section not in sections:
                sections.append(section)

    return sections or None
