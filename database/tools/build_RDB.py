"""Relational Database Loader for Dog Breed Data.

This script reads dogapi_akc_matched_breeds.csv and populates the PostgreSQL 
relational tables ('breeds', 'breed_scores', 'breed_attributes') with columns 
up to 'akc_markings_array'.
"""

import csv
import json
import os
import sys
from pathlib import Path
from typing import Any

import psycopg
from dotenv import load_dotenv

# Define base directory and load .env file
BASE_DIR = Path(__file__).resolve().parents[2]
load_dotenv(BASE_DIR / ".env", encoding="utf-8-sig")


def db_config() -> dict[str, Any]:
    """Read database connection parameters from environment variables."""
    return {
        "host": os.getenv("POSTGRES_HOST", "localhost"),
        "port": int(os.getenv("POSTGRES_PORT", "5432")),
        "dbname": os.getenv("POSTGRES_DB", "pet_dog"),
        "user": os.getenv("POSTGRES_USER", "admin"),
        "password": os.getenv("POSTGRES_PASSWORD", "admin1234"),
    }


def clean_str(val: str) -> str | None:
    """Clean string values, returning None if empty or 'null'."""
    if not val:
        return None
    val = val.strip()
    if val.lower() == "null" or not val:
        return None
    return val


def clean_int(val: str) -> int | None:
    """Parse integer values, returning None if empty or 'null'."""
    cleaned = clean_str(val)
    if cleaned is None:
        return None
    try:
        return int(cleaned)
    except ValueError:
        return None


def clean_float(val: str) -> float | None:
    """Parse float values, returning None if empty or 'null'."""
    cleaned = clean_str(val)
    if cleaned is None:
        return None
    try:
        return float(cleaned)
    except ValueError:
        return None


def parse_json_array(val: str) -> list[str] | None:
    """Parse JSON array strings into Python lists of strings."""
    cleaned = clean_str(val)
    if cleaned is None or cleaned == "[]":
        return None
    try:
        data = json.loads(cleaned)
        if isinstance(data, list):
            return [str(item) for item in data]
        return [str(data)]
    except Exception:
        # Fallback if string is not valid JSON but has array-like structures
        stripped = cleaned.strip("[]\"' ")
        if not stripped:
            return None
        items = [item.strip(" \"'") for item in stripped.split(",")]
        return [item for item in items if item]


