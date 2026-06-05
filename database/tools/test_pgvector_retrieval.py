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
from langchain_openai import ChatOpenAI, OpenAIEmbeddings


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


def translate_query_for_english_docs(llm: ChatOpenAI, query: str) -> str:
    """한국어 질문을 AKC 영어 문서 검색에 유리한 영어 query로 보강한다.

    - 원본 질문 자체를 번역해서 DB를 다시 만들지는 않는다.
    - 검색 직전에만 영어 query를 만들어 영어 문서와의 embedding 매칭을 높인다.
    - 품종명, 증상, 행동, 훈련 의도를 짧은 영어 검색문으로 바꾼다.
    """
    prompt = (
        "Convert the user's Korean dog-related question into one concise English search query. "
        "Keep dog breed names, symptoms, behavior terms, and care intent. "
        "Return only the English query without quotes.\n\n"
        f"User question: {query}"
    )
    return str(llm.invoke(prompt).content).strip()


def build_answer(llm: ChatOpenAI, query: str, results: list[dict[str, Any]]) -> str:
    """검색 결과 chunk를 근거로 한국어 답변을 생성한다.

    - AKC처럼 영어 chunk가 검색되어도 최종 답변은 한국어로 작성한다.
    - 검색 결과에 없는 내용은 단정하지 않게 한다.
    - 건강/수의학 관련 질문은 병원 상담 권고를 포함하도록 한다.
    """
    context_blocks = []
    for item in results:
        context_blocks.append(
            "\n".join([
                f"[rank {item['rank']}]",
                f"source: {item.get('source')}",
                f"title: {item.get('title')}",
                f"breed_name: {item.get('breed_name')}",
                f"url: {item.get('article_url')}",
                f"text: {item.get('preview')}",
            ])
        )
    context = "\n\n".join(context_blocks)
    prompt = (
        "You are a helpful Korean dog-care assistant. Answer in Korean. "
        "Use only the retrieved context below. If the context is in English, translate and summarize it naturally in Korean. "
        "If the evidence is weak, say that the retrieved data is limited. "
        "For medical or emergency topics, recommend consulting a veterinarian.\n\n"
        f"User question:\n{query}\n\n"
        f"Retrieved context:\n{context}"
    )
    return str(llm.invoke(prompt).content).strip()


def search_chunks(
    conn: psycopg.Connection,
    table: str,
    query_vector: str,
    k: int,
    source: str | None,
) -> list[dict[str, Any]]:
    """query vector로 pgvector cosine 검색을 수행하고 출력용 dict를 반환한다."""
    where_sql = "WHERE r.source = %s" if source else ""
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
    if source:
        params = [query_vector, source, query_vector, k]
    else:
        params = [query_vector, query_vector, k]

    with conn.cursor() as cur:
        cur.execute(sql, params)
        rows = cur.fetchall()

    results = []
    for rank, row in enumerate(rows, start=1):
        (
            chunk_id, doc_id, row_source, metadata, preview, similarity,
            breed_name, breed_section_title, qna_question, youtube_title,
            article_title, article_url,
        ) = row
        title = article_title or youtube_title or breed_section_title or qna_question
        results.append({
            "rank": rank,
            "similarity": float(similarity),
            "source": row_source,
            "source_file": metadata.get("source_file") if isinstance(metadata, dict) else None,
            "doc_id": doc_id,
            "chunk_id": chunk_id,
            "title": title,
            "breed_name": breed_name,
            "article_url": article_url,
            "preview": preview,
        })
    return results


def merge_results(*result_groups: list[dict[str, Any]], k: int) -> list[dict[str, Any]]:
    """원본 query 검색 결과와 번역 query 검색 결과를 chunk_id 기준으로 합친다."""
    merged: dict[str, dict[str, Any]] = {}
    for group in result_groups:
        for item in group:
            chunk_id = item["chunk_id"]
            if chunk_id not in merged or item["similarity"] > merged[chunk_id]["similarity"]:
                merged[chunk_id] = item
    sorted_results = sorted(merged.values(), key=lambda item: item["similarity"], reverse=True)[:k]
    for rank, item in enumerate(sorted_results, start=1):
        item["rank"] = rank
    return sorted_results


def main() -> None:
    parser = argparse.ArgumentParser(description="Search PostgreSQL pgvector table")
    parser.add_argument("--base-dir", type=Path, default=Path(__file__).resolve().parents[2])
    parser.add_argument("--query", required=True)
    parser.add_argument("--k", type=int, default=5)
    parser.add_argument("--source", default=None)
    parser.add_argument("--embedding-model", default=None)
    parser.add_argument("--chat-model", default=None)
    parser.add_argument("--translate-query", action="store_true")
    parser.add_argument("--answer", action="store_true")
    args = parser.parse_args()

    base_dir = args.base_dir.resolve()
    load_dotenv(base_dir / ".env", encoding="utf-8-sig")

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY is empty. Fill it in the project .env file first.")

    table = validate_identifier(os.getenv("PGVECTOR_TABLE", "rag_chunks"))
    embedding_model = args.embedding_model or os.getenv("OPENAI_EMBEDDING_MODEL", "text-embedding-3-small")
    embeddings = OpenAIEmbeddings(model=embedding_model, api_key=api_key)

    chat_model = args.chat_model or os.getenv("OPENAI_CHAT_MODEL", "gpt-4o-mini")
    llm = ChatOpenAI(model=chat_model, api_key=api_key, temperature=0) if (args.translate_query or args.answer) else None

    search_query = args.query
    translated_query = None
    if args.translate_query:
        if llm is None:
            raise RuntimeError("Chat model is required for --translate-query")
        translated_query = translate_query_for_english_docs(llm, args.query)
        search_query = translated_query

    query_vector = vector_literal(embeddings.embed_query(search_query))

    with psycopg.connect(**db_config()) as conn:
        results = search_chunks(conn, table, query_vector, args.k, args.source)

        if args.translate_query and translated_query:
            original_query_vector = vector_literal(embeddings.embed_query(args.query))
            original_results = search_chunks(conn, table, original_query_vector, args.k, args.source)
            results = merge_results(results, original_results, k=args.k)

    answer = None
    if args.answer:
        if llm is None:
            raise RuntimeError("Chat model is required for --answer")
        answer = build_answer(llm, args.query, results)

    output = {
        "query": args.query,
        "search_query": search_query,
        "translated_query": translated_query,
        "k": args.k,
        "source_filter": args.source,
        "table": table,
        "results": results,
    }
    if answer is not None:
        output["answer_ko"] = answer

    print(json.dumps(output, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
