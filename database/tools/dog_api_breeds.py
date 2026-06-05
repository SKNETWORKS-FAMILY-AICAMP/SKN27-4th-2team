import argparse
import csv
import json
import os
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


ROOT_DIR = Path(__file__).resolve().parents[2]
ENV_FILES = [ROOT_DIR / ".env", ROOT_DIR.parent / ".env"]
OUTPUT_DIR = ROOT_DIR / "database" / "contents" / "dog_api"
API_BASE_URL = "https://api.thedogapi.com/v1"


def load_env_value(key, env_files=ENV_FILES):
    if key in os.environ:
        return os.environ[key]

    for env_file in env_files:
        if not env_file.exists():
            continue

        for line in env_file.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue

            name, value = line.split("=", 1)
            if name.strip() == key:
                return value.strip().strip('"').strip("'")

    return None


def request_json(path, api_key, params=None):
    query = f"?{urlencode(params)}" if params else ""
    url = f"{API_BASE_URL}{path}{query}"
    request = Request(url, headers={"x-api-key": api_key})

    try:
        with urlopen(request, timeout=20) as response:
            body = response.read().decode("utf-8")
            return json.loads(body)
    except HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"TheDogAPI request failed: HTTP {exc.code} {detail}") from exc
    except URLError as exc:
        raise RuntimeError(f"TheDogAPI request failed: {exc.reason}") from exc


def flatten_breed(breed):
    image = breed.get("image") or {}
    weight = breed.get("weight") or {}
    height = breed.get("height") or {}

    return {
        "id": breed.get("id"),
        "name": breed.get("name"),
        "breed_group": breed.get("breed_group"),
        "life_span": breed.get("life_span"),
        "temperament": breed.get("temperament"),
        "origin": breed.get("origin"),
        "bred_for": breed.get("bred_for"),
        "weight_metric": weight.get("metric"),
        "height_metric": height.get("metric"),
        "reference_image_id": breed.get("reference_image_id"),
        "image_url": image.get("url"),
    }


def save_json(data, path):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def save_csv(rows, path):
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "id",
        "name",
        "breed_group",
        "life_span",
        "temperament",
        "origin",
        "bred_for",
        "weight_metric",
        "height_metric",
        "reference_image_id",
        "image_url",
    ]

    with path.open("w", encoding="utf-8-sig", newline="") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def fetch_breeds(api_key, search=None):
    if search:
        return request_json("/breeds/search", api_key, params={"q": search})
    return request_json("/breeds", api_key)


def main():
    parser = argparse.ArgumentParser(description="Fetch dog breed data from TheDogAPI.")
    parser.add_argument("--search", help="Search keyword, for example: terrier")
    args = parser.parse_args()

    api_key = load_env_value("THE_DOG_API_KEY")
    if not api_key:
        paths = ", ".join(str(path) for path in ENV_FILES)
        raise RuntimeError(f"THE_DOG_API_KEY is missing. Checked: {paths}")

    breeds = fetch_breeds(api_key, search=args.search)
    suffix = f"_search_{args.search}" if args.search else ""

    json_path = OUTPUT_DIR / f"breeds{suffix}.json"
    csv_path = OUTPUT_DIR / f"breeds{suffix}.csv"

    save_json(breeds, json_path)
    save_csv([flatten_breed(breed) for breed in breeds], csv_path)

    print(f"Saved {len(breeds)} breeds")
    print(f"JSON: {json_path}")
    print(f"CSV: {csv_path}")


if __name__ == "__main__":
    main()
