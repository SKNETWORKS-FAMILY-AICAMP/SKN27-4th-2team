"""Build breed-code mapping for animal protection API searches.

Input:
- database/animal_protection/breed_mapping.json
- database/animal_protection/responses/latest_dog_kind_response.json

Output:
- database/animal_protection/breed_code_mapping.json
"""

from __future__ import annotations

import json
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[2]
ANIMAL_DIR = PROJECT_ROOT / "database" / "animal_protection"
BREED_MAPPING_PATH = ANIMAL_DIR / "breed_mapping.json"
DOG_KIND_RESPONSE_PATH = ANIMAL_DIR / "responses" / "latest_dog_kind_response.json"
OUTPUT_PATH = ANIMAL_DIR / "breed_code_mapping.json"


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def extract_kind_items(response: dict[str, Any]) -> list[dict[str, str]]:
    item = response.get("response", {}).get("body", {}).get("items", {}).get("item", [])
    if isinstance(item, dict):
        return [item]
    if isinstance(item, list):
        return item
    return []


def normalize_name(value: str) -> str:
    return (
        value.replace(" ", "")
        .replace("-", "")
        .replace("_", "")
        .replace("[개]", "")
        .strip()
        .lower()
    )


def similarity(left: str, right: str) -> float:
    return SequenceMatcher(None, normalize_name(left), normalize_name(right)).ratio()


def find_best_match(candidates: list[str], public_kinds: list[dict[str, str]]) -> dict[str, Any] | None:
    normalized_candidates = {normalize_name(candidate) for candidate in candidates}

    for public_kind in public_kinds:
        public_name = str(public_kind.get("kindNm", ""))
        if normalize_name(public_name) in normalized_candidates:
            return {
                "kind_code": str(public_kind.get("kindCd", "")),
                "matched_public_name": public_name,
                "match_type": "exact",
                "score": 1.0,
            }

    scored_matches: list[dict[str, Any]] = []
    for candidate in candidates:
        for public_kind in public_kinds:
            public_name = str(public_kind.get("kindNm", ""))
            score = similarity(candidate, public_name)
            scored_matches.append(
                {
                    "kind_code": str(public_kind.get("kindCd", "")),
                    "matched_public_name": public_name,
                    "match_type": "fuzzy",
                    "score": round(score, 4),
                }
            )

    best = max(scored_matches, key=lambda match: match["score"], default=None)
    if best and best["score"] >= 0.72:
        return best
    return None


def main() -> None:
    breed_mapping: dict[str, list[str]] = load_json(BREED_MAPPING_PATH)
    dog_kind_response = load_json(DOG_KIND_RESPONSE_PATH)
    public_kinds = extract_kind_items(dog_kind_response)

    result: dict[str, Any] = {}
    unmatched: dict[str, list[str]] = {}

    for project_breed, candidates in breed_mapping.items():
        search_names = [project_breed, *candidates]
        match = find_best_match(search_names, public_kinds)
        if match:
            result[project_breed] = {
                **match,
                "public_names": candidates,
            }
        else:
            unmatched[project_breed] = candidates

    output = {
        "source": {
            "breed_mapping": str(BREED_MAPPING_PATH.relative_to(PROJECT_ROOT)),
            "dog_kind_response": str(DOG_KIND_RESPONSE_PATH.relative_to(PROJECT_ROOT)),
        },
        "matched_count": len(result),
        "unmatched_count": len(unmatched),
        "breeds": result,
        "unmatched": unmatched,
    }
    OUTPUT_PATH.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"output": str(OUTPUT_PATH), "matched": len(result), "unmatched": len(unmatched)}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

