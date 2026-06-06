import re

from backend.schemas.analysis import UserAnalysisResult


TOPIC_KEYWORDS: dict[str, list[str]] = {
    'separation_anxiety': ['분리불안', '혼자', '외출', '불안'],
    'barking': ['짖', '짖음', '소음', '하울링'],
    'walking': ['산책', '운동', '활동량'],
    'potty_training': ['배변', '화장실', '대소변'],
    'biting': ['입질', '무는', '물어요'],
    'grooming': ['털', '털빠짐', '그루밍', '목욕', '빗질'],
    'training': ['훈련', '교육', '초보'],
    'nutrition': ['사료', '영양', '밥', '간식'],
    'health': ['아프', '아픈', '아파요', '통증', '구토', '설사', '혈변', '출혈', '발작', '응급', '질병', '병원'],
    'breed_recommendation': ['추천', '견종', '품종', '키우기 좋은', '어울리는'],
}


BREED_ALIASES: dict[str, str] = {
    '말티즈': 'Maltese',
    '몰티즈': 'Maltese',
    'maltese': 'Maltese',
    '푸들': 'Poodle',
    'poodle': 'Poodle',
    '비숑': 'Bichon Frise',
    '비숑프리제': 'Bichon Frise',
    'bichon': 'Bichon Frise',
    '포메': 'Pomeranian',
    '포메라니안': 'Pomeranian',
    'pomeranian': 'Pomeranian',
    '웰시코기': 'Pembroke Welsh Corgi',
    '코기': 'Pembroke Welsh Corgi',
    '시바': 'Shiba Inu',
    '시바견': 'Shiba Inu',
    'shiba': 'Shiba Inu',
    '골든리트리버': 'Golden Retriever',
    '리트리버': 'Golden Retriever',
    'golden retriever': 'Golden Retriever',
    '래브라도': 'Labrador Retriever',
    '라브라도': 'Labrador Retriever',
    'labrador': 'Labrador Retriever',
    '진돗개': 'Korean Jindo Dog',
    '진도견': 'Korean Jindo Dog',
    'jindo': 'Korean Jindo Dog',
    'affenpinscher': 'Affenpinscher',
    'affen': 'Affenpinscher',
}


def analyze_user_message(user_message: str) -> UserAnalysisResult:
    """Extract simple search hints before routing to RAG."""

    normalized_message = user_message.strip()
    keywords = _extract_keywords(normalized_message)
    topics = _detect_topics(normalized_message)
    breed_names = _detect_breed_names(normalized_message)

    return UserAnalysisResult(
        summary=normalized_message[:120],
        keywords=keywords,
        breed_names=breed_names,
        topics=topics,
    )


def _extract_keywords(message: str) -> list[str]:
    tokens = re.findall(r'[A-Za-z가-힣0-9]+', message)
    seen: set[str] = set()
    keywords: list[str] = []

    for token in tokens:
        if len(token) <= 1:
            continue
        lowered = token.lower()
        if lowered in seen:
            continue
        seen.add(lowered)
        keywords.append(token)

    return keywords[:12]


def _detect_topics(message: str) -> list[str]:
    detected: list[str] = []

    for topic, keywords in TOPIC_KEYWORDS.items():
        if any(keyword in message for keyword in keywords):
            detected.append(topic)

    return detected


def _detect_breed_names(message: str) -> list[str]:
    lowered_message = message.lower()
    found: list[str] = []

    for alias, canonical_name in BREED_ALIASES.items():
        if alias.lower() in lowered_message and canonical_name not in found:
            found.append(canonical_name)

    return found
