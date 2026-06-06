from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv
from langchain_openai import ChatOpenAI

from backend.integrations.rag.schemas import RetrievedDocument
from backend.schemas.analysis import UserAnalysisResult


PROJECT_DIR = Path(__file__).resolve().parents[2]
DEFAULT_CHAT_MODEL = 'gpt-4o-mini'
MAX_CONTEXT_CHARS = 7000


def generate_answer(
    user_message: str,
    documents: list[RetrievedDocument],
    analysis: UserAnalysisResult,
    validation_feedback: list[str] | None = None,
) -> str:
    """Generate a natural answer grounded in retrieved RAG documents."""

    if not documents:
        return (
            '관련 근거 문서를 충분히 찾지 못했습니다. '
            '견종 이름이나 궁금한 상황을 조금 더 구체적으로 알려주세요.'
        )

    load_dotenv(PROJECT_DIR / '.env', encoding='utf-8-sig')
    api_key = os.getenv('OPENAI_API_KEY')
    if not api_key:
        return (
            'RAG 근거 문서는 찾았지만 OPENAI_API_KEY가 설정되어 있지 않아 '
            '자연어 답변을 생성하지 못했습니다.'
        )

    llm = ChatOpenAI(
        model=os.getenv('OPENAI_CHAT_MODEL', DEFAULT_CHAT_MODEL),
        api_key=api_key,
        temperature=0.2,
    )

    messages = [
        ('system', _system_prompt()),
        (
            'human',
            _build_user_prompt(
                user_message=user_message,
                documents=documents,
                analysis=analysis,
                validation_feedback=validation_feedback,
            ),
        ),
    ]
    response = llm.invoke(messages)
    return _clean_model_output(str(response.content))


def _system_prompt() -> str:
    return (
        '당신은 Pet Mate의 반려견 상담 챗봇입니다. '
        '반드시 제공된 RAG 근거 문서의 내용만 바탕으로 한국어로 답변하세요. '
        '근거에 없는 내용을 확정적으로 말하지 말고, 정보가 부족하면 부족하다고 말하세요. '
        '초보 보호자가 이해하기 쉽게 친절하고 실용적으로 설명하세요. '
        '의학적 증상이나 응급 상황은 수의사 상담을 권장하세요. '
        '견종 추천은 일반적 경향이며 개체별 차이가 있음을 짧게 언급하세요. '
        '답변 하단의 출처 표시는 웹 화면에서 별도로 처리하므로 본문에 [근거 1] 같은 출처 목록을 반복하지 마세요.'
    )


def _build_user_prompt(
    *,
    user_message: str,
    documents: list[RetrievedDocument],
    analysis: UserAnalysisResult,
    validation_feedback: list[str] | None,
) -> str:
    topic_text = ', '.join(analysis.topics) if analysis.topics else '일반 상담'
    breed_text = ', '.join(analysis.breed_names) if analysis.breed_names else '특정 견종 없음'
    context = _format_context(documents)
    feedback = ''

    if validation_feedback:
        feedback = '\n이전 검증 피드백:\n' + '\n'.join(f'- {issue}' for issue in validation_feedback)

    return (
        f'사용자 질문:\n{user_message}\n\n'
        f'질문 분석:\n'
        f'- 주제: {topic_text}\n'
        f'- 감지된 견종: {breed_text}\n'
        f'{feedback}\n\n'
        f'RAG 근거 문서:\n{context}\n\n'
        '작성 지침:\n'
        '- 질문에 직접 답하세요.\n'
        '- 핵심 특징이나 관리 포인트는 짧은 문단 또는 bullet로 정리하세요.\n'
        '- 문서에 있는 수치, trait, 색상, 관리 정보를 활용하세요.\n'
        '- 근거 문서에 없는 추측은 피하세요.\n'
        '- 최종 답변만 작성하세요.'
    )


def _format_context(documents: list[RetrievedDocument]) -> str:
    chunks: list[str] = []
    total_chars = 0

    for index, document in enumerate(documents, start=1):
        metadata = document.metadata or {}
        header = (
            f'[문서 {index}] '
            f'source={metadata.get("source", "unknown")}; '
            f'breed={metadata.get("breed_name", "unknown")}; '
            f'section={metadata.get("section", "unknown")}; '
            f'title={metadata.get("title", metadata.get("section_title", ""))}; '
            f'score={document.score}'
        )
        content = (document.content or '').strip()
        chunk = f'{header}\n{content}'

        if total_chars + len(chunk) > MAX_CONTEXT_CHARS:
            remaining = MAX_CONTEXT_CHARS - total_chars
            if remaining <= 300:
                break
            chunk = chunk[:remaining]

        chunks.append(chunk)
        total_chars += len(chunk)

    return '\n\n'.join(chunks)


def _clean_model_output(answer: str) -> str:
    return answer.replace('**', '').strip()
