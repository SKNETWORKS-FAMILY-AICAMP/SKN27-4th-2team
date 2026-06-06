"""Load Korean dog breed dictionary JSON into PostgreSQL.

This loader uses database/contents/dog_api/dogapi_akc_matched_breeds_ko.json
as the source for the dog-breed encyclopedia page.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any

try:
    import psycopg
except ImportError as exc:  # pragma: no cover - runtime environment guard
    raise SystemExit(
        "psycopg is required. Install project dependencies first: "
        "pip install -r requirements.txt"
    ) from exc


BASE_DIR = Path(__file__).resolve().parents[2]
DEFAULT_JSON_PATH = (
    BASE_DIR
    / "database"
    / "contents"
    / "dog_api"
    / "dogapi_akc_matched_breeds_ko_kc10groups.json"
)


CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS dog_breed_dictionary_ko (
    id BIGSERIAL PRIMARY KEY,
    breed_name_en VARCHAR(150) UNIQUE NOT NULL,
    breed_name_ko VARCHAR(150) NOT NULL,
    dogapi_id INTEGER,
    breed_group VARCHAR(100),
    breed_group_number INTEGER,
    breed_group_description TEXT,
    temperament TEXT,
    origin VARCHAR(200),
    image_url TEXT,
    height_min_cm NUMERIC(6,2),
    height_max_cm NUMERIC(6,2),
    weight_min_kg NUMERIC(6,2),
    weight_max_kg NUMERIC(6,2),
    life_expectancy_min INTEGER,
    life_expectancy_max INTEGER,
    affectionate_with_family_score INTEGER,
    good_with_young_children_score INTEGER,
    good_with_other_dogs_score INTEGER,
    shedding_level_score INTEGER,
    grooming_needs_score INTEGER,
    drooling_level_score INTEGER,
    openness_to_strangers_score INTEGER,
    playfulness_level_score INTEGER,
    watchdog_score INTEGER,
    adaptability_score INTEGER,
    trainability_score INTEGER,
    energy_level_score INTEGER,
    barking_level_score INTEGER,
    mental_stimulation_needs_score INTEGER,
    coat_type TEXT,
    coat_length TEXT,
    colors TEXT,
    markings TEXT,
    about TEXT,
    health TEXT,
    grooming TEXT,
    exercise TEXT,
    training TEXT,
    nutrition TEXT,
    history TEXT,
    raw_data JSONB NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_dog_breed_dictionary_ko_group
    ON dog_breed_dictionary_ko (breed_group);

CREATE INDEX IF NOT EXISTS idx_dog_breed_dictionary_ko_origin
    ON dog_breed_dictionary_ko (origin);
"""


