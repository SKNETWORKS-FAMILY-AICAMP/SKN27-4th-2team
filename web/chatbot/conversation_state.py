from __future__ import annotations

import re
from typing import Any

from .models import ChatMessage, ChatSession, RecommendationResult


AKC_BREED_BASE_URL = 'https://www.akc.org/dog-breeds/'

SECTION_LABELS = {
    'basic_profile': 'Basic Profile',
    'about_the_breed': 'About the Breed',
    'traits': 'Breed Traits & Characteristics',
    'colors_markings': 'Breed Colors & Markings',
    'health': 'Health',
    'grooming': 'Grooming',
    'exercise': 'Exercise',
    'training': 'Training',
    'nutrition': 'Nutrition',
    'history': 'History',
    'apartment_recommendation': 'Apartment Recommendation',
}

TOPIC_STOPWORDS = {
    '강아지',
    '반려견',
    '우리',
    '이유',
    '왜',
    '뭐',
    '뭐야',
    '무엇',
    '어떻게',
    '알려',
    '알려줘',
    '알려주세요',
    '있을까요',
    '있나요',
    '하나요',
    '하는',
    '질문',
    '상담',
    '행동',
    '경우',
    '방법',
}

KOREAN_SUFFIXES = (
    '하는데',
    '합니다',
    '했나요',
    '인가요',
    '일까요',
    '할까요',
    '있을까요',
    '있나요',
    '나요',
    '까요',
    '하게',
    '하는',
    '한테',
    '에게',
    '에서',
    '으로',
    '해줘',
    '요',
    '은',
    '는',
    '이',
    '가',
    '을',
    '를',
    '에',
    '의',
    '도',
    '만',
    '와',
    '과',
    '로',
)


def filter_display_sources(
    *,
    question: str,
    sources: list[Any],
    analysis: Any = None,
) -> list[Any]:
    """Keep only source documents that are suitable for user-facing citation."""

    documents = list(sources)
    if len(documents) <= 1:
        return documents

    topics = set(getattr(analysis, 'topics', []) or [])
    if 'breed_recommendation' in topics:
        return documents[:5]

    breed_names = {
        str(name).strip().lower()
        for name in (getattr(analysis, 'breed_names', []) or [])
        if str(name).strip()
    }
    if breed_names:
        breed_documents = [
            document
            for document in documents
            if _document_breed_name(document).lower() in breed_names
        ]
        if breed_documents:
            return breed_documents[:5]

    keywords = _topic_keywords(question)
    if not keywords:
        return documents[:1]

    filtered: list[Any] = []
    required_score = 2 if len(keywords) >= 2 else 1
    for document in documents:
        score = _topic_match_score(document, keywords)
        if score >= required_score:
            filtered.append(document)

    return filtered[:3] if filtered else documents[:1]


def serialize_sources(sources: list[Any]) -> list[dict[str, Any]]:
    """Convert RetrievedDocument objects into compact JSON metadata."""

    serialized: list[dict[str, Any]] = []
    for source in sources:
        metadata = getattr(source, 'metadata', {}) or {}
        chunk_id = getattr(source, 'document_id', '') or metadata.get('chunk_id') or ''
        display = _build_source_display(metadata=metadata, chunk_id=chunk_id)
        serialized.append(
            {
                'chunk_id': chunk_id,
                'source': metadata.get('source'),
                'breed_name': metadata.get('breed_name'),
                'section': metadata.get('section'),
                'title': metadata.get('title') or metadata.get('section_title'),
                'display_title': display['display_title'],
                'source_label': display['source_label'],
                'url': display['url'],
                'score': _safe_score(getattr(source, 'score', None)),
            }
        )

    return [
        item
        for item in serialized
        if item.get('chunk_id') or item.get('source') or item.get('breed_name')
    ]


def _build_source_display(*, metadata: dict[str, Any], chunk_id: str) -> dict[str, str | None]:
    source = str(metadata.get('source') or '').strip()
    doc_id = str(metadata.get('doc_id') or chunk_id or '').strip()
    title = _first_text(
        metadata.get('title'),
        metadata.get('section_title'),
        metadata.get('question'),
        metadata.get('doc_title'),
    )

    if source == 'akc_breed':
        breed_name = _first_text(metadata.get('breed_name'), _breed_name_from_doc_id(doc_id))
        section = str(metadata.get('section') or '').strip()
        section_title = _section_title(section=section, title=title)
        display_title = f'AKC - {breed_name} / {section_title}' if breed_name else f'AKC - {section_title}'
        return {
            'display_title': display_title,
            'source_label': 'AKC',
            'url': _akc_breed_url(breed_name=breed_name, doc_id=doc_id),
        }

    if source in {'youtube_training', 'youtube_vet'}:
        source_label = 'YouTube'
        channel = _first_text(metadata.get('channel'), metadata.get('expert'), metadata.get('creator'))
        display_title = _join_title_parts(source_label, channel, title or doc_id)
        return {
            'display_title': display_title,
            'source_label': source_label,
            'url': _source_url(metadata),
        }

    if source == 'qna':
        source_label = _qna_source_label(doc_id)
        question = _first_text(metadata.get('question'), title, doc_id)
        display_title = _join_title_parts('YouTube Q&A', source_label, question)
        return {
            'display_title': display_title,
            'source_label': source_label,
            'url': _source_url(metadata),
        }

    if source in {'article', 'article_docs'}:
        source_label = 'Article'
        display_title = f'Article - {title or doc_id or "참고 문서"}'
        return {
            'display_title': display_title,
            'source_label': source_label,
            'url': _source_url(metadata),
        }

    source_label = source or 'Source'
    display_title = _join_title_parts(source_label, None, title or doc_id or '참고 문서')
    return {
        'display_title': display_title,
        'source_label': source_label,
        'url': _source_url(metadata),
    }


