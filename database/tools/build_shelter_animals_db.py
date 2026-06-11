"""Load animal protection public API data into PostgreSQL.

This loader collects dog rescue/protection records from the data.go.kr
animal protection API and upserts them into the shelter_animals table.

Default scope:
- upkind=417000, dogs only
- all sido/sigungu regions
- all API states, unless --state is provided
"""

from __future__ import annotations

import argparse
import json
import math
import os
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any

try:
    import psycopg
except ImportError as exc:  # pragma: no cover - runtime environment guard
    raise SystemExit(
        "psycopg is required. Install project dependencies first: "
        "pip install -r requirements.txt"
    ) from exc


PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.integrations.animal_protection.client import (  # noqa: E402
    AnimalProtectionClient,
    DOG_UP_KIND_CODE,
    extract_items,
)


CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS shelter_animals (
    id BIGSERIAL PRIMARY KEY,
    desertion_no VARCHAR(50) UNIQUE NOT NULL,
    notice_no VARCHAR(100),
    happen_dt DATE,
    happen_place TEXT,
    up_kind_cd VARCHAR(20),
    up_kind_nm VARCHAR(50),
    kind_cd VARCHAR(20),
    kind_nm VARCHAR(150),
    kind_full_nm VARCHAR(200),
    color_cd VARCHAR(100),
    age VARCHAR(100),
    weight VARCHAR(100),
    sex_cd VARCHAR(10),
    neuter_yn VARCHAR(10),
    special_mark TEXT,
    care_reg_no VARCHAR(50),
    care_nm VARCHAR(200),
    care_tel VARCHAR(100),
    care_addr TEXT,
    care_owner_nm VARCHAR(200),
    org_nm VARCHAR(200),
    notice_sdt DATE,
    notice_edt DATE,
    process_state VARCHAR(100),
    popfile1 TEXT,
    popfile2 TEXT,
    api_updated_at TIMESTAMPTZ,
    raw_data JSONB NOT NULL,
    fetched_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_shelter_animals_kind_cd
    ON shelter_animals (kind_cd);

CREATE INDEX IF NOT EXISTS idx_shelter_animals_kind_nm
    ON shelter_animals (kind_nm);

CREATE INDEX IF NOT EXISTS idx_shelter_animals_process_state
    ON shelter_animals (process_state);

CREATE INDEX IF NOT EXISTS idx_shelter_animals_notice_sdt
    ON shelter_animals (notice_sdt);

CREATE INDEX IF NOT EXISTS idx_shelter_animals_org_nm
    ON shelter_animals (org_nm);

CREATE INDEX IF NOT EXISTS idx_shelter_animals_care_reg_no
    ON shelter_animals (care_reg_no);
"""


UPSERT_SQL = """
INSERT INTO shelter_animals (
    desertion_no,
    notice_no,
    happen_dt,
    happen_place,
    up_kind_cd,
    up_kind_nm,
    kind_cd,
    kind_nm,
    kind_full_nm,
    color_cd,
    age,
    weight,
    sex_cd,
    neuter_yn,
    special_mark,
    care_reg_no,
    care_nm,
    care_tel,
    care_addr,
    care_owner_nm,
    org_nm,
    notice_sdt,
    notice_edt,
    process_state,
    popfile1,
    popfile2,
    api_updated_at,
    raw_data
) VALUES (
    %(desertion_no)s,
    %(notice_no)s,
    %(happen_dt)s,
    %(happen_place)s,
    %(up_kind_cd)s,
    %(up_kind_nm)s,
    %(kind_cd)s,
    %(kind_nm)s,
    %(kind_full_nm)s,
    %(color_cd)s,
    %(age)s,
    %(weight)s,
    %(sex_cd)s,
    %(neuter_yn)s,
    %(special_mark)s,
    %(care_reg_no)s,
    %(care_nm)s,
    %(care_tel)s,
    %(care_addr)s,
    %(care_owner_nm)s,
    %(org_nm)s,
    %(notice_sdt)s,
    %(notice_edt)s,
    %(process_state)s,
    %(popfile1)s,
    %(popfile2)s,
    %(api_updated_at)s,
    %(raw_data)s::jsonb
)
ON CONFLICT (desertion_no)
DO UPDATE SET
    notice_no = EXCLUDED.notice_no,
    happen_dt = EXCLUDED.happen_dt,
    happen_place = EXCLUDED.happen_place,
    up_kind_cd = EXCLUDED.up_kind_cd,
    up_kind_nm = EXCLUDED.up_kind_nm,
    kind_cd = EXCLUDED.kind_cd,
    kind_nm = EXCLUDED.kind_nm,
    kind_full_nm = EXCLUDED.kind_full_nm,
    color_cd = EXCLUDED.color_cd,
    age = EXCLUDED.age,
    weight = EXCLUDED.weight,
    sex_cd = EXCLUDED.sex_cd,
    neuter_yn = EXCLUDED.neuter_yn,
    special_mark = EXCLUDED.special_mark,
    care_reg_no = EXCLUDED.care_reg_no,
    care_nm = EXCLUDED.care_nm,
    care_tel = EXCLUDED.care_tel,
    care_addr = EXCLUDED.care_addr,
    care_owner_nm = EXCLUDED.care_owner_nm,
    org_nm = EXCLUDED.org_nm,
    notice_sdt = EXCLUDED.notice_sdt,
    notice_edt = EXCLUDED.notice_edt,
    process_state = EXCLUDED.process_state,
    popfile1 = EXCLUDED.popfile1,
    popfile2 = EXCLUDED.popfile2,
    api_updated_at = EXCLUDED.api_updated_at,
    raw_data = EXCLUDED.raw_data,
    fetched_at = NOW(),
    updated_at = NOW();
"""


def load_env() -> None:
    env_path = PROJECT_ROOT / ".env"
    if not env_path.exists():
        return

    for line in env_path.read_text(encoding="utf-8-sig").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, value = stripped.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def db_config() -> dict[str, Any]:
    return {
        "host": os.getenv("POSTGRES_HOST", "localhost"),
        "port": int(os.getenv("POSTGRES_PORT", "5432")),
        "dbname": os.getenv("POSTGRES_DB", "pet_dog"),
        "user": os.getenv("POSTGRES_USER", "admin"),
        "password": os.getenv("POSTGRES_PASSWORD", "admin1234"),
    }


def clean_str(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def parse_date(value: Any) -> str | None:
    text = clean_str(value)
    if not text:
        return None
    digits = "".join(ch for ch in text if ch.isdigit())
    if len(digits) != 8:
        return None
    return f"{digits[:4]}-{digits[4:6]}-{digits[6:8]}"


def parse_timestamp(value: Any) -> str | None:
    text = clean_str(value)
    if not text:
        return None

    for fmt in ("%Y-%m-%d %H:%M:%S.%f", "%Y-%m-%d %H:%M:%S"):
        try:
            return datetime.strptime(text, fmt).isoformat(sep=" ")
        except ValueError:
            continue
    return None


def response_total_count(response: dict[str, Any]) -> int:
    body = response.get("response", {}).get("body", {})
    try:
        return int(body.get("totalCount") or 0)
    except (TypeError, ValueError):
        return 0


def normalize_row(item: dict[str, Any]) -> dict[str, Any] | None:
    desertion_no = clean_str(item.get("desertionNo"))
    if not desertion_no:
        return None

    return {
        "desertion_no": desertion_no,
        "notice_no": clean_str(item.get("noticeNo")),
        "happen_dt": parse_date(item.get("happenDt")),
        "happen_place": clean_str(item.get("happenPlace")),
        "up_kind_cd": clean_str(item.get("upKindCd")),
        "up_kind_nm": clean_str(item.get("upKindNm")),
        "kind_cd": clean_str(item.get("kindCd")),
        "kind_nm": clean_str(item.get("kindNm")),
        "kind_full_nm": clean_str(item.get("kindFullNm")),
        "color_cd": clean_str(item.get("colorCd")),
        "age": clean_str(item.get("age")),
        "weight": clean_str(item.get("weight")),
        "sex_cd": clean_str(item.get("sexCd")),
        "neuter_yn": clean_str(item.get("neuterYn")),
        "special_mark": clean_str(item.get("specialMark")),
        "care_reg_no": clean_str(item.get("careRegNo")),
        "care_nm": clean_str(item.get("careNm")),
        "care_tel": clean_str(item.get("careTel")),
        "care_addr": clean_str(item.get("careAddr")),
        "care_owner_nm": clean_str(item.get("careOwnerNm")),
        "org_nm": clean_str(item.get("orgNm")),
        "notice_sdt": parse_date(item.get("noticeSdt")),
        "notice_edt": parse_date(item.get("noticeEdt")),
        "process_state": clean_str(item.get("processState")),
        "popfile1": clean_str(item.get("popfile1") or item.get("popfile") or item.get("filename")),
        "popfile2": clean_str(item.get("popfile2")),
        "api_updated_at": parse_timestamp(item.get("updTm")),
        "raw_data": json.dumps(item, ensure_ascii=False),
    }


def setup_database(conn: psycopg.Connection, reset: bool) -> None:
    with conn.cursor() as cur:
        cur.execute(CREATE_TABLE_SQL)
        if reset:
            cur.execute("TRUNCATE TABLE shelter_animals RESTART IDENTITY;")
    conn.commit()


def upsert_rows(conn: psycopg.Connection, rows: list[dict[str, Any]]) -> int:
    if not rows:
        return 0
    with conn.cursor() as cur:
        cur.executemany(UPSERT_SQL, rows)
    conn.commit()
    return len(rows)


def get_region_codes(client: AnimalProtectionClient, sido_code: str | None = None) -> list[dict[str, str]]:
    sido_items = extract_items(client.get_sido(num_of_rows=100))
    regions: list[dict[str, str]] = []

    for sido in sido_items:
        upr_cd = clean_str(sido.get("orgCd"))
        sido_name = clean_str(sido.get("orgdownNm")) or ""
        if not upr_cd:
            continue
        if sido_code and upr_cd != sido_code:
            continue

        sigungu_items = extract_items(client.get_sigungu(upr_cd, num_of_rows=300))
        if not sigungu_items:
            regions.append({"upr_cd": upr_cd, "org_cd": "", "sido_name": sido_name, "sigungu_name": ""})
            continue

        for sigungu in sigungu_items:
            org_cd = clean_str(sigungu.get("orgCd")) or ""
            sigungu_name = clean_str(sigungu.get("orgdownNm")) or ""
            regions.append(
                {
                    "upr_cd": upr_cd,
                    "org_cd": org_cd,
                    "sido_name": sido_name,
                    "sigungu_name": sigungu_name,
                }
            )

    return regions


def fetch_region_pages(
    client: AnimalProtectionClient,
    *,
    upr_cd: str,
    org_cd: str,
    num_rows: int,
    state: str | None,
    bgnde: str | None,
    endde: str | None,
    sleep_seconds: float,
) -> tuple[int, int]:
    first_response = client.get_abandonments(
        upkind=DOG_UP_KIND_CODE,
        upr_cd=upr_cd,
        org_cd=org_cd,
        state=state,
        bgnde=bgnde,
        endde=endde,
        pageNo=1,
        numOfRows=num_rows,
    )
    total_count = response_total_count(first_response)
    page_count = max(1, math.ceil(total_count / num_rows)) if total_count else 1

    yield_items = extract_items(first_response)
    yield len(yield_items), total_count, yield_items

    for page_no in range(2, page_count + 1):
        if sleep_seconds:
            time.sleep(sleep_seconds)
        response = client.get_abandonments(
            upkind=DOG_UP_KIND_CODE,
            upr_cd=upr_cd,
            org_cd=org_cd,
            state=state,
            bgnde=bgnde,
            endde=endde,
            pageNo=page_no,
            numOfRows=num_rows,
        )
        items = extract_items(response)
        yield len(items), total_count, items


def load_shelter_animals(args: argparse.Namespace) -> dict[str, Any]:
    load_env()
    client = AnimalProtectionClient(timeout=args.timeout)

    total_seen = 0
    total_upserted = 0
    failed_regions: list[dict[str, str]] = []

    with psycopg.connect(**db_config()) as conn:
        setup_database(conn, reset=args.reset)
        regions = get_region_codes(client, sido_code=args.sido_cd)
        print(f"regions: {len(regions)}")

        for index, region in enumerate(regions, start=1):
            label = f"{region['sido_name']} {region['sigungu_name']}".strip()
            print(f"[{index}/{len(regions)}] {label} ({region['upr_cd']}/{region['org_cd']})")

            try:
                region_upserted = 0
                for page_item_count, region_total_count, items in fetch_region_pages(
                    client,
                    upr_cd=region["upr_cd"],
                    org_cd=region["org_cd"],
                    num_rows=args.num_rows,
                    state=args.state,
                    bgnde=args.bgnde,
                    endde=args.endde,
                    sleep_seconds=args.sleep,
                ):
                    total_seen += page_item_count
                    rows = [row for item in items if (row := normalize_row(item)) is not None]
                    region_upserted += upsert_rows(conn, rows)
                    total_upserted += len(rows)
                    print(
                        f"  total={region_total_count}, page_items={page_item_count}, "
                        f"region_upserted={region_upserted}"
                    )

            except Exception as exc:  # noqa: BLE001 - keep regional load resilient
                failed_regions.append(
                    {
                        "upr_cd": region["upr_cd"],
                        "org_cd": region["org_cd"],
                        "label": label,
                        "error": str(exc),
                    }
                )
                print(f"  failed: {exc}", file=sys.stderr)

            if args.sleep:
                time.sleep(args.sleep)

        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM shelter_animals;")
            table_count = cur.fetchone()[0]

    return {
        "seen_items": total_seen,
        "upserted_rows": total_upserted,
        "table_count": table_count,
        "failed_regions": failed_regions,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Load animal protection dog records into PostgreSQL.")
    parser.add_argument("--reset", action="store_true", help="TRUNCATE shelter_animals before loading.")
    parser.add_argument("--sido-cd", default=None, help="Optional sido code. Omit to load all regions.")
    parser.add_argument("--state", default=None, help="Optional API state filter, e.g. protect.")
    parser.add_argument("--bgnde", default=None, help="Optional begin date, YYYYMMDD.")
    parser.add_argument("--endde", default=None, help="Optional end date, YYYYMMDD.")
    parser.add_argument("--num-rows", type=int, default=100, help="API numOfRows per page.")
    parser.add_argument("--sleep", type=float, default=0.05, help="Sleep seconds between API calls.")
    parser.add_argument("--timeout", type=int, default=30, help="HTTP timeout seconds.")
    return parser.parse_args()


def main() -> None:
    try:
        result = load_shelter_animals(parse_args())
    except Exception as exc:  # noqa: BLE001 - command line error reporting
        print(f"Error: {exc}", file=sys.stderr)
        sys.exit(1)

    print(json.dumps(result, ensure_ascii=False, indent=2))
    if result["failed_regions"]:
        sys.exit(2)


if __name__ == "__main__":
    main()
