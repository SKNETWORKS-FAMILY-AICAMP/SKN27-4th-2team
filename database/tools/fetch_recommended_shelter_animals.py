"""Fetch protected animals by a recommended breed name."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.integrations.animal_protection.client import load_dotenv_file  # noqa: E402
from backend.integrations.animal_protection.recommendation import (  # noqa: E402
    fetch_recommended_shelter_animals,
    get_kind_code_for_recommended_breed,
    save_recommended_lookup_response,
)


def main() -> None:
    parser = argparse.ArgumentParser(description="Fetch protected animals for a recommended dog breed.")
    parser.add_argument("--breed", default="말티즈", help="Recommended breed name, e.g. 말티즈")
    parser.add_argument("--upr-cd", default="6110000", help="Sido code. Default is Seoul.")
    parser.add_argument("--org-cd", default=None, help="Sigungu code. Optional.")
    parser.add_argument("--limit", type=int, default=3, help="Number of animals to fetch.")
    parser.add_argument("--save", action="store_true", help="Save result under database/animal_protection/responses.")
    args = parser.parse_args()

    load_dotenv_file(PROJECT_ROOT / ".env")
    kind_code = get_kind_code_for_recommended_breed(args.breed)
    animals = fetch_recommended_shelter_animals(
        args.breed,
        upr_cd=args.upr_cd,
        org_cd=args.org_cd,
        limit=args.limit,
    )

    output = {
        "breed": args.breed,
        "kind_code": kind_code,
        "upr_cd": args.upr_cd,
        "org_cd": args.org_cd,
        "count": len(animals),
        "animals": animals,
    }
    if args.save:
        saved_path = save_recommended_lookup_response(args.breed, upr_cd=args.upr_cd, org_cd=args.org_cd, limit=args.limit)
        output["saved_path"] = str(saved_path)

    print(json.dumps(output, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
