import csv
import json
import os
import time
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


ROOT_DIR = Path(__file__).resolve().parents[2]
ENV_FILES = [ROOT_DIR / ".env", ROOT_DIR.parent / ".env"]
BREEDS_CSV = ROOT_DIR / "database" / "contents" / "dog_api" / "breeds.csv"
API_BASE_URL = "https://api.thedogapi.com/v1"


def load_env_value(key):
    # .env 파일에서 dog-api 키를 읽는 함수
    if key in os.environ:
        return os.environ[key]

    for env_file in ENV_FILES:
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
    request = Request(f"{API_BASE_URL}{path}{query}", headers={"x-api-key": api_key})

    try:
        with urlopen(request, timeout=8) as response:
            return json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"TheDogAPI request failed: HTTP {exc.code} {detail}") from exc
    except URLError as exc:
        raise RuntimeError(f"TheDogAPI request failed: {exc.reason}") from exc


def fetch_image_url(api_key, breed_id):
    images = request_json(
        "/images/search",
        api_key,
        params={"limit": 1, "breed_ids": breed_id},
    )
    if not images:
        return ""
    return images[0].get("url", "")


def safe_print(message):
    print(message.encode("cp949", errors="replace").decode("cp949"))


def save_csv(rows, fieldnames):
    with BREEDS_CSV.open("w", encoding="utf-8-sig", newline="") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def main():
    api_key = load_env_value("THE_DOG_API_KEY")
    if not api_key:
        paths = ", ".join(str(path) for path in ENV_FILES)
        raise RuntimeError(f"THE_DOG_API_KEY is missing. Checked: {paths}")

    with BREEDS_CSV.open(encoding="utf-8-sig", newline="") as csv_file:
        reader = csv.DictReader(csv_file)
        rows = list(reader)
        fieldnames = list(reader.fieldnames or [])

    if "image_url" not in fieldnames:
        fieldnames.append("image_url")

    filled = 0
    skipped = 0
    failed = 0

    for index, row in enumerate(rows, start=1):
        if row.get("image_url"):
            skipped += 1
            continue

        breed_id = row.get("id")
        if not breed_id:
            skipped += 1
            continue

        try:
            image_url = fetch_image_url(api_key, breed_id)
        except RuntimeError as exc:
            failed += 1
            print(f"[{index}/{len(rows)}] {row.get('name')} failed: {exc}")
            continue

        if image_url:
            row["image_url"] = image_url
            filled += 1

        safe_print(f"[{index}/{len(rows)}] {row.get('name')}: {image_url or 'no image'}")
        if index % 25 == 0:
            save_csv(rows, fieldnames)
            safe_print(f"Progress saved at {index}/{len(rows)}")
        time.sleep(0.05)

    save_csv(rows, fieldnames)
    safe_print(f"Done. filled={filled}, skipped={skipped}, failed={failed}, csv={BREEDS_CSV}")


if __name__ == "__main__":
    main()
