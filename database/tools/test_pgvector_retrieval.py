"""Search PostgreSQL + pgvector RAG table with source-table joins.

- 이 파일의 역할:
  - 사용자의 query를 OpenAI embedding으로 변환한다.
  - rag_chunks에서 pgvector cosine 검색을 수행한다.
  - source별 원천 테이블을 LEFT JOIN해 ERD 관계가 맞게 연결되는지 확인한다.

"""

from __future__ import annotations

import argparse
import json
import os
import re
from pathlib import Path
from typing import Any

import psycopg
from dotenv import load_dotenv
from langchain_openai import OpenAIEmbeddings


def vector_literal(values: list[float]) -> str:
    return "[" + ",".join(str(float(v)) for v in values) + "]"


def validate_identifier(name: str) -> str:
    if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", name):
        raise ValueError(f"Invalid SQL identifier: {name}")
    return name


def db_config() -> dict[str, Any]:
    return {
        "host": os.getenv("POSTGRES_HOST", "localhost"),
        "port": int(os.getenv("POSTGRES_PORT", "5432")),
        "dbname": os.getenv("POSTGRES_DB", "dog_rag"),
        "user": os.getenv("POSTGRES_USER", "dog_user"),
        "password": os.getenv("POSTGRES_PASSWORD", "dog_password"),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Search PostgreSQL pgvector table")
    parser.add_argument("--base-dir", type=Path, default=Path(__file__).resolve().parents[2])
    parser.add_argument("--query", required=True)
    parser.add_argument("--k", type=int, default=5)
    parser.add_argument("--source", default=None)
    parser.add_argument("--embedding-model", default=None)
    args = parser.parse_args()

    base_dir = args.base_dir.resolve()
    load_dotenv(base_dir / ".env", encoding="utf-8-sig")

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY is empty. Fill it in the project .env file first.")

    table = validate_identifier(os.getenv("PGVECTOR_TABLE", "rag_chunks"))
    embedding_model = args.embedding_model or os.getenv("OPENAI_EMBEDDING_MODEL", "text-embedding-3-small")
    embeddings = OpenAIEmbeddings(model=embedding_model, api_key=api_key)
    query_vector = vector_literal(embeddings.embed_query(args.query))

    where_sql = "WHERE r.source = %s" if args.source else ""
    sql = f"""
        SELECT
            r.chunk_id,
            r.doc_id,
            r.source,
            r.metadata,
            LEFT(r.text, 500) AS preview,
            1 - (r.embedding <=> %s::vector) AS similarity,
            b.breed_name,
            bs.section_title AS breed_section_title,
            q.question AS qna_question,
            yd.title AS youtube_title,
            ad.title AS article_title,
            ad.url AS article_url
        FROM {table} r
        LEFT JOIN breed_sections bs ON r.breed_section_id = bs.id
        LEFT JOIN breeds b ON bs.breed_id = b.id
        LEFT JOIN qna_items q ON r.qna_id = q.id
        LEFT JOIN youtube_docs yd ON r.youtube_doc_id = yd.id
        LEFT JOIN article_docs ad ON r.article_doc_id = ad.id
        {where_sql}
        ORDER BY r.embedding <=> %s::vector
        LIMIT %s
    """
    if args.source:
        params = [query_vector, args.source, query_vector, args.k]
    else:
        params = [query_vector, query_vector, args.k]

    with psycopg.connect(**db_config()) as conn:
        with conn.cursor() as cur:
            cur.execute(sql, params)
            rows = cur.fetchall()

    results = []
    for rank, row in enumerate(rows, start=1):
        (
            chunk_id, doc_id, source, metadata, preview, similarity,
            breed_name, breed_section_title, qna_question, youtube_title,
            article_title, article_url,
        ) = row
        title = article_title or youtube_title or breed_section_title or qna_question
        results.append({
            "rank": rank,
            "similarity": float(similarity),
            "source": source,
            "source_file": metadata.get("source_file") if isinstance(metadata, dict) else None,
            "doc_id": doc_id,
            "chunk_id": chunk_id,
            "title": title,
            "breed_name": breed_name,
            "article_url": article_url,
            "preview": preview,
        })

    print(json.dumps({
        "query": args.query,
        "k": args.k,
        "source_filter": args.source,
        "table": table,
        "results": results,
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
