from __future__ import annotations

import argparse
import json
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urljoin, urlparse, urlunparse
from urllib.request import Request, urlopen

from bs4 import BeautifulSoup

BASE_URL = "https://www.merckvetmanual.com"
DOG_OWNERS_URL = "https://www.merckvetmanual.com/dog-owners"
DEFAULT_OUTPUT = Path("database/merck_vet/urls/dog_owner_urls.json")
USER_AGENT = "PetMateResearchBot/0.1 (+educational RAG dataset; respects robots.txt)"


def fetch_html(url: str, timeout: int = 30) -> str:
    request = Request(url, headers={"User-Agent": USER_AGENT})
    with urlopen(request, timeout=timeout) as response:
        charset = response.headers.get_content_charset() or "utf-8"
        return response.read().decode(charset, errors="replace")


def normalize_url(href: str) -> str:
    absolute = urljoin(BASE_URL, href)
    parsed = urlparse(absolute)
    return urlunparse((parsed.scheme, parsed.netloc, parsed.path.rstrip("/"), "", "", ""))


def dog_owner_path_parts(url: str) -> list[str]:
    path = urlparse(url).path.strip("/")
    parts = path.split("/") if path else []
    if len(parts) >= 1 and parts[0] == "dog-owners":
        return parts
    return []


def collect_urls(html: str) -> list[dict[str, str]]:
    soup = BeautifulSoup(html, "html.parser")
    links: list[tuple[str, str]] = []
    seen: set[str] = set()

    for anchor in soup.find_all("a", href=True):
        title = anchor.get_text(" ", strip=True)
        if not title or title.lower().startswith("image:"):
            continue

        url = normalize_url(anchor["href"])
        parts = dog_owner_path_parts(url)
        if len(parts) < 2:
            continue
        if url in seen:
            continue

        seen.add(url)
        links.append((url, title))

    category_by_prefix: dict[str, str] = {}
    for url, title in links:
        parts = dog_owner_path_parts(url)
        if len(parts) == 2:
            category_by_prefix[parts[1]] = title

    records: list[dict[str, str]] = []
    for url, title in links:
        parts = dog_owner_path_parts(url)
        section_slug = parts[1] if len(parts) >= 2 else "dog-owners"
        category = category_by_prefix.get(section_slug, "Dog Owners")
        depth = "section" if len(parts) == 2 else "topic"
        records.append(
            {
                "title": title,
                "url": url,
                "category": category,
                "section_slug": section_slug,
                "depth": depth,
            }
        )

    records.sort(key=lambda item: (item["section_slug"], item["depth"], item["title"]))
    return records


def main() -> None:
    parser = argparse.ArgumentParser(description="Collect Merck Veterinary Manual dog-owner URLs.")
    parser.add_argument("--url", default=DOG_OWNERS_URL)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--delay", type=float, default=5.0, help="robots.txt crawl delay. Keep 5+ seconds for repeated runs.")
    args = parser.parse_args()

    html = fetch_html(args.url)
    if args.delay > 0:
        time.sleep(args.delay)

    records = collect_urls(html)
    payload = {
        "source": "merck_vet_manual",
        "scope": "dog-owners",
        "source_url": args.url,
        "crawled_at": datetime.now(timezone.utc).isoformat(),
        "robots_note": "robots.txt declares Crawl-delay: 5. Keep requests at least 5 seconds apart.",
        "count": len(records),
        "items": records,
    }

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"saved: {args.out}")
    print(f"url count: {len(records)}")


if __name__ == "__main__":
    main()