UPSERT_SQL = """
INSERT INTO dog_breed_dictionary_ko (
    breed_name_en,
    breed_name_ko,
    dogapi_id,
    breed_group,
    breed_group_number,
    breed_group_description,
    temperament,
    origin,
    image_url,
    height_min_cm,
    height_max_cm,
    weight_min_kg,
    weight_max_kg,
    life_expectancy_min,
    life_expectancy_max,
    affectionate_with_family_score,
    good_with_young_children_score,
    good_with_other_dogs_score,
    shedding_level_score,
    grooming_needs_score,
    drooling_level_score,
    openness_to_strangers_score,
    playfulness_level_score,
    watchdog_score,
    adaptability_score,
    trainability_score,
    energy_level_score,
    barking_level_score,
    mental_stimulation_needs_score,
    coat_type,
    coat_length,
    colors,
    markings,
    about,
    health,
    grooming,
    exercise,
    training,
    nutrition,
    history,
    raw_data
) VALUES (
    %(breed_name_en)s,
    %(breed_name_ko)s,
    %(dogapi_id)s,
    %(breed_group)s,
    %(breed_group_number)s,
    %(breed_group_description)s,
    %(temperament)s,
    %(origin)s,
    %(image_url)s,
    %(height_min_cm)s,
    %(height_max_cm)s,
    %(weight_min_kg)s,
    %(weight_max_kg)s,
    %(life_expectancy_min)s,
    %(life_expectancy_max)s,
    %(affectionate_with_family_score)s,
    %(good_with_young_children_score)s,
    %(good_with_other_dogs_score)s,
    %(shedding_level_score)s,
    %(grooming_needs_score)s,
    %(drooling_level_score)s,
    %(openness_to_strangers_score)s,
    %(playfulness_level_score)s,
    %(watchdog_score)s,
    %(adaptability_score)s,
    %(trainability_score)s,
    %(energy_level_score)s,
    %(barking_level_score)s,
    %(mental_stimulation_needs_score)s,
    %(coat_type)s,
    %(coat_length)s,
    %(colors)s,
    %(markings)s,
    %(about)s,
    %(health)s,
    %(grooming)s,
    %(exercise)s,
    %(training)s,
    %(nutrition)s,
    %(history)s,
    %(raw_data)s::jsonb
)
ON CONFLICT (breed_name_en)
DO UPDATE SET
    breed_name_ko = EXCLUDED.breed_name_ko,
    dogapi_id = EXCLUDED.dogapi_id,
    breed_group = EXCLUDED.breed_group,
    breed_group_number = EXCLUDED.breed_group_number,
    breed_group_description = EXCLUDED.breed_group_description,
    temperament = EXCLUDED.temperament,
    origin = EXCLUDED.origin,
    image_url = EXCLUDED.image_url,
    height_min_cm = EXCLUDED.height_min_cm,
    height_max_cm = EXCLUDED.height_max_cm,
    weight_min_kg = EXCLUDED.weight_min_kg,
    weight_max_kg = EXCLUDED.weight_max_kg,
    life_expectancy_min = EXCLUDED.life_expectancy_min,
    life_expectancy_max = EXCLUDED.life_expectancy_max,
    affectionate_with_family_score = EXCLUDED.affectionate_with_family_score,
    good_with_young_children_score = EXCLUDED.good_with_young_children_score,
    good_with_other_dogs_score = EXCLUDED.good_with_other_dogs_score,
    shedding_level_score = EXCLUDED.shedding_level_score,
    grooming_needs_score = EXCLUDED.grooming_needs_score,
    drooling_level_score = EXCLUDED.drooling_level_score,
    openness_to_strangers_score = EXCLUDED.openness_to_strangers_score,
    playfulness_level_score = EXCLUDED.playfulness_level_score,
    watchdog_score = EXCLUDED.watchdog_score,
    adaptability_score = EXCLUDED.adaptability_score,
    trainability_score = EXCLUDED.trainability_score,
    energy_level_score = EXCLUDED.energy_level_score,
    barking_level_score = EXCLUDED.barking_level_score,
    mental_stimulation_needs_score = EXCLUDED.mental_stimulation_needs_score,
    coat_type = EXCLUDED.coat_type,
    coat_length = EXCLUDED.coat_length,
    colors = EXCLUDED.colors,
    markings = EXCLUDED.markings,
    about = EXCLUDED.about,
    health = EXCLUDED.health,
    grooming = EXCLUDED.grooming,
    exercise = EXCLUDED.exercise,
    training = EXCLUDED.training,
    nutrition = EXCLUDED.nutrition,
    history = EXCLUDED.history,
    raw_data = EXCLUDED.raw_data,
    updated_at = NOW();
"""


def load_env() -> None:
    env_path = BASE_DIR / ".env"
    if not env_path.exists():
        return

    for line in env_path.read_text(encoding="utf-8-sig").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, value = stripped.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def db_config() -> dict[str, Any]:
    return {
        "host": os.getenv("POSTGRES_HOST", "localhost"),
        "port": int(os.getenv("POSTGRES_PORT", "5432")),
        "dbname": os.getenv("POSTGRES_DB", "pet_dog"),
        "user": os.getenv("POSTGRES_USER", "admin"),
        "password": os.getenv("POSTGRES_PASSWORD", "admin1234"),
    }


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
        "breed_group": clean_str(row.get("견종그룹명")),
        "breed_group_number": clean_int(row.get("견종그룹번호")),
        "breed_group_description": clean_str(row.get("견종그룹설명")),
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

def load_rows(json_path: Path) -> list[dict[str, Any]]:
    if not json_path.exists():
        raise FileNotFoundError(f"JSON file not found: {json_path}")
    rows = json.loads(json_path.read_text(encoding="utf-8"))
    if not isinstance(rows, list):
        raise ValueError("Top-level JSON must be a list of rows.")
    return rows


def load_into_db(json_path: Path, truncate: bool = False) -> int:
    rows = load_rows(json_path)
    normalized_rows = [normalize_row(row) for row in rows]
    missing_names = [row for row in normalized_rows if not row["breed_name_en"] or not row["breed_name_ko"]]
    if missing_names:
        raise ValueError(f"Rows with missing breed names: {len(missing_names)}")

    with psycopg.connect(**db_config()) as conn:
        with conn.cursor() as cur:
            cur.execute(CREATE_TABLE_SQL)
            if truncate:
                cur.execute("TRUNCATE TABLE dog_breed_dictionary_ko RESTART IDENTITY;")
            cur.executemany(UPSERT_SQL, normalized_rows)
            cur.execute("SELECT COUNT(*) FROM dog_breed_dictionary_ko;")
            total_count = cur.fetchone()[0]
        conn.commit()

    print(f"Loaded {len(normalized_rows)} rows from {json_path}")
    print(f"dog_breed_dictionary_ko row count: {total_count}")
    return total_count


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--json", type=Path, default=DEFAULT_JSON_PATH)
    parser.add_argument("--truncate", action="store_true")
    return parser.parse_args()


def main() -> None:
    load_env()
    args = parse_args()
    try:
        load_into_db(args.json, truncate=args.truncate)
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
