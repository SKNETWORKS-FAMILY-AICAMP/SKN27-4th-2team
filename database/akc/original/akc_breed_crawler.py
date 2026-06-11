"""
AKC Dog Breed Crawler
담당: 박준희
수집 항목:
  - breed name, height, weight, life expectancy
  - Breed Traits & Characteristics (all traits, 1~5 star rating)
  - About breed
  - Health, Grooming, Exercise, Training, Nutrition
산출물: akc_breeds.csv
CSV 컬럼 구조: 
    - breed_name, breed_url, height, weight, life_expectancy, traits, about, health, grooming, exercise, training, nutrition

"""

import time
import csv
import re
import logging
from dataclasses import dataclass, asdict
from typing import Optional

import requests
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler("akc_crawler.log", encoding="utf-8"),
        logging.StreamHandler(),
    ],
)
log = logging.getLogger(__name__)

BASE_URL = "https://www.akc.org"
BREEDS_URL = f"{BASE_URL}/dog-breeds/"
BREED_SITEMAP_URL = f"{BASE_URL}/breed-sitemap.xml"
OUTPUT_FILE = "akc_breeds.csv"
REQUEST_DELAY = 2  # seconds between page loads


# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------

@dataclass
class BreedRecord:
    breed_name: str = ""
    breed_url: str = ""
    height: str = ""
    weight: str = ""
    life_expectancy: str = ""
    traits: str = ""       # "TraitName:Score; TraitName:Score; ..."
    about: str = ""
    health: str = ""
    grooming: str = ""
    exercise: str = ""
    training: str = ""
    nutrition: str = ""


FIELDNAMES = list(BreedRecord.__dataclass_fields__.keys())


# ---------------------------------------------------------------------------
# Driver setup
# ---------------------------------------------------------------------------

def build_driver() -> webdriver.Chrome:
    options = Options()
    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--window-size=1920,1080")
    options.add_argument(
        "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
    )
    service = Service(ChromeDriverManager().install())
    return webdriver.Chrome(service=service, options=options)


# ---------------------------------------------------------------------------
# Breed list collection
# ---------------------------------------------------------------------------

def get_breed_urls() -> list[tuple[str, str]]:
    """사이트맵에서 전체 품종 URL 수집 (정적 요청, 빠름)."""
    log.info("Fetching breed list from sitemap: %s", BREED_SITEMAP_URL)
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
    r = requests.get(BREED_SITEMAP_URL, headers=headers, timeout=15)
    r.raise_for_status()

    soup = BeautifulSoup(r.text, "xml")
    breed_pattern = re.compile(r"https://www\.akc\.org/dog-breeds/([^/]+)/$")

    breeds: list[tuple[str, str]] = []
    for loc in soup.find_all("loc"):
        url = loc.text.strip()
        m = breed_pattern.match(url)
        if not m:
            continue
        slug = m.group(1)
        # slug → 사람이 읽을 수 있는 이름 (hyphens → spaces, title case)
        name = slug.replace("-", " ").title()
        breeds.append((name, url))

    log.info("Total breeds found: %d", len(breeds))
    return breeds


# ---------------------------------------------------------------------------
# Per-breed scraping
# ---------------------------------------------------------------------------

def scrape_basic_info(soup: BeautifulSoup, record: BreedRecord) -> None:
    """Height, Weight, Life Expectancy from hero overview section."""
    for block in soup.select(".breed-page__hero__overview__title"):
        label = block.get_text(strip=True)
        value_el = block.find_next_sibling("p")
        if not value_el:
            continue
        value = value_el.get_text(strip=True)
        if label == "Height":
            record.height = value
        elif label == "Weight":
            record.weight = value
        elif label == "Life Expectancy":
            record.life_expectancy = value


