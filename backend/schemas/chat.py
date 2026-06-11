from dataclasses import dataclass, field
from typing import Any

from backend.integrations.rag.schemas import RetrievedDocument
from backend.schemas.analysis import UserAnalysisResult


@dataclass(slots=True)
class ChatRequest:
    message: str
    conversation_id: str | None = None
    memory_context: dict[str, Any] | None = None


@dataclass(slots=True)
class ChatResponse:
    answer: str
    sources: list[RetrievedDocument] = field(default_factory=list)
    analysis: UserAnalysisResult | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "answer": self.answer,
            "sources": [source.to_dict() for source in self.sources],
            "analysis": self.analysis.to_dict() if self.analysis else None,
        }
