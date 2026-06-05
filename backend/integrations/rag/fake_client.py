from backend.integrations.rag.schemas import RetrievedDocument


class FakeRAGClient:
    """Temporary RAG client used until the Vector DB branch is connected."""

    def search_documents(
        self,
        query: str,
        categories: list[str] | None = None,
        breed_names: list[str] | None = None,
        sections: list[str] | None = None,
        top_k: int = 5,
    ) -> list[RetrievedDocument]:
        return [
            RetrievedDocument(
                document_id="fake:rag:basic-workflow",
                content=(
                    "현재는 실제 Vector DB가 연결되지 않은 Basic Workflow 단계입니다. "
                    "이 문서는 RAG 연결 전 챗봇 흐름 테스트를 위한 임시 검색 결과입니다."
                ),
                score=1.0,
                metadata={
                    "source": "fake",
                    "query": query,
                    "categories": categories or [],
                    "breed_names": breed_names or [],
                    "sections": sections or [],
                    "top_k": top_k,
                },
            )
        ]

