from langgraph.graph import END, START, StateGraph

from backend.agents.rag_query_builder import build_rag_search_request
from backend.agents.response_generator import generate_answer
from backend.agents.response_validator import validate_answer
from backend.agents.user_analysis_agent import analyze_user_message
from backend.integrations.rag.fake_client import FakeRAGClient
from backend.integrations.rag.interface import RAGClient
from backend.integrations.rag.schemas import RetrievedDocument
from backend.schemas.analysis import UserAnalysisResult
from backend.schemas.chat import ChatResponse
from backend.schemas.rag import RAGState


def create_rag_workflow(rag_client: RAGClient | None = None):
    """Create a LangGraph RAG workflow.

    Graph shape:
    START -> retrieve -> evaluate_relevance -> generate -> END
    """

    client = rag_client or FakeRAGClient()
    workflow = StateGraph(RAGState)

    workflow.add_node("retrieve", _make_retrieve_node(client))
    workflow.add_node("evaluate_relevance", evaluate_relevance)
    workflow.add_node("generate", generate)

    workflow.add_edge(START, "retrieve")
    workflow.add_edge("retrieve", "evaluate_relevance")
    workflow.add_edge("evaluate_relevance", "generate")
    workflow.add_edge("generate", END)

    return workflow.compile()


def run_rag_workflow(
    question: str,
    rag_client: RAGClient | None = None,
) -> ChatResponse:
    """Run the LangGraph RAG workflow and convert the final state to ChatResponse."""

    app = create_rag_workflow(rag_client=rag_client)
    final_state = app.invoke(
        {
            "question": question,
            "analysis": None,
            "retrieved_docs": [],
            "relevant_docs": [],
            "context": "",
            "answer": "",
            "sources": [],
            "relevance_issues": [],
            "validation_issues": [],
        }
    )

    return ChatResponse(
        answer=final_state.get("answer", ""),
        sources=final_state.get("relevant_docs", []),
        analysis=final_state.get("analysis"),
    )


def _make_retrieve_node(rag_client: RAGClient):
    def retrieve(state: RAGState) -> RAGState:
        """Document retrieval node."""

        question = state["question"]
        analysis = analyze_user_message(question)
        search_request = build_rag_search_request(question, analysis)

        retrieved_docs = rag_client.search_documents(
            query=search_request.query,
            categories=search_request.categories,
            breed_names=search_request.breed_names,
            sections=search_request.sections,
            top_k=search_request.top_k,
        )

        return {
            **state,
            "analysis": analysis,
            "search_query": search_request.query,
            "categories": search_request.categories,
            "breed_names": search_request.breed_names,
            "sections": search_request.sections,
            "retrieved_docs": retrieved_docs,
        }

    return retrieve


def evaluate_relevance(state: RAGState) -> RAGState:
    """Evaluate retrieved document relevance.

    This is rule-based for now. The future LLM version can replace this node while
    keeping the same state contract.
    """

    retrieved_docs = state.get("retrieved_docs", [])
    analysis = state.get("analysis")

    if not retrieved_docs:
        return {
            **state,
            "relevant_docs": [],
            "sources": [],
            "context": "",
            "relevance_issues": ["검색된 문서가 없습니다."],
        }

    relevant_docs = _filter_relevant_documents(
        question=state["question"],
        analysis=analysis,
        documents=retrieved_docs,
    )
    sources = _collect_sources(relevant_docs)
    context = _build_context(relevant_docs)
    issues = [] if relevant_docs else ["질문과 관련성이 충분한 문서를 찾지 못했습니다."]

    return {
        **state,
        "relevant_docs": relevant_docs,
        "sources": sources,
        "context": context,
        "relevance_issues": issues,
    }


def generate(state: RAGState) -> RAGState:
    """Answer generation node."""

    question = state["question"]
    analysis = state.get("analysis") or UserAnalysisResult(summary=question)
    relevant_docs = state.get("relevant_docs", [])

    draft_answer = generate_answer(
        user_message=question,
        documents=relevant_docs,
        analysis=analysis,
        validation_feedback=state.get("relevance_issues") or None,
    )
    validation_result = validate_answer(
        user_message=question,
        answer=draft_answer,
        has_sources=bool(relevant_docs),
    )

    return {
        **state,
        "answer": validation_result.answer,
        "validation_issues": validation_result.issues,
    }


def _filter_relevant_documents(
    question: str,
    analysis: UserAnalysisResult | None,
    documents: list[RetrievedDocument],
) -> list[RetrievedDocument]:
    keywords = _build_relevance_keywords(question, analysis)

    relevant_docs: list[RetrievedDocument] = []
    for document in documents:
        if document.metadata.get("source") == "fake":
            relevant_docs.append(document)
            continue

        if not keywords:
            relevant_docs.append(document)
            continue

        searchable_text = _document_searchable_text(document)
        if any(keyword in searchable_text for keyword in keywords):
            relevant_docs.append(document)

    return relevant_docs


def _build_relevance_keywords(
    question: str,
    analysis: UserAnalysisResult | None,
) -> list[str]:
    raw_keywords = list(analysis.keywords if analysis else [])
    raw_keywords.extend(question.replace(",", " ").split())

    keywords: list[str] = []
    seen: set[str] = set()
    for keyword in raw_keywords:
        normalized = keyword.strip().lower()
        if len(normalized) <= 1 or normalized in seen:
            continue
        seen.add(normalized)
        keywords.append(normalized)

    return keywords[:16]


def _document_searchable_text(document: RetrievedDocument) -> str:
    metadata_text = " ".join(str(value) for value in document.metadata.values())
    return f"{document.content} {metadata_text}".lower()


def _collect_sources(documents: list[RetrievedDocument]) -> list[str]:
    sources: list[str] = []

    for document in documents:
        source = str(document.metadata.get("source") or document.document_id)
        if source not in sources:
            sources.append(source)

    return sources


def _build_context(documents: list[RetrievedDocument]) -> str:
    return "\n\n".join(
        f"[문서 {index}]\n{document.content}"
        for index, document in enumerate(documents, start=1)
    )
