from __future__ import annotations

import os
import json
import re
from pathlib import Path
from typing import Any

import psycopg
from dotenv import load_dotenv
from langchain_openai import OpenAIEmbeddings

from backend.integrations.rag.schemas import RetrievedDocument


PROJECT_DIR = Path(__file__).resolve().parents[3]
DEFAULT_EMBEDDING_MODEL = "text-embedding-3-small"
DEFAULT_TABLE = "langchain_pg_embedding"
DEFAULT_COLLECTION_NAME = "dog_rag_documents"

SECTION_TITLES = {
    "basic_profile": "Basic Profile",
    "about_the_breed": "About the Breed",
    "traits": "Breed Traits & Characteristics",
    "colors_markings": "Breed Colors & Markings",
    "health": "Health",
    "grooming": "Grooming",
    "exercise": "Exercise",
    "training": "Training",
    "nutrition": "Nutrition",
    "history": "History",
}

TRAIT_LABELS = {
    "Adaptability Level": "adaptability_level",
    "Energy Level": "energy_level",
    "Barking Level": "barking_level",
    "Trainability Level": "trainability_level",
    "Mental Stimulation Needs": "mental_stimulation_needs",
}


class PGVectorRAGClient:
    """RAG client backed by PostgreSQL + pgvector."""

    def __init__(
        self,
        project_dir: Path | None = None,
        table: str | None = None,
        embedding_model: str | None = None,
        collection_name: str | None = None,
    ) -> None:
        self.project_dir = project_dir or PROJECT_DIR
        load_dotenv(self.project_dir / ".env", encoding="utf-8-sig")

        self.table = _validate_identifier(table or os.getenv("PGVECTOR_TABLE", DEFAULT_TABLE))
        self.collection_name = collection_name or os.getenv("PGVECTOR_COLLECTION", DEFAULT_COLLECTION_NAME)
        self.embedding_model_name = (
            embedding_model
            or os.getenv("OPENAI_EMBEDDING_MODEL")
            or DEFAULT_EMBEDDING_MODEL
        )
        self._embeddings: OpenAIEmbeddings | None = None

    def search_documents(
        self,
        query: str,
        categories: list[str] | None = None,
        breed_names: list[str] | None = None,
        sections: list[str] | None = None,
        top_k: int = 5,
    ) -> list[RetrievedDocument]:
        if not query.strip():
            return []

        if _is_apartment_recommendation_query(query, categories):
            with psycopg.connect(**_db_config()) as conn:
                return _search_apartment_recommendation_documents(
                    conn=conn,
                    table=self.table,
                    collection_name=self.collection_name,
                    top_k=top_k,
                )

        query_vector = _vector_literal(self._embedding_model().embed_query(query))

        with psycopg.connect(**_db_config()) as conn:
            rows = _search_chunks(
                conn=conn,
                table=self.table,
                collection_name=self.collection_name,
                query_vector=query_vector,
                k=top_k,
                categories=categories,
                breed_names=breed_names,
                sections=sections,
            )

        return [_row_to_document(row) for row in rows]

    def _embedding_model(self) -> OpenAIEmbeddings:
        if self._embeddings is not None:
            return self._embeddings

        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise RuntimeError("OPENAI_API_KEY is empty. Check the project .env file.")

        self._embeddings = OpenAIEmbeddings(
            model=self.embedding_model_name,
            api_key=api_key,
        )
        return self._embeddings


def _db_config() -> dict[str, Any]:
    return {
        "host": os.getenv("POSTGRES_HOST", "localhost"),
        "port": int(os.getenv("POSTGRES_PORT", "5432")),
        "dbname": os.getenv("POSTGRES_DB", "pet_dog"),
        "user": os.getenv("POSTGRES_USER", "admin"),
        "password": os.getenv("POSTGRES_PASSWORD", "admin1234"),
    }


def _validate_identifier(name: str) -> str:
    if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", name):
        raise ValueError(f"Invalid SQL identifier: {name}")
    return name


def _vector_literal(values: list[float]) -> str:
    return "[" + ",".join(str(float(value)) for value in values) + "]"


