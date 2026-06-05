from backend.integrations.rag.schemas import RetrievedDocument
from backend.schemas.analysis import UserAnalysisResult


def generate_answer(
    user_message: str,
    documents: list[RetrievedDocument],
    analysis: UserAnalysisResult,
    validation_feedback: list[str] | None = None,
) -> str:
    """Generate a temporary grounded answer until the real LLM prompt is wired."""

    if not documents:
        return (
            "관련 근거 문서를 찾지 못했습니다. 질문을 조금 더 구체적으로 작성해 주세요."
        )

    references = _format_reference_preview(documents)
    topic_text = ", ".join(analysis.topics) if analysis.topics else "일반 상담"
    breed_text = ", ".join(analysis.breed_names) if analysis.breed_names else "특정 견종 없음"
    feedback_text = ""

    if validation_feedback:
        feedback_text = (
            "\n\n이전 답변 검증에서 발견된 보완점:\n"
            + "\n".join(f"- {issue}" for issue in validation_feedback)
            + "\n"
        )

    return (
        "Basic Workflow로 질문을 처리했습니다.\n\n"
        f"- 질문 요약: {analysis.summary}\n"
        f"- 감지된 주제: {topic_text}\n"
        f"- 감지된 견종: {breed_text}\n\n"
        f"{feedback_text}"
        "현재는 실제 LLM/RAG 연결 전 단계라, 아래 검색 문서를 근거로 응답 형태만 확인합니다.\n\n"
        f"{references}\n\n"
        "실제 Vector DB와 답변 생성 모델이 연결되면 이 위치에서 자연스러운 상담 답변이 생성됩니다."
    )


def _format_reference_preview(documents: list[RetrievedDocument]) -> str:
    lines: list[str] = []

    for index, document in enumerate(documents, start=1):
        source = document.metadata.get("source", "unknown")
        preview = document.content.replace("\n", " ")[:220]
        lines.append(f"[근거 {index}] source={source}, score={document.score}\n{preview}")

    return "\n\n".join(lines)
