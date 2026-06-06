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

from _utils.clean import normalize_row
from _utils.argparser import get_database_args
from _utils.db import get_db_config

try:
    import psycopg
except ImportError as exc:  # pragma: no cover - runtime environment guard
    raise SystemExit(
        "psycopg is required. Install project dependencies first: "
        "pip install -r requirements.txt"
    ) from exc


# BASE_DIR = Path(__file__).resolve().parents[2]
# DEFAULT_JSON_PATH = (
#     BASE_DIR
#     / "database"
#     / "contents"
#     / "dog_api"
#     / "dogapi_akc_matched_breeds_ko.json"
# )


CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS dog_breed_dictionary_ko (
    id BIGSERIAL PRIMARY KEY,
    breed_name_en VARCHAR(150) UNIQUE NOT NULL,
    breed_name_ko VARCHAR(150) NOT NULL,
    dogapi_id INTEGER,
    breed_group VARCHAR(100),
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

    with psycopg.connect(**get_db_config()) as conn:
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


# def parse_args() -> argparse.Namespace:
#     parser = argparse.ArgumentParser()
#     parser.add_argument("--json", type=Path, default=DEFAULT_JSON_PATH)
#     parser.add_argument("--truncate", action="store_true")
#     return parser.parse_args()


def main() -> None:
    args = get_database_args()
    try:
        load_into_db(args.json, truncate=args.truncate)
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
