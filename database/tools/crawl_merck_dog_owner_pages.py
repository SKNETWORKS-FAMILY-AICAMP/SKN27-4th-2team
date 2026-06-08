from __future__ import annotations

import argparse
import json
import re
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse
from urllib.request import Request, urlopen

from bs4 import BeautifulSoup

DEFAULT_URLS = Path("database/merck_vet/urls/dog_owner_urls.json")
DEFAULT_OUT_DIR = Path("database/merck_vet/raw")
USER_AGENT = "PetMateResearchBot/0.1 (+educational RAG dataset; respects robots.txt)"
STOP_PATTERNS = (
    "Test your Knowledge now",
    "Take a Quiz!",
    "© 2025 Merck",
    "© 2026 Merck",
    "Cookie Preferences",
    "Your Privacy Choices",
)


def slugify(value: str) -> str:
    value = value.lower()
    value = re.sub(r"[^a-z0-9가-힣]+", "-", value)
    return value.strip("-") or "page"


def fetch_html(url: str, timeout: int = 30) -> str:
    request = Request(url, headers={"User-Agent": USER_AGENT})
    with urlopen(request, timeout=timeout) as response:
        charset = response.headers.get_content_charset() or "utf-8"
        return response.read().decode(charset, errors="replace")


def clean_text(value: str) -> str:
    value = value.replace("\xa0", " ")
    value = re.sub(r"\s+", " ", value)
    return value.strip()


def find_reviewed_date(text: str) -> str:
    match = re.search(r"Reviewed/Revised\s+Modified\s+([A-Za-z]{3}\s+\d{4})", text)
    if match:
        return match.group(1)
    match = re.search(r"Reviewed/Revised\s+([A-Za-z]{3}\s+\d{4})", text)
    return match.group(1) if match else ""


def extract_author(text: str) -> str:
    match = re.search(r"\bBy\s+(.+?)\s+Reviewed/Revised", text)
    if match:
        return clean_text(match.group(1))
    return ""


def should_stop(text: str) -> bool:
    return any(pattern in text for pattern in STOP_PATTERNS)


def extract_page(html: str, source_record: dict[str, str]) -> dict[str, object]:
    soup = BeautifulSoup(html, "html.parser")

    for tag in soup(["script", "style", "noscript", "svg", "form", "header", "footer"]):
        tag.decompose()

    h1 = soup.find("h1")
    title = clean_text(h1.get_text(" ", strip=True)) if h1 else source_record.get("title", "")
    all_text = clean_text(soup.get_text(" ", strip=True))
    reviewed_date = find_reviewed_date(all_text)
    author = extract_author(all_text)

    sections: list[dict[str, object]] = []
    current_heading = "Overview"
    current_paragraphs: list[str] = []

    if h1:
        iterator = h1.find_all_next(["h2", "h3", "p", "li"])
    else:
        iterator = soup.find_all(["h2", "h3", "p", "li"])

    def flush() -> None:
        nonlocal current_paragraphs
        if current_paragraphs:
            sections.append({"heading": current_heading, "paragraphs": current_paragraphs})
            current_paragraphs = []

    for tag in iterator:
        text = clean_text(tag.get_text(" ", strip=True))
        if not text:
            continue
        if should_stop(text):
            break
        if tag.name in {"h2", "h3"}:
            flush()
            current_heading = text
            continue
        if len(text) < 3:
            continue
        current_paragraphs.append(text)

    flush()
    content = "\n\n".join(
        f"## {section['heading']}\n" + "\n".join(section["paragraphs"])
        for section in sections
    ).strip()

    return {
        "source": "merck_vet_manual",
        "scope": "dog-owners",
        "title": title,
        "url": source_record["url"],
        "category": source_record.get("category", "Dog Owners"),
        "section_slug": source_record.get("section_slug", ""),
        "reviewed_date": reviewed_date,
        "author": author,
        "language": "en",
        "content": content,
        "sections": sections,
        "crawled_at": datetime.now(timezone.utc).isoformat(),
        "usage_note": "Use for retrieval-grounded summaries with source attribution; do not republish full article text in the UI.",
    }


def load_url_records(path: Path, include_sections: bool) -> list[dict[str, str]]:
    payload = json.loads(path.read_text(encoding="utf-8-sig"))
    records = payload.get("items", [])
    if not include_sections:
        records = [record for record in records if record.get("depth") != "section"]
    return records


def output_path_for(record: dict[str, str], out_dir: Path) -> Path:
    parsed = urlparse(record["url"])
    slug = slugify(parsed.path.strip("/").split("/")[-1] or record.get("title", "page"))
    return out_dir / f"{slug}.json"


def main() -> None:
    parser = argparse.ArgumentParser(description="Crawl Merck dog-owner pages into raw JSON files.")
    parser.add_argument("--urls", type=Path, default=DEFAULT_URLS)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--delay", type=float, default=5.0, help="robots.txt crawl delay. Keep 5+ seconds.")
    parser.add_argument("--overwrite", action="store_true")
    parser.add_argument("--include-sections", action="store_true")
    args = parser.parse_args()

    records = load_url_records(args.urls, include_sections=args.include_sections)
    if args.limit is not None:
        records = records[: args.limit]

    args.out_dir.mkdir(parents=True, exist_ok=True)
    saved = 0
    skipped = 0

    for index, record in enumerate(records, start=1):
        out_path = output_path_for(record, args.out_dir)
        if out_path.exists() and not args.overwrite:
            skipped += 1
            print(f"skip existing: {out_path}")
            continue

        print(f"[{index}/{len(records)}] fetch: {record['url']}")
        html = fetch_html(record["url"])
        page = extract_page(html, record)
        out_path.write_text(json.dumps(page, ensure_ascii=False, indent=2), encoding="utf-8")
        saved += 1
        print(f"saved: {out_path} ({len(page.get('content', '')):,} chars)")

        if index < len(records) and args.delay > 0:
            time.sleep(args.delay)

    print({"saved": saved, "skipped": skipped, "total_requested": len(records)})


if __name__ == "__main__":
    main()