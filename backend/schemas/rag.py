from typing import TypedDict

from backend.integrations.rag.schemas import RetrievedDocument
from backend.schemas.analysis import UserAnalysisResult


class RAGState(TypedDict, total=False):
    """State passed between LangGraph RAG workflow nodes."""

    question: str
    analysis: UserAnalysisResult | None
    search_query: str
    categories: list[str] | None
    breed_names: list[str] | None
    sections: list[str] | None
    retrieved_docs: list[RetrievedDocument]
    relevant_docs: list[RetrievedDocument]
    context: str
    answer: str
    sources: list[str]
    relevance_issues: list[str]
    validation_issues: list[str]

