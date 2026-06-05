from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class UserAnalysisResult:
    """Lightweight analysis output for the basic linear workflow."""

    summary: str
    keywords: list[str] = field(default_factory=list)
    breed_names: list[str] = field(default_factory=list)
    topics: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "summary": self.summary,
            "keywords": self.keywords,
            "breed_names": self.breed_names,
            "topics": self.topics,
        }

