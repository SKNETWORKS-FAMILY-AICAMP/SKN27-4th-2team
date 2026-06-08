from __future__ import annotations

from dataclasses import dataclass
from urllib.parse import urlencode

from django.db import DatabaseError, ProgrammingError
from django.db.models import Q
from django.urls import reverse

from dog.models import DogBreedDictionaryKo
from shelter.models import ShelterAnimal


DEFAULT_SHELTER_STATUS = "보호중"
RECOMMENDATION_KEYWORDS = ("견종 추천", "추천 견종", "강아지 추천", "반려견 추천", "키우기 쉬운 견종")
MAX_LINKED_BREEDS = 3
COMMON_BREED_ALIASES = (
    "말티즈",
    "푸들",
    "토이 푸들",
    "비숑",
    "비숑 프리제",
    "포메라니안",
    "치와와",
    "시츄",
    "요크셔 테리어",
    "닥스훈트",
    "웰시코기",
    "골든 리트리버",
    "래브라도 리트리버",
    "리트리버",
    "진돗개",
    "시바",
    "시바견",
    "보더 콜리",
    "코카 스파니엘",
    "슈나우저",
    "퍼그",
    "프렌치 불독",
)


@dataclass(frozen=True)
class ShelterBreedMatch:
    breed_name: str
    shelter_breed_name: str
    count: int
    url: str


def append_shelter_links_for_recommendation(
    *,
    question: str,
    answer: str,
    analysis,
) -> str:
    """Append shelter animal links when a breed recommendation mentions adoptable breeds."""

    if not _is_breed_recommendation(question=question, analysis=analysis):
        return answer

    matches = find_shelter_matches_for_text(f"{question}\n{answer}")
    if not matches:
        return answer

    lines = [
        "",
        "현재 보호자를 기다리는 아이들도 함께 확인해볼 수 있어요.",
    ]
    for match in matches:
        count_text = f"{match.count}마리" if match.count else "보호동물"
        lines.append(f"- {match.breed_name}: {count_text} 확인하기 {match.url}")

    return answer.rstrip() + "\n" + "\n".join(lines)


def find_shelter_matches_for_text(text: str) -> list[ShelterBreedMatch]:
    try:
        breed_candidates = _breed_candidates_from_text(text)
        matches: list[ShelterBreedMatch] = []

        for breed_name in breed_candidates:
            shelter_breed_name, count = _find_shelter_breed(breed_name)
            if not shelter_breed_name or count <= 0:
                continue
            matches.append(
                ShelterBreedMatch(
                    breed_name=breed_name,
                    shelter_breed_name=shelter_breed_name,
                    count=count,
                    url=_shelter_url(shelter_breed_name),
                )
            )
            if len(matches) >= MAX_LINKED_BREEDS:
                break

        return matches
    except (DatabaseError, ProgrammingError):
        return []


def _is_breed_recommendation(*, question: str, analysis) -> bool:
    topics = set(getattr(analysis, "topics", []) or [])
    if "breed_recommendation" in topics:
        return True

    normalized_question = " ".join(question.split())
    return any(keyword in normalized_question for keyword in RECOMMENDATION_KEYWORDS)


def _breed_candidates_from_text(text: str) -> list[str]:
    normalized_text = text.lower()
    candidates: list[str] = []

    for alias in COMMON_BREED_ALIASES:
        if alias.lower() in normalized_text and alias not in candidates:
            candidates.append(alias)

    breeds = (
        DogBreedDictionaryKo.objects.exclude(breed_name_ko__isnull=True)
        .exclude(breed_name_ko="")
        .values_list("breed_name_ko", "breed_name_en")
    )

    for breed_name_ko, breed_name_en in breeds:
        names = [breed_name_ko]
        if breed_name_en:
            names.append(breed_name_en)

        if any(name and name.lower() in normalized_text for name in names):
            if breed_name_ko not in candidates:
                candidates.append(breed_name_ko)

    candidates.sort(key=lambda name: normalized_text.find(name.lower()) if name.lower() in normalized_text else 99999)
    return candidates


def _find_shelter_breed(breed_name: str) -> tuple[str, int]:
    queryset = ShelterAnimal.objects.filter(process_state=DEFAULT_SHELTER_STATUS).filter(
        Q(kind_nm__icontains=breed_name) | Q(kind_full_nm__icontains=breed_name)
    )

    shelter_breed_name = (
        queryset.exclude(kind_nm__isnull=True)
        .exclude(kind_nm="")
        .values_list("kind_nm", flat=True)
        .first()
    )
    if not shelter_breed_name:
        return "", 0

    count = ShelterAnimal.objects.filter(
        process_state=DEFAULT_SHELTER_STATUS,
        kind_nm=shelter_breed_name,
    ).count()
    return shelter_breed_name, count


def _shelter_url(shelter_breed_name: str) -> str:
    query = urlencode(
        {
            "breed": shelter_breed_name,
            "status": DEFAULT_SHELTER_STATUS,
        }
    )
    return f"{reverse('shelter:list')}?{query}"