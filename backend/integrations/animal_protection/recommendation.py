"""Recommendation-to-shelter animal lookup helpers."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .client import AnimalProtectionClient, DOG_UP_KIND_CODE, normalize_abandonments


PROJECT_ROOT = Path(__file__).resolve().parents[3]
ANIMAL_DIR = PROJECT_ROOT / "database" / "animal_protection"
BREED_CODE_MAPPING_PATH = ANIMAL_DIR / "breed_code_mapping.json"
RESPONSES_DIR = ANIMAL_DIR / "responses"


def load_breed_code_mapping(path: Path = BREED_CODE_MAPPING_PATH) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def get_kind_code_for_recommended_breed(breed: str, mapping: dict[str, Any] | None = None) -> str | None:
    mapping = mapping or load_breed_code_mapping()
    breed_info = mapping.get("breeds", {}).get(breed)
    if not breed_info:
        return None
    return str(breed_info.get("kind_code") or "") or None


def fetch_recommended_shelter_animals(
    breed: str,
    *,
    upr_cd: str | None = None,
    org_cd: str | None = None,
    state: str = "protect",
    limit: int = 3,
    client: AnimalProtectionClient | None = None,
) -> list[dict[str, Any]]:
    api_client = client or AnimalProtectionClient()
    kind_code = get_kind_code_for_recommended_breed(breed)

    params: dict[str, Any] = {
        "upkind": DOG_UP_KIND_CODE,
        "kind": kind_code,
        "upr_cd": upr_cd,
        "org_cd": org_cd,
        "state": state,
        "pageNo": 1,
        "numOfRows": limit,
    }
    response = api_client.get_abandonments(**params)
    animals = normalize_abandonments(response)

    if animals or not kind_code:
        return animals

    fallback_params = {
        "upkind": DOG_UP_KIND_CODE,
        "upr_cd": upr_cd,
        "org_cd": org_cd,
        "state": state,
        "pageNo": 1,
        "numOfRows": limit,
    }
    fallback_response = api_client.get_abandonments(**fallback_params)
    return normalize_abandonments(fallback_response)


def save_recommended_lookup_response(
    breed: str,
    *,
    upr_cd: str | None = "6110000",
    org_cd: str | None = None,
    limit: int = 3,
) -> Path:
    animals = fetch_recommended_shelter_animals(breed, upr_cd=upr_cd, org_cd=org_cd, limit=limit)
    safe_breed = breed.replace(" ", "_").replace("/", "_")
    output_path = RESPONSES_DIR / f"latest_recommended_{safe_breed}_animals.json"
    output_path.write_text(json.dumps(animals, ensure_ascii=False, indent=2), encoding="utf-8")
    return output_path
