from __future__ import annotations

RECOMMENDATION_KEYWORDS = ("견종 추천", "추천 견종", "강아지 추천", "반려견 추천", "키우기 쉬운 견종")


def append_shelter_links_for_recommendation(
    *,
    question: str,
    answer: str,
    analysis,
    base_url: str | None = None,
) -> str:
    """Append a general shelter adoption prompt after breed recommendations."""

    if not _is_breed_recommendation(question=question, analysis=analysis):
        return answer

    lines = [
        "",
        "유기견 입양도 함께 고민하고 있다면, 보호 중인 아이들을 입양 페이지에서 확인해볼 수 있어요.",
    ]

    return answer.rstrip() + "\n" + "\n".join(lines)


def _is_breed_recommendation(*, question: str, analysis) -> bool:
    topics = set(getattr(analysis, "topics", []) or [])
    if "breed_recommendation" in topics:
        return True

    normalized_question = " ".join(question.split())
    return any(keyword in normalized_question for keyword in RECOMMENDATION_KEYWORDS)
