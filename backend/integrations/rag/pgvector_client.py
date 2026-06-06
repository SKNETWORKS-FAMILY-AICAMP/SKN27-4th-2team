from __future__ import annotations

import os
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
