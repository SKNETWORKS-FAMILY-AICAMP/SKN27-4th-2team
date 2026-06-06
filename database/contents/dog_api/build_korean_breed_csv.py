import csv
import http.client
import json
import os
import sys
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent
SOURCE = BASE_DIR / "dogapi_akc_matched_breeds.csv"
OUTPUT = BASE_DIR / "dogapi_akc_matched_breeds_ko.csv"
CACHE = BASE_DIR / ".dogapi_akc_matched_breeds_ko_cache.json"
MODEL = os.environ.get("OPENAI_TRANSLATION_MODEL", "gpt-4o-mini")
BATCH_SIZE = int(os.environ.get("OPENAI_TRANSLATION_BATCH_SIZE", "1"))
MAX_WORKERS = int(os.environ.get("OPENAI_TRANSLATION_MAX_WORKERS", "12"))

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

TEXT_FIELDS = [
    "matched_breed_name",
    "dogapi_breed_group",
    "dogapi_temperament",
    "dogapi_origin",
    "akc_coat_type_array",
    "akc_coat_length_array",
    "akc_colors_array",
    "akc_markings_array",
    "akc_about_the_breed",
    "akc_health",
    "akc_grooming",
    "akc_exercise",
    "akc_training",
    "akc_nutrition",
    "akc_history",
]

SCORE_COLUMNS = {
    "akc_affectionate_with_family_score": "가족_친화도_점수",
    "akc_good_with_young_children_score": "어린이_친화도_점수",
    "akc_good_with_other_dogs_score": "다른개_친화도_점수",
    "akc_shedding_level_score": "털빠짐_수준_점수",
    "akc_coat_grooming_frequency_score": "미용_필요도_점수",
    "akc_drooling_level_score": "침흘림_수준_점수",
    "akc_openness_to_strangers_score": "낯선사람_친화도_점수",
    "akc_playfulness_level_score": "장난기_수준_점수",
    "akc_watchdog_protective_nature_score": "경비_보호본능_점수",
    "akc_adaptability_level_score": "적응력_점수",
    "akc_trainability_level_score": "훈련_용이성_점수",
    "akc_energy_level_score": "에너지_수준_점수",
    "akc_barking_level_score": "짖는_수준_점수",
    "akc_mental_stimulation_needs_score": "지적자극_필요도_점수",
}

OUTPUT_COLUMNS = [
    "견종명_영문",
    "견종명_한글",
    "dogapi_id",
    "견종그룹",
    "성격",
    "출신",
    "이미지URL",
    "키_최소_cm",
    "키_최대_cm",
    "체중_최소_kg",
    "체중_최대_kg",
    "평균수명_최소_년",
    "평균수명_최대_년",
    *SCORE_COLUMNS.values(),
    "털_타입",
    "털_길이",
    "털_색상",
    "무늬",
    "견종소개",
    "건강",
    "미용",
    "운동",
    "훈련",
    "영양",
    "역사",
]


def load_dotenv_key():
    if os.environ.get("OPENAI_API_KEY"):
        return os.environ["OPENAI_API_KEY"]

    env_path = BASE_DIR.parents[2] / ".env"
    if not env_path.exists():
        return None

    for line in env_path.read_text(encoding="utf-8-sig").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, value = stripped.split("=", 1)
        if key.strip() == "OPENAI_API_KEY":
            return value.strip().strip('"').strip("'")
    return None


def to_float(value):
    if value is None or str(value).strip() == "":
        return None
    return float(value)


def convert_weight_lb_to_kg(value):
    number = to_float(value)
    return "" if number is None else round(number * 0.453592, 1)


def convert_height_in_to_cm(value):
    number = to_float(value)
    return "" if number is None else round(number * 2.54, 1)


def load_cache():
    if CACHE.exists():
        return json.loads(CACHE.read_text(encoding="utf-8"))
    return {}


def save_cache(cache):
    temp_cache = CACHE.with_suffix(".json.tmp")
    temp_cache.write_text(json.dumps(cache, ensure_ascii=True, indent=2), encoding="utf-8")
    temp_cache.replace(CACHE)


