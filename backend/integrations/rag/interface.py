from typing import Protocol

from backend.integrations.rag.schemas import RetrievedDocument


class RAGClient(Protocol):
    """Contract that the real Vector DB retriever should implement later."""

    def search_documents(
        self,
        query: str,
        categories: list[str] | None = None,
        breed_names: list[str] | None = None,
        sections: list[str] | None = None,
        top_k: int = 5,
    ) -> list[RetrievedDocument]:
        ...

