from dataclasses import dataclass, field


MEDICAL_KEYWORDS = ["아파", "구토", "설사", "피", "발작", "응급", "질병", "병원"]
RECOMMENDATION_KEYWORDS = ["추천", "키우기 좋은", "견종", "품종"]


@dataclass(slots=True)
class ValidationResult:
    is_valid: bool
    answer: str
    issues: list[str] = field(default_factory=list)
    notices: list[str] = field(default_factory=list)
    should_retry: bool = False


def validate_answer(user_message: str, answer: str, has_sources: bool) -> ValidationResult:
    """Validate the draft answer and decide whether the workflow should retry."""

    issues: list[str] = []
    notices: list[str] = []

    if not answer.strip():
        issues.append("답변 내용이 비어 있습니다.")

    if not has_sources:
        issues.append("질문과 연결되는 근거 문서가 없습니다.")
        notices.append("참고: 현재 질문과 직접 연결되는 근거 문서를 충분히 찾지 못했습니다.")

    if any(keyword in user_message for keyword in MEDICAL_KEYWORDS):
        notices.append(
            "주의: 건강 이상이나 응급 증상이 의심되면 온라인 답변만으로 판단하지 말고 "
            "수의사 또는 동물병원 상담을 권장합니다."
        )

    if any(keyword in user_message for keyword in RECOMMENDATION_KEYWORDS):
        notices.append(
            "참고: 견종 특성은 일반적인 경향이며 실제 개체의 성격과 생활 환경에 따라 달라질 수 있습니다."
        )

    final_answer = answer
    if notices:
        final_answer = answer + "\n\n" + "\n".join(f"- {notice}" for notice in notices)

    return ValidationResult(
        is_valid=not issues,
        answer=final_answer,
        issues=issues,
        notices=notices,
        should_retry=bool(issues),
    )