def _source_filter_from_categories(
    categories: list[str] | None,
    breed_names: list[str] | None,
) -> str | None:
    if not categories or breed_names:
        return None

    if "breed_recommendation" in categories:
        return "akc_breed"

    category_sources = {
        "breed_recommendation": "akc_breed",
        "health": "youtube_vet",
        "nutrition": "article",
        "training": "youtube_training",
        "walking": "youtube_training",
        "grooming": "article",
    }
    matched_sources = [
        category_sources[category]
        for category in categories
        if category in category_sources
    ]

    if len(set(matched_sources)) == 1:
        return matched_sources[0]

    return None


def _is_apartment_recommendation_query(
    query: str,
    categories: list[str] | None,
) -> bool:
    if not categories or "breed_recommendation" not in categories:
        return False

    apartment_keywords = ["아파트", "원룸", "실내", "작은 집", "공동주택", "소형"]
    return any(keyword in query for keyword in apartment_keywords)


def _search_apartment_recommendation_documents(
    conn: psycopg.Connection,
    table: str,
    collection_name: str,
    top_k: int,
) -> list[RetrievedDocument]:
    sql = f"""
        SELECT
            e.document,
            e.cmetadata
        FROM {table} e
        JOIN langchain_pg_collection c ON e.collection_id = c.uuid
        WHERE c.name = %s
          AND e.cmetadata->>'doc_type' = 'breed_section'
          AND e.cmetadata->>'section' = ANY(%s)
    """

    with conn.cursor() as cur:
        cur.execute(sql, [collection_name, ["basic_profile", "traits"]])
        rows = cur.fetchall()

    grouped: dict[str, dict[str, Any]] = {}
    for document, metadata in rows:
        metadata = metadata if isinstance(metadata, dict) else {}
        doc_id = str(metadata.get("doc_id") or "")
        slug = _akc_slug_from_doc_id(doc_id)
        if not slug:
            continue

        section = metadata.get("section")
        grouped.setdefault(slug, {"doc_id": doc_id, "sections": {}})
        grouped[slug]["sections"][section] = str(document or "")

    candidates: list[dict[str, Any]] = []
    for slug, item in grouped.items():
        profile = _parse_basic_profile(item["sections"].get("basic_profile", ""))
        traits = _parse_traits(item["sections"].get("traits", ""))
        if not profile or not traits:
            continue

        score = _score_apartment_fit(profile=profile, traits=traits)
        if score is None:
            continue

        breed_name = profile.get("breed_name") or _breed_name_from_slug(slug)
        candidates.append(
            {
                "breed_name": breed_name,
                "doc_id": item["doc_id"],
                "profile": profile,
                "traits": traits,
                "score": score,
            }
        )

    candidates.sort(key=lambda item: (-item["score"], item["breed_name"]))
    selected = candidates[:top_k]

    documents: list[RetrievedDocument] = []
    for rank, candidate in enumerate(selected, start=1):
        breed_name = candidate["breed_name"]
        content = _build_apartment_recommendation_content(candidate)
        documents.append(
            RetrievedDocument(
                document_id=f"structured_apartment_recommendation_{rank}_{_slugify(breed_name)}",
                content=content,
                score=round(float(candidate["score"]), 4),
                metadata={
                    "rank": rank,
                    "source": "akc_breed",
                    "doc_id": candidate["doc_id"],
                    "chunk_id": f"structured_apartment_recommendation_{rank}_{_slugify(breed_name)}",
                    "breed_name": breed_name,
                    "section": "apartment_recommendation",
                    "section_title": "Apartment Recommendation",
                    "title": "Apartment Recommendation",
                },
            )
        )

    return documents


