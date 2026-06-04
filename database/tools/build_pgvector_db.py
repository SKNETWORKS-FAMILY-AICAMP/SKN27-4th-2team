"""Build PostgreSQL + pgvector ERD-friendly RAG tables.

- 이 파일의 역할:
  - all_chunks.jsonl을 읽어 source별 원천 테이블을 먼저 생성/적재한다.
  - rag_chunks는 원천 데이터를 대체하지 않고, 검색용 embedding index로만 사용한다.
  - rag_chunks에는 source별 nullable FK를 둔다.

- 생성되는 원천 테이블:
  - breeds: AKC 품종 기본 엔티티
  - breed_sections: 품종별 섹션 문서
  - qna_items: 강형욱/설채현 QnA 문서
  - youtube_docs: YouTube 기초교육/수의학 문서
  - article_docs: AKC article 문서

- 생성되는 검색 인덱스 테이블:
  - rag_chunks: text + metadata + embedding + source별 FK를 가진 pgvector 검색 테이블

- 실행 예시:
  - 테스트: python database/tools/build_pgvector_db.py --reset --limit 100
  - 전체: python database/tools/build_pgvector_db.py --reset
"""

from __future__ import annotations

import argparse
import json
import os
import re
import time
from pathlib import Path
from typing import Any

import psycopg
from dotenv import load_dotenv
from langchain_openai import OpenAIEmbeddings
from openai import RateLimitError
from psycopg.types.json import Jsonb

DEFAULT_BATCH_SIZE = 50
DEFAULT_EMBEDDING_DIM = 1536
DEFAULT_MAX_RETRIES = 8
DEFAULT_RETRY_SLEEP = 2.0


def load_chunks(path: Path, limit: int | None = None) -> list[dict[str, Any]]:
    """JSONL chunk 파일을 읽는다.

    - 입력은 database/chunks/all_chunks.jsonl이다.
    - text가 비어 있는 row는 embedding 대상이 아니므로 제외한다.
    - limit 옵션이 있으면 앞 N개만 읽어 테스트 적재할 수 있다.
    """
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            if limit is not None and len(rows) >= limit:
                break
            line = line.strip()
            if not line:
                continue
            row = json.loads(line)
            if row.get("text"):
                rows.append(row)
    return rows


def batched(rows: list[dict[str, Any]], batch_size: int):
    """OpenAI embedding과 DB insert를 batch 단위로 처리한다."""
    for start in range(0, len(rows), batch_size):
        yield start, rows[start : start + batch_size]


def embed_documents_with_retry(
    embeddings: OpenAIEmbeddings,
    texts: list[str],
    max_retries: int,
    retry_sleep: float,
) -> list[list[float]]:
    """OpenAI rate limit이 발생하면 기다렸다가 같은 batch를 재시도한다.

    - 429 RateLimitError는 API 키나 DB 문제가 아니라 분당 token 처리량 제한이다.
    - 실패한 batch를 버리지 않고 sleep 후 다시 요청한다.
    - 재시도 간격은 2초, 4초, 8초처럼 점점 늘리되 너무 길어지지 않게 제한한다.
    """
    for attempt in range(max_retries + 1):
        try:
            return embeddings.embed_documents(texts)
        except RateLimitError as exc:
            if attempt >= max_retries:
                raise
            wait_seconds = min(retry_sleep * (2 ** attempt), 60.0)
            print(
                f"OpenAI rate limit reached. Retrying in {wait_seconds:.1f}s "
                f"({attempt + 1}/{max_retries})..."
            )
            time.sleep(wait_seconds)
    raise RuntimeError("Embedding retry loop ended unexpectedly")


def load_existing_chunk_ids(conn: psycopg.Connection, table: str) -> set[str]:
    """이미 rag_chunks에 저장된 chunk_id를 읽어 resume 실행에 사용한다.

    - --reset 없이 다시 실행하면 이전 성공분은 유지된다.
    - 이 함수 덕분에 이미 들어간 chunk는 다시 embedding하지 않고 건너뛴다.
    """
    with conn.cursor() as cur:
        cur.execute(f"SELECT chunk_id FROM {table}")
        return {row[0] for row in cur.fetchall()}


