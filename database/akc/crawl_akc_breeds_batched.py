"""
Collect AKC breed rows in alphabetical batches.

Default run collects the first 50 breeds alphabetically and merges them into:
  - affenpinscher_sample.csv
  - affenpinscher_sample.xlsx
  - affenpinscher_sample_table.html

Example:
  python database/akc/crawl_akc_breeds_batched.py --batch-size 50 --batch-index 0
  python database/akc/crawl_akc_breeds_batched.py --batch-size 50 --batch-index 1

This uses the same breedPage data-js-props JSON parser as build_akc_sample_dataset.py.
It is intentionally batched and delayed to keep requests modest.
"""

from __future__ import annotations

import argparse
import csv
import logging
import sys
import time
from pathlib import Path

from build_akc_sample_dataset import (
    FIELDNAMES,
    LOG_FILE,
    SAMPLE_CSV,
    SAMPLE_HTML,
    SAMPLE_XLSX,
    apply_breed_page_props,
    blank_row,
    get_breedlist,
    write_html,
    write_xlsx,
)


BASE_DIR = Path(__file__).resolve().parent
BATCH_LOG_FILE = BASE_DIR / "akc_full_crawl.log"


def configure_logging() -> None:
    logging.basicConfig(
        filename=BATCH_LOG_FILE,
        filemode="a",
        encoding="utf-8",
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
    )


def read_existing_rows() -> list[dict[str, str]]:
    if not SAMPLE_CSV.exists():
        return []
    with SAMPLE_CSV.open(encoding="utf-8-sig", newline="") as f:
        return [{name: row.get(name, "") for name in FIELDNAMES} for row in csv.DictReader(f)]


def write_csv(rows: list[dict[str, str]]) -> None:
    with SAMPLE_CSV.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
        writer.writeheader()
        writer.writerows(rows)


def normalize_item_name(item: dict) -> str:
    return item.get("breed_name_display") or item.get("breed_name", "").replace("-", " ").title()


def sorted_breed_items() -> list[dict]:
    return sorted(get_breedlist(), key=lambda item: normalize_item_name(item).casefold())


def merge_sorted(rows_by_name: dict[str, dict[str, str]]) -> list[dict[str, str]]:
    return [normalize_missing(rows_by_name[name]) for name in sorted(rows_by_name, key=str.casefold)]


def normalize_missing(row: dict[str, str]) -> dict[str, str]:
    for field in FIELDNAMES:
        if row.get(field):
            continue
        if field in {"source_file", "breed_name", "breed_url"}:
            continue
        if field in {"colors", "markings"}:
            row[field] = "None listed"
        else:
            row[field] = "Not specified"
    return row


def crawl_batch(batch_size: int, batch_index: int, delay: float) -> list[str]:
    items = sorted_breed_items()
    start = batch_index * batch_size
    end = min(start + batch_size, len(items))
    batch = items[start:end]

    if not batch:
        raise SystemExit(f"No breeds in batch {batch_index}; total breeds={len(items)}")

    rows_by_name = {row["breed_name"]: row for row in read_existing_rows() if row.get("breed_name")}
    logging.info(
        "Starting batch index=%s size=%s range=%s:%s total=%s",
        batch_index,
        batch_size,
        start,
        end,
        len(items),
    )

    processed = []
    for idx, item in enumerate(batch, 1):
        name = normalize_item_name(item)
        print(f"[{idx}/{len(batch)}] {name}")
        logging.info("Fetching %s", name)
        row = apply_breed_page_props(blank_row(), item, overwrite=True)
        rows_by_name[row.get("breed_name") or name] = row
        processed.append(row.get("breed_name") or name)
        if delay > 0 and idx < len(batch):
            time.sleep(delay)

    rows = merge_sorted(rows_by_name)
    write_csv(rows)
    write_html(rows)
    write_xlsx(rows)

    logging.info("Completed batch index=%s; merged rows=%s", batch_index, len(rows))
    print(f"Wrote {len(rows)} merged rows")
    print(SAMPLE_CSV)
    print(SAMPLE_XLSX)
    print(SAMPLE_HTML)
    print(BATCH_LOG_FILE)
    return processed


def normalize_outputs_only() -> None:
    rows_by_name = {row["breed_name"]: row for row in read_existing_rows() if row.get("breed_name")}
    rows = merge_sorted(rows_by_name)
    write_csv(rows)
    write_html(rows)
    write_xlsx(rows)
    logging.info("Normalized existing outputs only; rows=%s", len(rows))
    print(f"Normalized {len(rows)} rows")
    print(SAMPLE_CSV)
    print(SAMPLE_XLSX)
    print(SAMPLE_HTML)


def main() -> None:
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except AttributeError:
        pass

    parser = argparse.ArgumentParser(description="Crawl AKC breed data in alphabetical batches.")
    parser.add_argument("--batch-size", type=int, default=50)
    parser.add_argument("--batch-index", type=int, default=0)
    parser.add_argument("--delay", type=float, default=1.0, help="Seconds between breed page requests.")
    parser.add_argument("--normalize-only", action="store_true", help="Fill blank cells and regenerate outputs without network requests.")
    args = parser.parse_args()

    configure_logging()
    if args.normalize_only:
        normalize_outputs_only()
        return

    processed = crawl_batch(args.batch_size, args.batch_index, args.delay)
    logging.info("Processed breeds: %s", ", ".join(processed))


if __name__ == "__main__":
    main()