def load_csv_and_populate_db(csv_path: Path) -> None:
    """Reads the CSV and inserts parsed rows into the split Postgres tables."""
    if not csv_path.exists():
        print(f"Error: CSV file not found at {csv_path}", file=sys.stderr)
        sys.exit(1)

    print(f"Connecting to database with config: {db_config()}")
    
    with psycopg.connect(**db_config()) as conn:
        with conn.cursor() as cur:
            # 1. Truncate existing tables (CASCADE automatically clears breed_scores & breed_attributes)
            print("Truncating existing tables...")
            cur.execute("TRUNCATE TABLE breeds CASCADE;")
            
            # 2. Read and parse CSV file
            print(f"Reading CSV file from {csv_path}...")
            with csv_path.open("r", encoding="utf-8-sig") as f:
                reader = csv.DictReader(f)
                
                inserted_count = 0
                for row in reader:
                    # Clean and parse columns
                    breed_name = clean_str(row.get("matched_breed_name") or row.get("\ufeffmatched_breed_name") or "")
                    if not breed_name:
                        continue
                    
                    dogapi_id = clean_int(row.get("dogapi_id", ""))
                    breed_group = clean_str(row.get("dogapi_breed_group", ""))
                    life_span = clean_str(row.get("dogapi_life_span", ""))
                    temperament = clean_str(row.get("dogapi_temperament", ""))
                    origin = clean_str(row.get("dogapi_origin", ""))
                    weight_metric = clean_str(row.get("dogapi_weight_metric", ""))
                    height_metric = clean_str(row.get("dogapi_height_metric", ""))
                    image_url = clean_str(row.get("dogapi_image_url", ""))
                    
                    height_min = clean_float(row.get("akc_height_min", ""))
                    height_max = clean_float(row.get("akc_height_max", ""))
                    weight_min = clean_float(row.get("akc_weight_min", ""))
                    weight_max = clean_float(row.get("akc_weight_max", ""))
                    life_expectancy_min = clean_float(row.get("akc_life_expectancy_min", ""))
                    life_expectancy_max = clean_float(row.get("akc_life_expectancy_max", ""))
                    
                    # 2.1 Insert into core 'breeds' table
                    cur.execute(
                        """
                        INSERT INTO breeds (
                            breed_name, dogapi_id, breed_group, life_span, temperament, origin,
                            weight_metric, height_metric, image_url,
                            height_min, height_max, weight_min, weight_max,
                            life_expectancy_min, life_expectancy_max
                        ) VALUES (
                            %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
                        ) RETURNING id;
                        """,
                        (
                            breed_name, dogapi_id, breed_group, life_span, temperament, origin,
                            weight_metric, height_metric, image_url,
                            height_min, height_max, weight_min, weight_max,
                            life_expectancy_min, life_expectancy_max
                        )
                    )
                    breed_id = cur.fetchone()[0]
                    
                    # 2.2 Parse and insert into 'breed_scores' table
                    affectionate_family = clean_int(row.get("akc_affectionate_with_family_score", ""))
                    good_children = clean_int(row.get("akc_good_with_young_children_score", ""))
                    good_dogs = clean_int(row.get("akc_good_with_other_dogs_score", ""))
                    shedding_level = clean_int(row.get("akc_shedding_level_score", ""))
                    grooming_frequency = clean_int(row.get("akc_coat_grooming_frequency_score", ""))
                    drooling_level = clean_int(row.get("akc_drooling_level_score", ""))
                    openness_strangers = clean_int(row.get("akc_openness_to_strangers_score", ""))
                    playfulness_level = clean_int(row.get("akc_playfulness_level_score", ""))
                    watchdog_nature = clean_int(row.get("akc_watchdog_protective_nature_score", ""))
                    adaptability_level = clean_int(row.get("akc_adaptability_level_score", ""))
                    trainability_level = clean_int(row.get("akc_trainability_level_score", ""))
                    energy_level = clean_int(row.get("akc_energy_level_score", ""))
                    barking_level = clean_int(row.get("akc_barking_level_score", ""))
                    mental_stimulation = clean_int(row.get("akc_mental_stimulation_needs_score", ""))
                    
                    cur.execute(
                        """
                        INSERT INTO breed_scores (
                            breed_id, affectionate_with_family_score, good_with_young_children_score,
                            good_with_other_dogs_score, shedding_level_score, coat_grooming_frequency_score,
                            drooling_level_score, openness_to_strangers_score, playfulness_level_score,
                            watchdog_protective_nature_score, adaptability_level_score,
                            trainability_level_score, energy_level_score, barking_level_score,
                            mental_stimulation_needs_score
                        ) VALUES (
                            %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
                        );
                        """,
                        (
                            breed_id, affectionate_family, good_children, good_dogs, shedding_level,
                            grooming_frequency, drooling_level, openness_strangers, playfulness_level,
                            watchdog_nature, adaptability_level, trainability_level, energy_level,
                            barking_level, mental_stimulation
                        )
                    )
                    
                    # 2.3 Parse and insert into 'breed_attributes' table
                    coat_type = parse_json_array(row.get("akc_coat_type_array", ""))
                    coat_length = parse_json_array(row.get("akc_coat_length_array", ""))
                    colors = parse_json_array(row.get("akc_colors_array", ""))
                    markings = parse_json_array(row.get("akc_markings_array", ""))
                    
                    cur.execute(
                        """
                        INSERT INTO breed_attributes (
                            breed_id, coat_type_array, coat_length_array, colors_array, markings_array
                        ) VALUES (
                            %s, %s, %s, %s, %s
                        );
                        """,
                        (breed_id, coat_type, coat_length, colors, markings)
                    )
                    
                    inserted_count += 1
            
            # Commit the transaction
            conn.commit()
            print(f"Successfully loaded {inserted_count} breeds into relational tables.")


def main() -> None:
    csv_path = BASE_DIR / "database" / "contents" / "dog_api" / "dogapi_akc_matched_breeds.csv"
    load_csv_and_populate_db(csv_path)


if __name__ == "__main__":
    main()