def _first_text(*values: Any) -> str:
    for value in values:
        if value is None:
            continue
        text = str(value).strip()
        if text:
            return text
    return ''


def _join_title_parts(prefix: str, middle: str | None, suffix: str) -> str:
    if middle:
        return f'{prefix} - {middle} / {suffix}'
    return f'{prefix} - {suffix}'


def _section_title(*, section: str, title: str) -> str:
    return SECTION_LABELS.get(section) or title or section or 'Breed Information'


def _source_url(metadata: dict[str, Any]) -> str | None:
    for key in ('video_url', 'youtube_url', 'source_url', 'article_url', 'url'):
        url = metadata.get(key)
        if url:
            return str(url).strip()
    return None


def _qna_source_label(doc_id: str) -> str:
    lower_doc_id = doc_id.lower()
    if lower_doc_id.startswith('kang_qna'):
        return '강형욱 Q&A'
    if lower_doc_id.startswith('seol_qna'):
        return '설채현 Q&A'
    return 'YouTube Q&A'


def _akc_breed_url(*, breed_name: str, doc_id: str) -> str | None:
    slug = _akc_slug_from_doc_id(doc_id) or _slugify_akc_breed_name(breed_name)
    if not slug:
        return None
    return f'{AKC_BREED_BASE_URL}{slug}/'


def _akc_slug_from_doc_id(doc_id: str) -> str:
    if not doc_id.startswith('akc_breed:'):
        return ''

    parts = doc_id.split(':')
    if len(parts) < 2:
        return ''
    return parts[1].strip()


def _breed_name_from_doc_id(doc_id: str) -> str:
    slug = _akc_slug_from_doc_id(doc_id)
    if not slug:
        return ''
    return slug.replace('-', ' ').title()


def _slugify_akc_breed_name(breed_name: str) -> str:
    text = breed_name.strip().lower()
    text = text.replace('&', ' and ')
    text = re.sub(r'[^a-z0-9]+', '-', text)
    return text.strip('-')


def _document_breed_name(document: Any) -> str:
    metadata = getattr(document, 'metadata', {}) or {}
    return str(metadata.get('breed_name') or '').strip()


def _topic_keywords(question: str) -> list[str]:
    tokens = re.findall(r'[0-9a-zA-Z가-힣]+', question.lower())
    keywords: list[str] = []
    seen: set[str] = set()

    for token in tokens:
        normalized = _normalize_topic_keyword(token)
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        keywords.append(normalized)

    return keywords[:8]


def _normalize_topic_keyword(keyword: str) -> str:
    text = keyword.strip().lower()
    for suffix in KOREAN_SUFFIXES:
        if len(text) > len(suffix) + 1 and text.endswith(suffix):
            text = text[: -len(suffix)]
            break

    if len(text) <= 1 or text in TOPIC_STOPWORDS:
        return ''
    return text


def _topic_match_score(document: Any, keywords: list[str]) -> int:
    metadata = getattr(document, 'metadata', {}) or {}
    content = str(getattr(document, 'content', '') or '')
    searchable_text = ' '.join(
        [
            content,
            *(str(value) for value in metadata.values() if value is not None),
        ]
    ).lower()

    return sum(1 for keyword in keywords if keyword in searchable_text)


def update_session_state(
    *,
    session: ChatSession,
    question: str,
    answer: str,
    analysis: Any,
    assistant_message: ChatMessage,
    sources: list[dict[str, Any]],
) -> None:
    """Persist lightweight context for follow-up questions and recommendations."""

    topics = list(getattr(analysis, 'topics', []) or [])
    keywords = list(getattr(analysis, 'keywords', []) or [])
    detected_breeds = list(getattr(analysis, 'breed_names', []) or [])
    source_breeds = _unique_non_empty(source.get('breed_name') for source in sources)
    recommended_breeds = source_breeds or detected_breeds

    preferences = {
        'last_question': question,
        'topics': topics,
        'keywords': keywords,
        'detected_breeds': detected_breeds,
    }

    session.context_summary = _build_context_summary(
        previous_summary=session.context_summary,
        question=question,
        answer=answer,
        topics=topics,
        breeds=recommended_breeds,
    )
    session.last_user_preferences = preferences
    session.last_recommended_breeds = recommended_breeds
    session.save(
        update_fields=[
            'context_summary',
            'last_user_preferences',
            'last_recommended_breeds',
            'updated_at',
        ]
    )

    if 'breed_recommendation' in topics and recommended_breeds:
        RecommendationResult.objects.create(
            session=session,
            message=assistant_message,
            breeds=recommended_breeds,
            user_preferences=preferences,
        )


def _safe_score(score: Any) -> float | None:
    if score is None:
        return None

    try:
        return round(float(score), 4)
    except (TypeError, ValueError):
        return None


def _unique_non_empty(values) -> list[str]:
    unique: list[str] = []
    for value in values:
        if not value or value in unique:
            continue
        unique.append(str(value))
    return unique


def _build_context_summary(
    *,
    previous_summary: str,
    question: str,
    answer: str,
    topics: list[str],
    breeds: list[str],
) -> str:
    topic_text = ', '.join(topics) if topics else 'general'
    breed_text = ', '.join(breeds[:5]) if breeds else 'none'
    answer_preview = answer.replace('\n', ' ')[:160]
    new_line = f'Q: {question[:120]} | topics: {topic_text} | breeds: {breed_text} | A: {answer_preview}'

    lines = [line for line in previous_summary.splitlines() if line.strip()]
    lines.append(new_line)
    return '\n'.join(lines[-6:])
