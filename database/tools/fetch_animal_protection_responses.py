"""Fetch real public API responses for animal protection integration planning.

This script reads ANIMAL_API_SERVICE_KEY from the project .env, calls the public
APIs, and stores the actual responses under database/animal_protection/responses.
It does not modify existing app files.
"""

from __future__ import annotations

import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.integrations.animal_protection.client import (  # noqa: E402
    AnimalProtectionClient,
    DOG_UP_KIND_CODE,
    extract_items,
    load_dotenv_file,
    normalize_abandonments,
)

OUTPUT_DIR = PROJECT_ROOT / "database" / "animal_protection" / "responses"
SEOUL_NAME = "서울특별시"


def save_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def find_code(items: list[dict[str, Any]], name: str) -> str | None:
    for item in items:
        if item.get("orgdownNm") == name or item.get("knm") == name:
            return str(item.get("orgCd") or item.get("kindCd") or "")
    return None


def main() -> None:
    load_dotenv_file(PROJECT_ROOT / ".env")
    client = AnimalProtectionClient()

    fetched_at = datetime.now().isoformat(timespec="seconds")

    sido_response = client.get_sido(num_of_rows=50)
    sido_items = extract_items(sido_response)
    seoul_code = find_code(sido_items, SEOUL_NAME)

    sigungu_response = None
    if seoul_code:
        sigungu_response = client.get_sigungu(seoul_code, num_of_rows=100)

    dog_kind_response = client.get_kind(DOG_UP_KIND_CODE, num_of_rows=300)
    abandonment_response = client.get_abandonments(upkind=DOG_UP_KIND_CODE, numOfRows=10, pageNo=1)
    normalized_animals = normalize_abandonments(abandonment_response)

    save_json(OUTPUT_DIR / "latest_sido_response.json", sido_response)
    if sigungu_response is not None:
        save_json(OUTPUT_DIR / "latest_sigungu_seoul_response.json", sigungu_response)
    save_json(OUTPUT_DIR / "latest_dog_kind_response.json", dog_kind_response)
    save_json(OUTPUT_DIR / "latest_abandonment_dogs_response.json", abandonment_response)
    save_json(OUTPUT_DIR / "latest_normalized_shelter_animals.json", normalized_animals)

    manifest = {
        "fetched_at": fetched_at,
        "service_key_env": "ANIMAL_API_SERVICE_KEY",
        "outputs": {
            "sido": "latest_sido_response.json",
            "sigungu_seoul": "latest_sigungu_seoul_response.json" if sigungu_response else None,
            "dog_kind": "latest_dog_kind_response.json",
            "abandonment_dogs": "latest_abandonment_dogs_response.json",
            "normalized_shelter_animals": "latest_normalized_shelter_animals.json",
        },
        "discovered_codes": {
            "dog_up_kind_code": DOG_UP_KIND_CODE,
            "seoul_upr_cd": seoul_code,
        },
        "counts": {
            "sido_items": len(sido_items),
            "sigungu_seoul_items": len(extract_items(sigungu_response)) if sigungu_response else 0,
            "dog_kind_items": len(extract_items(dog_kind_response)),
            "abandonment_dog_items": len(extract_items(abandonment_response)),
            "normalized_shelter_animals": len(normalized_animals),
        },
    }
    save_json(OUTPUT_DIR / "latest_manifest.json", manifest)

    print(json.dumps(manifest, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
