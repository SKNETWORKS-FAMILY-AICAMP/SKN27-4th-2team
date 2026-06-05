from dataclasses import dataclass

from backend.schemas.analysis import UserAnalysisResult


@dataclass(slots=True)
class RAGSearchRequest:
    query: str
    categories: list[str] | None = None
    breed_names: list[str] | None = None
    sections: list[str] | None = None
    top_k: int = 5


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

