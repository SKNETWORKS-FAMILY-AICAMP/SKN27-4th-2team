"""
Parse locally saved AKC breed pages into a CSV.

This script does not request AKC pages. Put saved breed HTML files under
database/akc/html_pages, then run:

    python database/akc/parse_saved_breed_html.py

Output:
    database/akc/akc_breeds_from_html.csv
"""

from __future__ import annotations

import argparse
import csv
import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable

from lxml import html
from lxml.html import HtmlElement


BASE_DIR = Path(__file__).resolve().parent
DEFAULT_INPUT_DIR = BASE_DIR / "html_pages"
DEFAULT_OUTPUT_FILE = BASE_DIR / "akc_breeds_from_html.csv"


TRAIT_COLUMNS = {
    "Affectionate With Family": "affectionate_with_family",
    "Good With Young Children": "good_with_young_children",
    "Good With Other Dogs": "good_with_other_dogs",
    "Shedding Level": "shedding_level",
    "Coat Grooming Frequency": "coat_grooming_frequency",
    "Drooling Level": "drooling_level",
    "Coat Type": "coat_type",
    "Coat Length": "coat_length",
    "Openness To Strangers": "openness_to_strangers",
    "Playfulness Level": "playfulness_level",
    "Watchdog/Protective Nature": "watchdog_protective_nature",
    "Adaptability Level": "adaptability_level",
    "Trainability Level": "trainability_level",
    "Energy Level": "energy_level",
    "Barking Level": "barking_level",
    "Mental Stimulation Needs": "mental_stimulation_needs",
}


@dataclass
class BreedRecord:
    source_file: str = ""
    breed_name: str = ""
    breed_url: str = ""
    height: str = ""
    weight: str = ""
    life_expectancy: str = ""
    affectionate_with_family: str = ""
    good_with_young_children: str = ""
    good_with_other_dogs: str = ""
    shedding_level: str = ""
    coat_grooming_frequency: str = ""
    drooling_level: str = ""
    coat_type: str = ""
    coat_length: str = ""
    openness_to_strangers: str = ""
    playfulness_level: str = ""
    watchdog_protective_nature: str = ""
    adaptability_level: str = ""
    trainability_level: str = ""
    energy_level: str = ""
    barking_level: str = ""
    mental_stimulation_needs: str = ""
    colors: str = ""
    markings: str = ""
    about_the_breed: str = ""
    health: str = ""
    grooming: str = ""
    exercise: str = ""
    training: str = ""
    nutrition: str = ""
    history: str = ""


FIELDNAMES = list(BreedRecord.__dataclass_fields__.keys())


def clean_text(value: str) -> str:
    value = re.sub(r"\s+", " ", value or "")
    return value.strip()


def element_text(element: HtmlElement | None) -> str:
    if element is None:
        return ""
    return clean_text(element.text_content())


def has_class(class_name: str) -> str:
    return f"contains(concat(' ', normalize-space(@class), ' '), ' {class_name} ')"


def first(elements: list[HtmlElement]) -> HtmlElement | None:
    return elements[0] if elements else None


def selected_choices(container: HtmlElement) -> list[str]:
    choices = []
    query = f".//*[{has_class('breed-trait-score__choice--selected')}]"
    for choice in container.xpath(query):
        text = element_text(first(choice.xpath(".//span"))) or element_text(choice)
        if text:
            choices.append(text)
    return choices


def score_value(container: HtmlElement) -> str:
    choices = selected_choices(container)
    if choices:
        return " | ".join(choices)

    units = container.xpath(f".//*[{has_class('breed-trait-score__score-unit')}]")
    if not units:
        return ""

    filled = container.xpath(f".//*[{has_class('breed-trait-score__score-unit--filled')}]")
    return f"{len(filled)}/{len(units)}"


def parse_name_and_url(doc: HtmlElement, record: BreedRecord) -> None:
    name_el = first(doc.xpath(f".//*[{has_class('page-header__title')}]"))
    if name_el is None:
        name_el = first(doc.xpath(".//h1"))
    record.breed_name = element_text(name_el)

    canonical = first(doc.xpath(".//link[@rel='canonical']"))
    og_url = first(doc.xpath(".//meta[@property='og:url']"))
    if canonical is not None and canonical.get("href"):
        record.breed_url = canonical.get("href", "").strip()
    elif og_url is not None and og_url.get("content"):
        record.breed_url = og_url.get("content", "").strip()


def parse_overview(doc: HtmlElement, record: BreedRecord) -> None:
    query = f".//*[{has_class('breed-page__hero__overview__title')}]"
    for title in doc.xpath(query):
        label = element_text(title)
        value = element_text(first(title.xpath("following-sibling::p[1]")))
        if label == "Height":
            record.height = value
        elif label == "Weight":
            record.weight = value
        elif label == "Life Expectancy":
            record.life_expectancy = value


