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
DEFAULT_TABLE = "rag_chunks"


class PGVectorRAGClient:
    """RAG client backed by PostgreSQL + pgvector."""

    def __init__(
        self,
        project_dir: Path | None = None,
        table: str | None = None,
        embedding_model: str | None = None,
    ) -> None:
        self.project_dir = project_dir or PROJECT_DIR
        load_dotenv(self.project_dir / ".env", encoding="utf-8-sig")

        self.table = _validate_identifier(table or os.getenv("PGVECTOR_TABLE", DEFAULT_TABLE))
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
                return _search_apartment_recommendation_documents(conn=conn, top_k=top_k)

        query_vector = _vector_literal(self._embedding_model().embed_query(query))

        with psycopg.connect(**_db_config()) as conn:
            rows = _search_chunks(
                conn=conn,
                table=self.table,
                query_vector=query_vector,
                k=top_k,
                source_filter=_source_filter_from_categories(categories, breed_names),
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
    top_k: int,
) -> list[RetrievedDocument]:
    sql = """
        SELECT
            b.breed_name,
            bs.doc_id,
            bs.metadata
        FROM breed_sections bs
        JOIN breeds b ON bs.breed_id = b.id
        WHERE bs.section = 'basic_profile'
          AND bs.metadata ? 'profile'
          AND bs.metadata ? 'trait_scores'
    """

    with conn.cursor() as cur:
        cur.execute(sql)
        rows = cur.fetchall()

    candidates: list[dict[str, Any]] = []
    for breed_name, doc_id, metadata in rows:
        metadata = metadata if isinstance(metadata, dict) else {}
        profile = _json_metadata_value(metadata.get("profile"))
        traits = _json_metadata_value(metadata.get("trait_scores"))
        score = _score_apartment_fit(profile=profile, traits=traits)
        if score is None:
            continue

        candidates.append(
            {
                "breed_name": breed_name,
                "doc_id": doc_id,
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


def _search_chunks(
    conn: psycopg.Connection,
    table: str,
    query_vector: str,
    k: int,
    source_filter: str | None,
    breed_names: list[str] | None,
    sections: list[str] | None,
) -> list[dict[str, Any]]:
    where_clauses: list[str] = []
    params: list[Any] = [query_vector]

    if source_filter:
        where_clauses.append("r.source = %s")
        params.append(source_filter)

    if breed_names:
        where_clauses.append("b.breed_name ILIKE ANY(%s)")
        params.append([f"%{breed_name}%" for breed_name in breed_names])

    if sections:
        where_clauses.append("(bs.section = ANY(%s) OR bs.section IS NULL)")
        params.append(sections)

    where_sql = f"WHERE {' AND '.join(where_clauses)}" if where_clauses else ""

    sql = f"""
        SELECT
            r.chunk_id,
            r.doc_id,
            r.source,
            r.metadata,
            r.text,
            1 - (r.embedding <=> %s::vector) AS similarity,
            b.breed_name,
            bs.section AS breed_section,
            bs.section_title AS breed_section_title
        FROM {table} r
        LEFT JOIN breed_sections bs ON r.breed_section_id = bs.id
        LEFT JOIN breeds b ON bs.breed_id = b.id
        {where_sql}
        ORDER BY r.embedding <=> %s::vector
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
            row_source,
            metadata,
            text,
            similarity,
            breed_name,
            breed_section,
            breed_section_title,
        ) = row
        row_metadata = metadata if isinstance(metadata, dict) else {}
        title = (
            row_metadata.get("title")
            or row_metadata.get("question")
            or breed_section_title
        )
        results.append(
            {
                "rank": rank,
                "chunk_id": chunk_id,
                "doc_id": doc_id,
                "source": row_source,
                "metadata": row_metadata,
                "text": text,
                "similarity": float(similarity),
                "breed_name": breed_name,
                "breed_section": breed_section,
                "breed_section_title": breed_section_title,
                "title": title,
                "article_url": row_metadata.get("url"),
            }
        )

    return results


def _row_to_document(row: dict[str, Any]) -> RetrievedDocument:
    metadata = dict(row.get("metadata") or {})
    metadata.update(
        {
            "rank": row.get("rank"),
            "source": row.get("source"),
            "doc_id": row.get("doc_id"),
            "chunk_id": row.get("chunk_id"),
            "breed_name": row.get("breed_name"),
            "section": row.get("breed_section"),
            "section_title": row.get("breed_section_title"),
            "title": row.get("title"),
            "article_url": row.get("article_url"),
        }
    )

    return RetrievedDocument(
        document_id=str(row["chunk_id"]),
        content=str(row.get("text") or ""),
        score=row.get("similarity"),
        metadata={key: value for key, value in metadata.items() if value is not None},
    )