def vector_literal(values: list[float]) -> str:
    """pgvector가 받을 수 있는 '[0.1,0.2,...]' 문자열로 변환한다."""
    return "[" + ",".join(str(float(v)) for v in values) + "]"


def validate_identifier(name: str) -> str:
    """동적 테이블명에 SQL injection이 들어가지 않도록 제한한다."""
    if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", name):
        raise ValueError(f"Invalid SQL identifier: {name}")
    return name


def db_config() -> dict[str, Any]:
    """.env에서 PostgreSQL 접속 정보를 읽는다."""
    return {
        "host": os.getenv("POSTGRES_HOST", "localhost"),
        "port": int(os.getenv("POSTGRES_PORT", "5432")),
        "dbname": os.getenv("POSTGRES_DB", "dog_rag"),
        "user": os.getenv("POSTGRES_USER", "dog_user"),
        "password": os.getenv("POSTGRES_PASSWORD", "dog_password"),
    }


def row_metadata(row: dict[str, Any]) -> dict[str, Any]:
    """chunk row의 metadata에 추적용 공통 필드를 추가한다."""
    metadata = dict(row.get("metadata") or {})
    metadata["chunk_id"] = row.get("chunk_id")
    metadata["doc_id"] = row.get("doc_id")
    metadata["source"] = row.get("source")
    return metadata


def split_qna_text(body: str) -> tuple[str | None, str | None]:
    """'Question: ...\nAnswer: ...' 형태에서 question/answer를 보조 추출한다."""
    if "Answer:" not in body:
        return None, None
    q_part, a_part = body.split("Answer:", 1)
    question = q_part.replace("Question:", "", 1).strip()
    answer = a_part.strip()
    return question or None, answer or None