def translate_batch(api_key, rows):
    payload_rows = [
        {
            "key": row["matched_breed_name"],
            "data": {field: row.get(field, "") for field in TEXT_FIELDS},
        }
        for row in rows
    ]

    messages = [
        {
            "role": "system",
            "content": (
                "You translate dog breed encyclopedia data into natural Korean. "
                "Return only valid JSON. Preserve meaning, numbers, and medical facts. "
                "For arrays encoded as JSON strings, return a concise Korean comma-separated string. "
                "Translate breed names into commonly used Korean names when known; otherwise use Korean transliteration. "
                "Use an informative encyclopedia tone for long fields."
            ),
        },
        {
            "role": "user",
            "content": json.dumps(
                {
                    "instruction": (
                        "Translate each row's data values to Korean. "
                        "Return JSON exactly as {\"rows\":[{\"key\":\"...\",\"data\":{same keys}}]}."
                    ),
                    "rows": payload_rows,
                },
                ensure_ascii=False,
            ),
        },
    ]

    request_body = json.dumps(
        {
            "model": MODEL,
            "messages": messages,
            "temperature": 0.1,
            "response_format": {"type": "json_object"},
            "max_completion_tokens": 16000,
        }
    ).encode("utf-8")

    request = urllib.request.Request(
        "https://api.openai.com/v1/chat/completions",
        data=request_body,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )

    for attempt in range(5):
        try:
            with urllib.request.urlopen(request, timeout=300) as response:
                body = json.loads(response.read().decode("utf-8"))
            content = body["choices"][0]["message"]["content"]
            parsed = json.loads(content)
            translated_rows = parsed.get("rows", [])
            return {
                item["key"]: item.get("data", {})
                for item in translated_rows
                if "key" in item
            }
        except (
            http.client.RemoteDisconnected,
            urllib.error.HTTPError,
            urllib.error.URLError,
            TimeoutError,
        ) as exc:
            if attempt == 4:
                raise
            wait_seconds = 2 ** attempt
            names = ", ".join(row["matched_breed_name"] for row in rows)
            print(f"Retrying batch [{names}] after error: {exc}. wait={wait_seconds}s")
            time.sleep(wait_seconds)


def build_output_row(row, translated):
    return {
        "견종명_영문": row.get("matched_breed_name", ""),
        "견종명_한글": translated.get("matched_breed_name", ""),
        "dogapi_id": row.get("dogapi_id", ""),
        "견종그룹": translated.get("dogapi_breed_group", ""),
        "성격": translated.get("dogapi_temperament", ""),
        "출신": translated.get("dogapi_origin", ""),
        "이미지URL": row.get("dogapi_image_url", ""),
        "키_최소_cm": convert_height_in_to_cm(row.get("akc_height_min")),
        "키_최대_cm": convert_height_in_to_cm(row.get("akc_height_max")),
        "체중_최소_kg": convert_weight_lb_to_kg(row.get("akc_weight_min")),
        "체중_최대_kg": convert_weight_lb_to_kg(row.get("akc_weight_max")),
        "평균수명_최소_년": row.get("akc_life_expectancy_min", ""),
        "평균수명_최대_년": row.get("akc_life_expectancy_max", ""),
        **{ko: row.get(en, "") for en, ko in SCORE_COLUMNS.items()},
        "털_타입": translated.get("akc_coat_type_array", ""),
        "털_길이": translated.get("akc_coat_length_array", ""),
        "털_색상": translated.get("akc_colors_array", ""),
        "무늬": translated.get("akc_markings_array", ""),
        "견종소개": translated.get("akc_about_the_breed", ""),
        "건강": translated.get("akc_health", ""),
        "미용": translated.get("akc_grooming", ""),
        "운동": translated.get("akc_exercise", ""),
        "훈련": translated.get("akc_training", ""),
        "영양": translated.get("akc_nutrition", ""),
        "역사": translated.get("akc_history", ""),
    }


def main():
    api_key = load_dotenv_key()
    if not api_key:
        raise SystemExit("OPENAI_API_KEY was not found in environment or .env")

    with SOURCE.open("r", encoding="utf-8-sig", newline="") as source_file:
        rows = list(csv.DictReader(source_file))

    cache = load_cache()
    output_rows = []

    missing_rows = [row for row in rows if row["matched_breed_name"] not in cache]
    batches = [missing_rows[i : i + BATCH_SIZE] for i in range(0, len(missing_rows), BATCH_SIZE)]

    if batches:
        print(
            f"Translating {len(missing_rows)} missing rows with {MAX_WORKERS} workers",
            flush=True,
        )
        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
            futures = {
                executor.submit(translate_batch, api_key, batch): batch
                for batch in batches
            }

            completed = 0
            for future in as_completed(futures):
                batch = futures[future]
                translated_batch = future.result()
                for row in batch:
                    row_key = row["matched_breed_name"]
                    if row_key not in translated_batch:
                        if len(batch) == 1 and len(translated_batch) == 1:
                            cache[row_key] = next(iter(translated_batch.values()))
                            continue
                        raise RuntimeError(f"Missing translation for {row_key}")
                    cache[row_key] = translated_batch[row_key]

                completed += len(batch)
                save_cache(cache)
                names = ", ".join(row["matched_breed_name"] for row in batch)
                print(
                    f"Translated {completed}/{len(missing_rows)} missing rows: {names}",
                    flush=True,
                )
    else:
        print("Using cache for all rows", flush=True)

    for row in rows:
        row_key = row["matched_breed_name"]
        output_rows.append(build_output_row(row, cache[row_key]))

    with OUTPUT.open("w", encoding="utf-8-sig", newline="") as output_file:
        writer = csv.DictWriter(output_file, fieldnames=OUTPUT_COLUMNS)
        writer.writeheader()
        writer.writerows(output_rows)

    print(f"Wrote {len(output_rows)} rows to {OUTPUT}")


if __name__ == "__main__":
    main()
