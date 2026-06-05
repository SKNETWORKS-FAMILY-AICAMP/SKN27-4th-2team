import csv
import re
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[2]
DOGAPI_CSV = ROOT_DIR / "database" / "contents" / "dog_api" / "breeds.csv"
AKC_CSV = ROOT_DIR / "database" / "akc" / "preprocessed" / "akc_breed_info_step5_completed.csv"
OUTPUT_CSV = ROOT_DIR / "database" / "contents" / "dog_api" / "dogapi_akc_matched_breeds.csv"


def normalize_breed_name(name):
    name = (name or "").lower().replace("&", " and ")
    name = re.sub(r"[^a-z0-9]+", " ", name)
    return re.sub(r"\s+", " ", name).strip()


def read_csv(path):
    with path.open(encoding="utf-8-sig", newline="") as csv_file:
        reader = csv.DictReader(csv_file)
        return list(reader), list(reader.fieldnames or [])


def prefix_row(row, prefix, excluded_fields=None):
    excluded_fields = set(excluded_fields or [])
    return {f"{prefix}_{key}": value for key, value in row.items() if key not in excluded_fields}


def prefixed_fields(fields, prefix, excluded_fields=None):
    excluded_fields = set(excluded_fields or [])
    return [f"{prefix}_{field}" for field in fields if field not in excluded_fields]


def main():
    dogapi_rows, dogapi_fields = read_csv(DOGAPI_CSV)
    akc_rows, akc_fields = read_csv(AKC_CSV)

    akc_by_normalized_name = {
        normalize_breed_name(row["breed_name"]): row
        for row in akc_rows
        if normalize_breed_name(row.get("breed_name"))
    }

    output_rows = []
    seen_normalized_names = set()
    for dogapi_row in dogapi_rows:
        normalized_name = normalize_breed_name(dogapi_row.get("name"))
        if normalized_name in seen_normalized_names:
            continue

        akc_row = akc_by_normalized_name.get(normalized_name)
        if not akc_row:
            continue

        seen_normalized_names.add(normalized_name)
        output_rows.append(
            {
                "matched_breed_name": akc_row["breed_name"],
                **prefix_row(
                    dogapi_row,
                    "dogapi",
                    excluded_fields={"name", "bred_for", "reference_image_id"},
                ),
                **prefix_row(akc_row, "akc", excluded_fields={"breed_name"}),
            }
        )

    fieldnames = (
        ["matched_breed_name"]
        + prefixed_fields(
            dogapi_fields,
            "dogapi",
            excluded_fields={"name", "bred_for", "reference_image_id"},
        )
        + prefixed_fields(akc_fields, "akc", excluded_fields={"breed_name"})
    )

    OUTPUT_CSV.parent.mkdir(parents=True, exist_ok=True)
    with OUTPUT_CSV.open("w", encoding="utf-8-sig", newline="") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(output_rows)

    print(f"matched_rows={len(output_rows)}")
    print(f"columns={len(fieldnames)}")
    print(f"output={OUTPUT_CSV}")


if __name__ == "__main__":
    main()