def _json_metadata_value(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return value
    if isinstance(value, str):
        try:
            parsed = json.loads(value)
        except json.JSONDecodeError:
            return {}
        return parsed if isinstance(parsed, dict) else {}
    return {}


def _score_apartment_fit(
    *,
    profile: dict[str, Any],
    traits: dict[str, Any],
) -> float | None:
    weight_max = _as_float(profile.get("weight_max"))
    adaptability = _as_float(traits.get("adaptability_level"))
    energy = _as_float(traits.get("energy_level"))
    barking = _as_float(traits.get("barking_level"))
    trainability = _as_float(traits.get("trainability_level"))
    mental = _as_float(traits.get("mental_stimulation_needs"))

    if weight_max is None or adaptability is None or energy is None:
        return None

    score = 0.0

    if weight_max <= 12:
        score += 4.0
    elif weight_max <= 20:
        score += 3.0
    elif weight_max <= 30:
        score += 1.5
    elif weight_max <= 45:
        score += 0.5
    else:
        score -= 2.0

    score += adaptability * 1.0
    score += (6 - energy) * 0.9

    if barking is not None:
        score += (6 - barking) * 0.8

    if trainability is not None:
        score += trainability * 0.3

    if mental is not None:
        score += (6 - mental) * 0.3

    return score


def _as_float(value: Any) -> float | None:
    try:
        if value is None:
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def _build_apartment_recommendation_content(candidate: dict[str, Any]) -> str:
    profile = candidate["profile"]
    traits = candidate["traits"]
    return (
        f"Breed: {candidate['breed_name']}\n"
        "Section: Apartment Recommendation\n"
        f"Apartment fit score: {round(float(candidate['score']), 2)}\n"
        f"Weight range: {profile.get('weight_min')} - {profile.get('weight_max')} pounds\n"
        f"Height range: {profile.get('height_min')} - {profile.get('height_max')} inches\n"
        f"Life expectancy: {profile.get('life_expectancy_min')} - {profile.get('life_expectancy_max')} years\n"
        f"Adaptability Level: {traits.get('adaptability_level')}\n"
        f"Energy Level: {traits.get('energy_level')}\n"
        f"Barking Level: {traits.get('barking_level')}\n"
        f"Trainability Level: {traits.get('trainability_level')}\n"
        f"Mental Stimulation Needs: {traits.get('mental_stimulation_needs')}\n"
        "Recommendation basis: smaller body size, adaptability, moderate or low energy, barking level, "
        "trainability, and mental stimulation needs from AKC breed data."
    )


def _slugify(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")


def _breed_search_patterns(breed_names: list[str]) -> list[str]:
    patterns: list[str] = []
    for breed_name in breed_names:
        name = breed_name.strip()
        if not name:
            continue
        slug = _slugify(name)
        patterns.append(f"%{name}%")
        if slug:
            patterns.append(f"%{slug}%")
    return patterns


def _normalize_source(metadata: dict[str, Any]) -> str:
    source = str(metadata.get("source") or "").strip()
    doc_type = str(metadata.get("doc_type") or "").strip()
    doc_id = str(metadata.get("doc_id") or "").strip()

    if source == "qna":
        return "qna"
    if source == "YouTube":
        if str(metadata.get("expert_role") or "").strip() == "veterinarian":
            return "youtube_vet"
        return "youtube_training"
    if source == "American Kennel Club":
        if doc_type == "breed_section" or doc_id.startswith("akc_breed:"):
            return "akc_breed"
        return "article"
    return source or "unknown"


def _title_from_metadata_or_text(metadata: dict[str, Any], text: str, section: str) -> str:
    for key in ("title", "question", "section_title"):
        value = metadata.get(key)
        if value:
            return str(value).strip()

    if metadata.get("source") == "qna":
        question = _extract_qna_question(text)
        if question:
            return question

    return SECTION_TITLES.get(section) or ""


def _extract_qna_question(text: str) -> str:
    match = re.search(r"Question:\s*(.+?)(?:\n\s*\n|Answer:|$)", text, flags=re.DOTALL)
    if not match:
        return ""
    return re.sub(r"\s+", " ", match.group(1)).strip()


def _parse_basic_profile(text: str) -> dict[str, Any]:
    if not text.strip():
        return {}

    profile = {
        "breed_name": _line_value(text, "Breed Name"),
        "height_min": _range_value(_line_value(text, "Height"), minimum=True),
        "height_max": _range_value(_line_value(text, "Height"), minimum=False),
        "weight_min": _range_value(_line_value(text, "Weight"), minimum=True),
        "weight_max": _range_value(_line_value(text, "Weight"), minimum=False),
        "life_expectancy_min": _range_value(_line_value(text, "Life Expectancy"), minimum=True),
        "life_expectancy_max": _range_value(_line_value(text, "Life Expectancy"), minimum=False),
    }
    return {key: value for key, value in profile.items() if value not in (None, "")}


def _parse_traits(text: str) -> dict[str, Any]:
    traits: dict[str, Any] = {}
    for label, key in TRAIT_LABELS.items():
        match = re.search(rf"-\s*{re.escape(label)}:\s*(\d+)", text)
        if match:
            traits[key] = float(match.group(1))
    return traits


def _line_value(text: str, label: str) -> str:
    match = re.search(rf"^{re.escape(label)}:\s*(.+)$", text, flags=re.MULTILINE)
    return match.group(1).strip() if match else ""


def _range_value(text: str, *, minimum: bool) -> float | None:
    numbers = [float(value) for value in re.findall(r"\d+(?:\.\d+)?", text)]
    if not numbers:
        return None
    return min(numbers) if minimum else max(numbers)


def _akc_slug_from_doc_id(doc_id: str) -> str:
    if not doc_id.startswith("akc_breed:"):
        return ""
    parts = doc_id.split(":")
    return parts[1].strip() if len(parts) >= 2 else ""


def _breed_name_from_doc_id(doc_id: str) -> str:
    slug = _akc_slug_from_doc_id(doc_id)
    return _breed_name_from_slug(slug) if slug else ""


def _breed_name_from_slug(slug: str) -> str:
    return slug.replace("-", " ").title()


def _breed_name_from_text(text: str) -> str:
    return _line_value(text, "Breed Name")


def _search_chunks(
    conn: psycopg.Connection,
    table: str,
    collection_name: str,
    query_vector: str,
    k: int,
    categories: list[str] | None,
    breed_names: list[str] | None,
    sections: list[str] | None,
) -> list[dict[str, Any]]:
    where_clauses: list[str] = ["c.name = %s"]
    params: list[Any] = [query_vector, collection_name]

    if categories and "breed_recommendation" in categories and not breed_names:
        where_clauses.append("e.cmetadata->>'doc_type' = %s")
        params.append("breed_section")

    if breed_names:
        patterns = _breed_search_patterns(breed_names)
        where_clauses.append("(e.document ILIKE ANY(%s) OR e.cmetadata->>'doc_id' ILIKE ANY(%s))")
        params.extend([patterns, patterns])

    if sections:
        where_clauses.append("((e.cmetadata->>'section') = ANY(%s) OR NOT (e.cmetadata ? 'section'))")
        params.append(sections)

    where_sql = f"WHERE {' AND '.join(where_clauses)}"

    sql = f"""
        SELECT
            e.id,
            COALESCE(e.cmetadata->>'doc_id', e.id),
            e.cmetadata,
            e.document,
            1 - (e.embedding <=> %s::vector) AS similarity,
            c.name
        FROM {table} e
        JOIN langchain_pg_collection c ON e.collection_id = c.uuid
        {where_sql}
        ORDER BY e.embedding <=> %s::vector
        LIMIT %s
    """
    params.extend([query_vector, k])

    with conn.cursor() as cur:
        cur.execute(sql, params)
        rows = cur.fetchall()

    results: list[dict[str, Any]] = []
    for rank, row in enumerate(rows, start=1):
        (
            chunk_id,
            doc_id,
            metadata,
            text,
            similarity,
            collection_name,
        ) = row
        row_metadata = metadata if isinstance(metadata, dict) else {}
        results.append(
            {
                "rank": rank,
                "chunk_id": chunk_id,
                "doc_id": doc_id,
                "metadata": row_metadata,
                "text": text,
                "similarity": float(similarity),
                "collection_name": collection_name,
            }
        )

    return results


def _row_to_document(row: dict[str, Any]) -> RetrievedDocument:
    metadata = dict(row.get("metadata") or {})
    text = str(row.get("text") or "")
    doc_id = str(row.get("doc_id") or row.get("chunk_id") or "")
    section = str(metadata.get("section") or "")
    title = _title_from_metadata_or_text(metadata, text, section)
    breed_name = _breed_name_from_doc_id(doc_id) or _breed_name_from_text(text)

    if _normalize_source(metadata) == "qna" and title:
        metadata["question"] = title

    metadata.update(
        {
            "rank": row.get("rank"),
            "source": _normalize_source(metadata),
            "original_source": metadata.get("source"),
            "doc_id": doc_id,
            "chunk_id": row.get("chunk_id"),
            "breed_name": breed_name,
            "section": section or None,
            "section_title": SECTION_TITLES.get(section),
            "title": title,
            "article_url": metadata.get("url"),
            "collection_name": row.get("collection_name"),
        }
    )

    return RetrievedDocument(
        document_id=str(row["chunk_id"]),
        content=text,
        score=row.get("similarity"),
        metadata={key: value for key, value in metadata.items() if value is not None and value != ""},
    )