def scrape_traits(soup: BeautifulSoup, record: BreedRecord) -> None:
    """All traits with star ratings (1~5) from Breed Traits & Characteristics."""
    pairs: list[str] = []
    seen_names: set[str] = set()

    for trait_el in soup.select(".breed-trait-group__trait"):
        name_el = trait_el.select_one(".accordion__header__text")
        if not name_el:
            continue
        trait_name = name_el.get_text(strip=True)
        if not trait_name or trait_name in seen_names:
            continue
        seen_names.add(trait_name)

        filled = len(trait_el.select(".breed-trait-score__score-unit--filled"))
        total = len(trait_el.select(".breed-trait-score__score-unit"))
        rating = f"{filled}/{total}" if total else str(filled)
        pairs.append(f"{trait_name}:{rating}")

    record.traits = "; ".join(pairs)


def scrape_about(soup: BeautifulSoup, record: BreedRecord) -> None:
    """'About the Breed' section text."""
    for h2 in soup.find_all("h2"):
        if "about" in h2.get_text(strip=True).lower():
            parts: list[str] = []
            for sib in h2.next_siblings:
                if not hasattr(sib, "get_text"):
                    continue
                if sib.name == "h2":
                    break
                text = sib.get_text(" ", strip=True)
                if text:
                    parts.append(text)
            record.about = " ".join(parts)
            return


def scrape_care_sections(soup: BeautifulSoup, record: BreedRecord) -> None:
    """Health, Grooming, Exercise, Training, Nutrition 섹션 텍스트 수집.
    각 섹션은 .breed-table__wrap 내부의 .breed-table__accordion 에 있음.
    """
    care_attrs = {"health", "grooming", "exercise", "training", "nutrition"}

    for wrap in soup.select(".breed-table__wrap"):
        header_el = wrap.select_one("h3.breed-table__header")
        if not header_el:
            continue
        label = header_el.get_text(strip=True).lower()
        if label not in care_attrs:
            continue

        accordion = wrap.select_one(".breed-table__accordion")
        if accordion:
            setattr(record, label, accordion.get_text(" ", strip=True))


def scrape_breed_page(driver: webdriver.Chrome, name: str, url: str) -> BreedRecord:
    record = BreedRecord(breed_name=name, breed_url=url)
    log.info("Scraping: %s", name)

    try:
        driver.get(url)
        time.sleep(REQUEST_DELAY + 4)  # React 렌더링 충분히 대기

        soup = BeautifulSoup(driver.page_source, "html.parser")
        scrape_basic_info(soup, record)
        scrape_traits(soup, record)
        scrape_about(soup, record)
        scrape_care_sections(soup, record)

    except Exception as exc:
        log.error("Failed [%s]: %s", name, exc)

    return record


# ---------------------------------------------------------------------------
# CSV helpers
# ---------------------------------------------------------------------------

def save_csv(records: list[BreedRecord], path: str = OUTPUT_FILE) -> None:
    with open(path, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
        writer.writeheader()
        for r in records:
            writer.writerow(asdict(r))
    log.info("Saved %d records → %s", len(records), path)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main(limit: Optional[int] = None, start_from: int = 0) -> None:
    driver = build_driver()
    records: list[BreedRecord] = []

    try:
        breeds = get_breed_urls()
        breeds = breeds[start_from:]
        if limit is not None:
            breeds = breeds[:limit]

        for idx, (name, url) in enumerate(breeds, 1):
            record = scrape_breed_page(driver, name, url)
            records.append(record)

            if idx % 10 == 0:
                save_csv(records)
                log.info("Checkpoint: %d breeds saved", idx)

    finally:
        driver.quit()
        save_csv(records)
        log.info("Complete. Total: %d breeds", len(records))


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="AKC Breed Crawler (박준희)")
    parser.add_argument("--limit", type=int, default=None, help="최대 크롤링 품종 수")
    parser.add_argument("--start", type=int, default=0, help="N번째 품종부터 시작 (재시작용)")
    parser.add_argument("--test", action="store_true", help="테스트: 3개 품종만 수집")
    args = parser.parse_args()

    if args.test:
        main(limit=3)
    else:
        main(limit=args.limit, start_from=args.start)
