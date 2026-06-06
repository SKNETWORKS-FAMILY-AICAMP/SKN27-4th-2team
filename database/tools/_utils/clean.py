import re
import json
from typing import Any

def clean_text(text):
    """텍스트 내 잔여 특수문자 및 공백 문자 제거"""
    if not isinstance(text, str):
        return ""
    text = text.replace('\xa0', ' ')
    text = re.sub(r'\s+', ' ', text)
    return text.strip()

def clean_str(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def clean_int(value: Any) -> int | None:
    text = clean_str(value)
    if text is None:
        return None
    try:
        return int(float(text))
    except ValueError:
        return None


def clean_float(value: Any) -> float | None:
    text = clean_str(value)
    if text is None:
        return None
    try:
        return float(text)
    except ValueError:
        return None

def normalize_row(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "breed_name_en": clean_str(row.get("견종명_영문")),
        "breed_name_ko": clean_str(row.get("견종명_한글")),
        "dogapi_id": clean_int(row.get("dogapi_id")),
        "breed_group": clean_str(row.get("견종그룹")),
        "temperament": clean_str(row.get("성격")),
        "origin": clean_str(row.get("출신")),
        "image_url": clean_str(row.get("이미지URL")),
        "height_min_cm": clean_float(row.get("키_최소_cm")),
        "height_max_cm": clean_float(row.get("키_최대_cm")),
        "weight_min_kg": clean_float(row.get("체중_최소_kg")),
        "weight_max_kg": clean_float(row.get("체중_최대_kg")),
        "life_expectancy_min": clean_int(row.get("평균수명_최소_년")),
        "life_expectancy_max": clean_int(row.get("평균수명_최대_년")),
        "affectionate_with_family_score": clean_int(row.get("가족_친화도_점수")),
        "good_with_young_children_score": clean_int(row.get("어린이_친화도_점수")),
        "good_with_other_dogs_score": clean_int(row.get("다른개_친화도_점수")),
        "shedding_level_score": clean_int(row.get("털빠짐_수준_점수")),
        "grooming_needs_score": clean_int(row.get("미용_필요도_점수")),
        "drooling_level_score": clean_int(row.get("침흘림_수준_점수")),
        "openness_to_strangers_score": clean_int(row.get("낯선사람_친화도_점수")),
        "playfulness_level_score": clean_int(row.get("장난기_수준_점수")),
        "watchdog_score": clean_int(row.get("경비_보호본능_점수")),
        "adaptability_score": clean_int(row.get("적응력_점수")),
        "trainability_score": clean_int(row.get("훈련_용이성_점수")),
        "energy_level_score": clean_int(row.get("에너지_수준_점수")),
        "barking_level_score": clean_int(row.get("짖는_수준_점수")),
        "mental_stimulation_needs_score": clean_int(row.get("지적자극_필요도_점수")),
        "coat_type": clean_str(row.get("털_타입")),
        "coat_length": clean_str(row.get("털_길이")),
        "colors": clean_str(row.get("털_색상")),
        "markings": clean_str(row.get("무늬")),
        "about": clean_str(row.get("견종소개")),
        "health": clean_str(row.get("건강")),
        "grooming": clean_str(row.get("미용")),
        "exercise": clean_str(row.get("운동")),
        "training": clean_str(row.get("훈련")),
        "nutrition": clean_str(row.get("영양")),
        "history": clean_str(row.get("역사")),
        "raw_data": json.dumps(row, ensure_ascii=False),
    }