def ensure_schema(conn: psycopg.Connection, table: str, dim: int, reset: bool) -> None:
    """pgvector 확장, source별 원천 테이블, rag_chunks 테이블을 준비한다.

    - reset=True이면 전체 RAG 관련 테이블을 삭제 후 재생성한다.
    - rag_chunks는 source별 nullable FK를 가진 검색용 embedding index다.
    - 원천 테이블은 ERD에서 데이터 성격을 설명하기 위한 도메인 테이블이다.
    """
    with conn.cursor() as cur:
        cur.execute("CREATE EXTENSION IF NOT EXISTS vector")
        if reset:
            cur.execute(f"DROP TABLE IF EXISTS {table} CASCADE")
            cur.execute("DROP TABLE IF EXISTS breed_sections CASCADE")
            cur.execute("DROP TABLE IF EXISTS breeds CASCADE")
            cur.execute("DROP TABLE IF EXISTS qna_items CASCADE")
            cur.execute("DROP TABLE IF EXISTS youtube_docs CASCADE")
            cur.execute("DROP TABLE IF EXISTS article_docs CASCADE")

        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS breeds (
                id BIGSERIAL PRIMARY KEY,
                breed_name TEXT UNIQUE NOT NULL,
                metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
            )
            """
        )
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS breed_sections (
                id BIGSERIAL PRIMARY KEY,
                breed_id BIGINT NOT NULL REFERENCES breeds(id) ON DELETE CASCADE,
                doc_id TEXT UNIQUE NOT NULL,
                section TEXT,
                section_title TEXT,
                metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
            )
            """
        )
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS qna_items (
                id BIGSERIAL PRIMARY KEY,
                doc_id TEXT UNIQUE NOT NULL,
                qna_source TEXT,
                question TEXT,
                answer TEXT,
                source_file TEXT,
                metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
            )
            """
        )
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS youtube_docs (
                id BIGSERIAL PRIMARY KEY,
                doc_id TEXT UNIQUE NOT NULL,
                source TEXT NOT NULL,
                video_id TEXT,
                video_url TEXT,
                channel TEXT,
                expert TEXT,
                title TEXT,
                source_file TEXT,
                metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
            )
            """
        )
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS article_docs (
                id BIGSERIAL PRIMARY KEY,
                doc_id TEXT UNIQUE NOT NULL,
                source_file TEXT,
                source_category TEXT,
                title TEXT,
                url TEXT,
                author TEXT,
                updated_date TEXT,
                section_title TEXT,
                doc_type TEXT,
                metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
            )
            """
        )
        cur.execute(
            f"""
            CREATE TABLE IF NOT EXISTS {table} (
                id BIGSERIAL PRIMARY KEY,
                chunk_id TEXT UNIQUE NOT NULL,
                doc_id TEXT NOT NULL,
                source TEXT NOT NULL,
                breed_section_id BIGINT REFERENCES breed_sections(id) ON DELETE CASCADE,
                qna_id BIGINT REFERENCES qna_items(id) ON DELETE CASCADE,
                youtube_doc_id BIGINT REFERENCES youtube_docs(id) ON DELETE CASCADE,
                article_doc_id BIGINT REFERENCES article_docs(id) ON DELETE CASCADE,
                text TEXT NOT NULL,
                metadata JSONB NOT NULL DEFAULT '{{}}'::jsonb,
                embedding VECTOR({dim}) NOT NULL,
                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                CONSTRAINT {table}_one_source_fk CHECK (
                    ((breed_section_id IS NOT NULL)::int +
                     (qna_id IS NOT NULL)::int +
                     (youtube_doc_id IS NOT NULL)::int +
                     (article_doc_id IS NOT NULL)::int) = 1
                )
            )
            """
        )
        cur.execute(f"CREATE INDEX IF NOT EXISTS idx_{table}_source ON {table} (source)")
        cur.execute(f"CREATE INDEX IF NOT EXISTS idx_{table}_metadata ON {table} USING GIN (metadata)")
        cur.execute(f"CREATE INDEX IF NOT EXISTS idx_{table}_breed_section_id ON {table} (breed_section_id)")
        cur.execute(f"CREATE INDEX IF NOT EXISTS idx_{table}_qna_id ON {table} (qna_id)")
        cur.execute(f"CREATE INDEX IF NOT EXISTS idx_{table}_youtube_doc_id ON {table} (youtube_doc_id)")
        cur.execute(f"CREATE INDEX IF NOT EXISTS idx_{table}_article_doc_id ON {table} (article_doc_id)")
    conn.commit()


def upsert_breed_section(cur: psycopg.Cursor, row: dict[str, Any], metadata: dict[str, Any]) -> int:
    """AKC 품종 source row를 breeds/breed_sections에 upsert하고 breed_sections.id를 반환한다."""
    breed_name = metadata.get("breed_name") or "unknown"
    cur.execute(
        """
        INSERT INTO breeds (breed_name, metadata)
        VALUES (%s, %s)
        ON CONFLICT (breed_name) DO UPDATE SET metadata = breeds.metadata || EXCLUDED.metadata
        RETURNING id
        """,
        (breed_name, Jsonb({"breed_name": breed_name})),
    )
    breed_id = cur.fetchone()[0]
    cur.execute(
        """
        INSERT INTO breed_sections (breed_id, doc_id, section, section_title, metadata)
        VALUES (%s, %s, %s, %s, %s)
        ON CONFLICT (doc_id) DO UPDATE SET
            breed_id = EXCLUDED.breed_id,
            section = EXCLUDED.section,
            section_title = EXCLUDED.section_title,
            metadata = EXCLUDED.metadata
        RETURNING id
        """,
        (breed_id, row["doc_id"], metadata.get("section"), metadata.get("section_title"), Jsonb(metadata)),
    )
    return cur.fetchone()[0]


def upsert_qna(cur: psycopg.Cursor, row: dict[str, Any], metadata: dict[str, Any]) -> int:
    """QnA source row를 qna_items에 upsert하고 qna_items.id를 반환한다."""
    question, answer = split_qna_text(row["text"])
    question = metadata.get("question") or question
    cur.execute(
        """
        INSERT INTO qna_items (doc_id, qna_source, question, answer, source_file, metadata)
        VALUES (%s, %s, %s, %s, %s, %s)
        ON CONFLICT (doc_id) DO UPDATE SET
            qna_source = EXCLUDED.qna_source,
            question = EXCLUDED.question,
            answer = EXCLUDED.answer,
            source_file = EXCLUDED.source_file,
            metadata = EXCLUDED.metadata
        RETURNING id
        """,
        (row["doc_id"], metadata.get("qna_source"), question, answer, metadata.get("source_file"), Jsonb(metadata)),
    )
    return cur.fetchone()[0]


def upsert_youtube_doc(cur: psycopg.Cursor, row: dict[str, Any], metadata: dict[str, Any]) -> int:
    """YouTube source row를 youtube_docs에 upsert하고 youtube_docs.id를 반환한다."""
    cur.execute(
        """
        INSERT INTO youtube_docs (doc_id, source, video_id, video_url, channel, expert, title, source_file, metadata)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (doc_id) DO UPDATE SET
            source = EXCLUDED.source,
            video_id = EXCLUDED.video_id,
            video_url = EXCLUDED.video_url,
            channel = EXCLUDED.channel,
            expert = EXCLUDED.expert,
            title = EXCLUDED.title,
            source_file = EXCLUDED.source_file,
            metadata = EXCLUDED.metadata
        RETURNING id
        """,
        (
            row["doc_id"], row["source"], metadata.get("video_id"), metadata.get("video_url"),
            metadata.get("channel"), metadata.get("expert"), metadata.get("title"),
            metadata.get("source_file"), Jsonb(metadata),
        ),
    )
    return cur.fetchone()[0]


def upsert_article_doc(cur: psycopg.Cursor, row: dict[str, Any], metadata: dict[str, Any]) -> int:
    """Article source row를 article_docs에 upsert하고 article_docs.id를 반환한다."""
    cur.execute(
        """
        INSERT INTO article_docs (doc_id, source_file, source_category, title, url, author, updated_date, section_title, doc_type, metadata)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (doc_id) DO UPDATE SET
            source_file = EXCLUDED.source_file,
            source_category = EXCLUDED.source_category,
            title = EXCLUDED.title,
            url = EXCLUDED.url,
            author = EXCLUDED.author,
            updated_date = EXCLUDED.updated_date,
            section_title = EXCLUDED.section_title,
            doc_type = EXCLUDED.doc_type,
            metadata = EXCLUDED.metadata
        RETURNING id
        """,
        (
            row["doc_id"], metadata.get("source_file"), metadata.get("source_category") or metadata.get("category"),
            metadata.get("title"), metadata.get("url"), metadata.get("author"), metadata.get("updated_date"),
            metadata.get("section_title"), metadata.get("doc_type"), Jsonb(metadata),
        ),
    )
    return cur.fetchone()[0]


def upsert_source_doc(cur: psycopg.Cursor, row: dict[str, Any], metadata: dict[str, Any]) -> dict[str, int | None]:
    """source 값에 맞는 원천 테이블에 upsert하고 rag_chunks FK 값을 만든다."""
    fks: dict[str, int | None] = {
        "breed_section_id": None,
        "qna_id": None,
        "youtube_doc_id": None,
        "article_doc_id": None,
    }
    source = row["source"]
    if source == "akc_breed":
        fks["breed_section_id"] = upsert_breed_section(cur, row, metadata)
    elif source == "qna":
        fks["qna_id"] = upsert_qna(cur, row, metadata)
    elif source in {"youtube_training", "youtube_vet"}:
        fks["youtube_doc_id"] = upsert_youtube_doc(cur, row, metadata)
    elif source == "article":
        fks["article_doc_id"] = upsert_article_doc(cur, row, metadata)
    else:
        raise ValueError(f"Unsupported source: {source}")
    return fks


def create_vector_index(conn: psycopg.Connection, table: str) -> None:
    """cosine 검색용 HNSW index를 생성한다."""
    with conn.cursor() as cur:
        cur.execute(f"CREATE INDEX IF NOT EXISTS idx_{table}_embedding_hnsw ON {table} USING hnsw (embedding vector_cosine_ops)")
    conn.commit()


def main() -> None:
    parser = argparse.ArgumentParser(description="Build PostgreSQL pgvector ERD-friendly RAG tables")
    parser.add_argument("--base-dir", type=Path, default=Path(__file__).resolve().parents[2])
    parser.add_argument("--chunks-file", type=Path, default=None)
    parser.add_argument("--embedding-model", default=None)
    parser.add_argument("--embedding-dim", type=int, default=DEFAULT_EMBEDDING_DIM)
    parser.add_argument("--batch-size", type=int, default=DEFAULT_BATCH_SIZE)
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--reset", action="store_true")
    parser.add_argument("--max-retries", type=int, default=DEFAULT_MAX_RETRIES)
    parser.add_argument("--retry-sleep", type=float, default=DEFAULT_RETRY_SLEEP)
    args = parser.parse_args()

    base_dir = args.base_dir.resolve()
    load_dotenv(base_dir / ".env", encoding="utf-8-sig")

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY is empty. Fill it in the project .env file first.")

    table = validate_identifier(os.getenv("PGVECTOR_TABLE", "rag_chunks"))
    chunks_file = args.chunks_file or (base_dir / "database" / "chunks" / "all_chunks.jsonl")
    chunks_file = chunks_file.resolve()
    embedding_model = args.embedding_model or os.getenv("OPENAI_EMBEDDING_MODEL", "text-embedding-3-small")

    rows = load_chunks(chunks_file, limit=args.limit)
    if not rows:
        raise RuntimeError(f"No chunks loaded from {chunks_file}")

    if args.batch_size <= 0:
        raise ValueError("--batch-size must be greater than 0")
    if args.max_retries < 0:
        raise ValueError("--max-retries must be 0 or greater")
    if args.retry_sleep <= 0:
        raise ValueError("--retry-sleep must be greater than 0")

    embeddings = OpenAIEmbeddings(model=embedding_model, api_key=api_key)

    with psycopg.connect(**db_config()) as conn:
        ensure_schema(conn, table=table, dim=args.embedding_dim, reset=args.reset)

        if args.reset:
            print("Reset requested. Rebuilding tables from the first chunk.")
        else:
            existing_chunk_ids = load_existing_chunk_ids(conn, table)
            if existing_chunk_ids:
                before_count = len(rows)
                rows = [row for row in rows if row["chunk_id"] not in existing_chunk_ids]
                skipped_count = before_count - len(rows)
                print(f"Resume mode: skipped {skipped_count} chunks already stored in {table}.")
            if not rows:
                print(f"All chunks are already stored in {table}. Nothing to insert.")
                create_vector_index(conn, table)
                return

        insert_sql = f"""
            INSERT INTO {table} (
                chunk_id, doc_id, source,
                breed_section_id, qna_id, youtube_doc_id, article_doc_id,
                text, metadata, embedding
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s::vector)
            ON CONFLICT (chunk_id) DO UPDATE SET
                doc_id = EXCLUDED.doc_id,
                source = EXCLUDED.source,
                breed_section_id = EXCLUDED.breed_section_id,
                qna_id = EXCLUDED.qna_id,
                youtube_doc_id = EXCLUDED.youtube_doc_id,
                article_doc_id = EXCLUDED.article_doc_id,
                text = EXCLUDED.text,
                metadata = EXCLUDED.metadata,
                embedding = EXCLUDED.embedding
        """

        for start, batch in batched(rows, args.batch_size):
            texts = [row["text"] for row in batch]
            vectors = embed_documents_with_retry(
                embeddings,
                texts,
                max_retries=args.max_retries,
                retry_sleep=args.retry_sleep,
            )
            params = []
            with conn.cursor() as cur:
                for row, vector in zip(batch, vectors):
                    metadata = row_metadata(row)
                    fks = upsert_source_doc(cur, row, metadata)
                    params.append((
                        row["chunk_id"], row["doc_id"], row["source"],
                        fks["breed_section_id"], fks["qna_id"], fks["youtube_doc_id"], fks["article_doc_id"],
                        row["text"], Jsonb(metadata), vector_literal(vector),
                    ))
                cur.executemany(insert_sql, params)
            conn.commit()
            print(f"Inserted {min(start + len(batch), len(rows))}/{len(rows)} chunks")

        create_vector_index(conn, table)

    print(json.dumps({
        "chunks_file": str(chunks_file),
        "rag_table": table,
        "source_tables": ["breeds", "breed_sections", "qna_items", "youtube_docs", "article_docs"],
        "embedding_model": embedding_model,
        "embedding_dim": args.embedding_dim,
        "batch_size": args.batch_size,
        "inserted_chunks": len(rows),
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