def parse_traits(doc: HtmlElement, record: BreedRecord) -> None:
    seen = set()

    # Prefer the All Traits panel because it contains every trait in one place.
    roots = doc.xpath(
        f".//*[@id='breed-page__traits__all']//*[{has_class('breed-trait-group__trait')}]"
    )
    if not roots:
        roots = doc.xpath(
            f".//*[{has_class('breed-page__traits')}]//*[{has_class('breed-trait-group__trait')}]"
        )

    for trait in roots:
        name_el = first(trait.xpath(f".//*[{has_class('breed-trait-group__header')}]"))
        if name_el is None:
            name_el = first(trait.xpath(f".//*[{has_class('accordion__header__text')}]"))
        if name_el is None:
            name_el = first(trait.xpath(".//h4"))
        name = element_text(name_el)
        column = TRAIT_COLUMNS.get(name)
        if not column or column in seen:
            continue

        value = score_value(trait)
        setattr(record, column, value)
        seen.add(column)


def parse_table_rows(table: HtmlElement | None, kind: str) -> str:
    if table is None:
        return ""

    rows = []
    for tr in table.xpath(".//tbody/tr"):
        cells = tr.xpath("./td")
        if kind == "colors" and len(cells) >= 3:
            desc = element_text(cells[0])
            code = element_text(cells[1])
            standard = "yes" if cells[2].xpath(".//svg") else element_text(cells[2])
            rows.append(f"{desc} (code: {code}, standard: {standard})")
        elif kind == "markings" and len(cells) >= 3:
            desc = element_text(cells[0])
            standard = "yes" if cells[1].xpath(".//svg") else element_text(cells[1])
            code = element_text(cells[2])
            rows.append(f"{desc} (code: {code}, standard: {standard})")

    return "; ".join(row for row in rows if row)


def parse_colors_and_markings(doc: HtmlElement, record: BreedRecord) -> None:
    record.colors = parse_table_rows(first(doc.xpath(".//*[@id='colors-t-h']")), "colors")
    record.markings = parse_table_rows(first(doc.xpath(".//*[@id='markings-t-h']")), "markings")


def parse_about(doc: HtmlElement, record: BreedRecord) -> None:
    about = first(doc.xpath(f".//*[{has_class('breed-page__about')}]"))
    if about is None:
        return

    text_node = first(about.xpath(f".//*[{has_class('breed-page__about__read-more__text')}]"))
    record.about_the_breed = element_text(text_node if text_node is not None else about)


def first_content_paragraph(wrap: HtmlElement) -> str:
    padding = first(wrap.xpath(f".//*[{has_class('breed-table__accordion-padding')}]"))
    if padding is None:
        return element_text(first(wrap.xpath(f".//*[{has_class('breed-table__accordion')}]")))

    # Email/signup and ad blocks are not part of the care content.
    noisy_query = (
        f".//form | .//*[{has_class('breed_ad_container')}]"
        f" | .//*[{has_class('breed-table__email-box')}]"
    )
    for noisy in padding.xpath(noisy_query):
        parent = noisy.getparent()
        if parent is not None:
            parent.remove(noisy)

    return element_text(padding)


def parse_care_sections(doc: HtmlElement, record: BreedRecord) -> None:
    labels = {
        "health": "health",
        "grooming": "grooming",
        "exercise": "exercise",
        "training": "training",
        "nutrition": "nutrition",
    }

    for wrap in doc.xpath(f".//*[{has_class('breed-table__wrap')}]"):
        header = element_text(first(wrap.xpath(f".//h3[{has_class('breed-table__header')}]"))).lower()
        attr = labels.get(header)
        if attr:
            setattr(record, attr, first_content_paragraph(wrap))


def parse_history(doc: HtmlElement, record: BreedRecord) -> None:
    history = first(doc.xpath(f".//*[{has_class('breed-page__history')}]"))
    if history is None:
        return

    content = first(history.xpath(f".//*[{has_class('breed-page__history__text-content')}]"))
    record.history = element_text(content if content is not None else history)


def parse_html_file(path: Path) -> BreedRecord:
    html = path.read_text(encoding="utf-8", errors="replace")
    doc = html_from_string(html)
    record = BreedRecord(source_file=str(path))

    parse_name_and_url(doc, record)
    parse_overview(doc, record)
    parse_traits(doc, record)
    parse_colors_and_markings(doc, record)
    parse_about(doc, record)
    parse_care_sections(doc, record)
    parse_history(doc, record)

    if not record.breed_name:
        record.breed_name = path.stem.replace("-", " ").replace("_", " ").title()

    return record


def html_from_string(value: str) -> HtmlElement:
    return html.fromstring(value)


def iter_html_files(input_dir: Path) -> Iterable[Path]:
    patterns = ("*.html", "*.htm")
    for pattern in patterns:
        yield from sorted(input_dir.glob(pattern))


def write_csv(records: list[BreedRecord], output_file: Path) -> None:
    output_file.parent.mkdir(parents=True, exist_ok=True)
    with output_file.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
        writer.writeheader()
        for record in records:
            writer.writerow(asdict(record))


def main() -> None:
    parser = argparse.ArgumentParser(description="Parse saved AKC breed HTML files into CSV.")
    parser.add_argument("--input-dir", type=Path, default=DEFAULT_INPUT_DIR)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT_FILE)
    args = parser.parse_args()

    files = list(iter_html_files(args.input_dir))
    if not files:
        raise SystemExit(f"No HTML files found in {args.input_dir}")

    records = [parse_html_file(path) for path in files]
    write_csv(records, args.output)
    print(f"Saved {len(records)} records to {args.output}")


if __name__ == "__main__":
    main()
