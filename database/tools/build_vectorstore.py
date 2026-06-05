"""Build PostgreSQL PGVector vector store for RAG.

실행 흐름:
1. 문서 로드(loader.py)
2. 문서 분할(필요하면)
3. 임베딩
   3-1. 임베딩 모델 선언
4. PGVector 벡터 스토어 저장

저장 방식:
- LangChain의 PGVector.from_documents() 사용
- collection_name 기준으로 LangChain 관리 테이블 자동 생성
- DBeaver에서 langchain_pg_collection, langchain_pg_embedding 확인 가능
"""

from __future__ import annotations

import argparse
import os
from pathlib import Path

import psycopg
from dotenv import load_dotenv
from langchain_core.documents import Document
from langchain_openai import OpenAIEmbeddings
from langchain_postgres import PGVector
from langchain_text_splitters import RecursiveCharacterTextSplitter

from loader import (
    get_article_loader,
    get_dog_info_loader,
    get_qna_loader,
    get_youtube_loader,
)

# - DATABASE_DIR: database 폴더 경로
# - PROJECT_DIR: 프로젝트 루트 경로
# - DEFAULT_COLLECTION_NAME: PGVector collection 기본 이름
DATABASE_DIR = Path(__file__).resolve().parents[1]
PROJECT_DIR = DATABASE_DIR.parent
DEFAULT_COLLECTION_NAME = "dog_rag_documents"
DEFAULT_EMBEDDING_MODEL = "text-embedding-3-small"
DEFAULT_CHUNK_SIZE = 1000
DEFAULT_CHUNK_OVERLAP = 150


# 1. 문서 로드(loader.py)
def load_documents(limit: int | None = None) -> list[Document]:
    """loader.py에 정의된 loader들로 원본 파일을 Document로 변환한다.

    - loader.py는 파일 하나를 읽는 방법만 정의한다.
    - build_vectorstore.py는 실제로 어떤 파일들을 읽을지 결정한다.
    - article 파일은 여러 개라서 article_*.json을 for문으로 반복 처리한다.
    - QnA/YouTube/AKC는 파일 수가 정해져 있어 직접 경로를 지정한다.
    """
    loaders = [
        get_dog_info_loader(
            str(DATABASE_DIR / "akc" / "preprocessed" / "akc_breed_info_vector_documents.json")
        ),
    ]

    # - Article 문서 전체 로드
    # - database/docs/article_*.json 전체를 자동으로 찾는다.
    for article_path in sorted((DATABASE_DIR / "docs").glob("article_*.json")):
        loaders.append(get_article_loader(str(article_path)))

    # - YouTube/QnA 문서 로드
    # - QnA는 qna_source 값으로 설채현/강형욱 metadata를 구분한다.
    loaders.extend(
        [
            get_youtube_loader(str(DATABASE_DIR / "docs" / "youtube_basic_instruction.json")),
            get_youtube_loader(str(DATABASE_DIR / "docs" / "youtube_vet_knowledge.json")),
            get_qna_loader(
                str(DATABASE_DIR / "youtube" / "processed" / "final_seol_qna.jsonl"),
                "final_seol_qna",
            ),
            get_qna_loader(
                str(DATABASE_DIR / "youtube" / "processed" / "kang_qna.jsonl"),
                "kang_qna",
            ),
        ]
    )

    documents: list[Document] = []
    for loader in loaders:
        loaded = loader.load()
        documents.extend(loaded)
        print(f"loaded {len(loaded):>5} docs from {loader.file_path}")

        # - limit은 테스트용 옵션이다.
        # - 전체 적재 전 일부 문서만 빠르게 확인할 때 사용한다.
        if limit is not None and len(documents) >= limit:
            return documents[:limit]

    return documents


# 2. 문서 분할(필요하면)
def split_documents(
    documents: list[Document],
    chunk_size: int,
    chunk_overlap: int,
) -> list[Document]:
    """긴 문서를 chunk 단위로 나눈다.

    - chunk_size: chunk 하나의 최대 문자 길이 기준
    - chunk_overlap: 앞뒤 chunk가 겹치는 문자 수
    - 짧은 문서는 거의 그대로 유지된다.
    - 긴 article/YouTube 문서는 여러 chunk로 나뉠 수 있다.
    """
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
    )
    return splitter.split_documents(documents)


# 3. 임베딩
# 3-1. 임베딩 모델 선언
def create_embedding_model(model_name: str, api_key: str) -> OpenAIEmbeddings:
    """OpenAI embedding 모델을 생성한다.

    - 기본 모델은 text-embedding-3-small이다.
    - .env의 OPENAI_API_KEY를 사용한다.
    - 실제 embedding 생성은 PGVector.from_documents() 호출 시 일어난다.
    """
    return OpenAIEmbeddings(model=model_name, api_key=api_key)


def get_connection_string() -> str:
    """LangChain PGVector가 사용할 PostgreSQL 연결 문자열을 만든다.

    - docker-compose.yml 기본값과 맞춘다.
    - 팀 Docker 설정 기본값:
      - DB: pet_dog
      - USER: admin
      - PASSWORD: admin1234
    """
    host = os.getenv("POSTGRES_HOST", "localhost")
    port = os.getenv("POSTGRES_PORT", "5432")
    db = os.getenv("POSTGRES_DB", "pet_dog")
    user = os.getenv("POSTGRES_USER", "admin")
    password = os.getenv("POSTGRES_PASSWORD", "admin1234")
    return f"postgresql+psycopg://{user}:{password}@{host}:{port}/{db}"


def ensure_pgvector_extension() -> None:
    """PostgreSQL에 pgvector extension을 활성화한다.

    - PGVector.from_documents() 실행 전 vector extension이 필요하다.
    - 이미 생성되어 있으면 아무 작업도 하지 않는다.
    """
    host = os.getenv("POSTGRES_HOST", "localhost")
    port = int(os.getenv("POSTGRES_PORT", "5432"))
    db = os.getenv("POSTGRES_DB", "pet_dog")
    user = os.getenv("POSTGRES_USER", "admin")
    password = os.getenv("POSTGRES_PASSWORD", "admin1234")

    with psycopg.connect(host=host, port=port, dbname=db, user=user, password=password) as conn:
        with conn.cursor() as cur:
            cur.execute("CREATE EXTENSION IF NOT EXISTS vector")
        conn.commit()


# 4. PGVector 벡터 스토어 저장
def batch_documents(documents, batch_size):
    for start in range(0, len(documents), batch_size):
        yield start, documents[start : start + batch_size]


def save_vectorstore(
    chunks,
    embedding_model,
    connection_string,
    collection_name,
    reset,
    batch_size=500,
):
    vectorstore = None

    for start, batch in batch_documents(chunks, batch_size):
        is_first_batch = start == 0

        if is_first_batch:
            vectorstore = PGVector.from_documents(
                documents=batch,
                embedding=embedding_model,
                connection=connection_string,
                collection_name=collection_name,
                distance_strategy="cosine",
                pre_delete_collection=reset,
                use_jsonb=True,
            )
        else:
            vectorstore.add_documents(batch)

        end = min(start + len(batch), len(chunks))
        print(f"inserted {end}/{len(chunks)} chunks")

    if vectorstore is None:
        raise RuntimeError("No chunks to save.")

    return vectorstore

def build_vectorstore(args: argparse.Namespace) -> None:
    """전체 PGVector 적재 파이프라인을 실행한다.

    - .env 로드
    - 문서 로드
    - 문서 청킹
    - 임베딩 모델 준비
    - pgvector extension 준비
    - PGVector.from_documents()로 저장
    """
    load_dotenv(PROJECT_DIR / ".env", override=True, encoding="utf-8-sig")

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY is empty. Fill it in the project .env file first.")

    documents = load_documents(limit=args.limit)
    print(f"total source documents: {len(documents)}")

    chunks = split_documents(
        documents=documents,
        chunk_size=args.chunk_size,
        chunk_overlap=args.chunk_overlap,
    )
    print(f"total chunks: {len(chunks)}")

    embedding_model = create_embedding_model(args.embedding_model, api_key=api_key)
    connection_string = get_connection_string()

    ensure_pgvector_extension()

    vectorstore = save_vectorstore(
        chunks=chunks,
        embedding_model=embedding_model,
        connection_string=connection_string,
        collection_name=args.collection_name,
        reset=args.reset,
        batch_size=args.batch_size,
    )

    print(
        {
            "collection_name": args.collection_name,
            "source_documents": len(documents),
            "chunks": len(chunks),
            "embedding_model": args.embedding_model,
            "tables": ["langchain_pg_collection", "langchain_pg_embedding"],
            "vectorstore": type(vectorstore).__name__,
        }
    )


def parse_args() -> argparse.Namespace:
    """명령행 옵션을 정의한다.

    - --reset: 기존 collection 삭제 후 재생성
    - --limit: 테스트용으로 일부 문서만 적재
    - --collection-name: PGVector collection 이름
    - --chunk-size: chunk 크기 조정
    - --chunk-overlap: chunk 겹침 크기 조정
    """
    parser = argparse.ArgumentParser(description="Build LangChain PGVector store for dog RAG documents.")
    parser.add_argument("--collection-name", default=os.getenv("PGVECTOR_COLLECTION", DEFAULT_COLLECTION_NAME))
    parser.add_argument("--embedding-model", default=os.getenv("OPENAI_EMBEDDING_MODEL", DEFAULT_EMBEDDING_MODEL))
    parser.add_argument("--chunk-size", type=int, default=DEFAULT_CHUNK_SIZE)
    parser.add_argument("--chunk-overlap", type=int, default=DEFAULT_CHUNK_OVERLAP)
    parser.add_argument("--limit", type=int, default=None, help="테스트용으로 앞 N개 원본 문서만 로드한다.")
    parser.add_argument("--reset", action="store_true", help="기존 PGVector collection을 삭제하고 다시 만든다.")
    parser.add_argument("--batch-size", type=int, default=50, help="한 번에 저장할 문서 수")
    return parser.parse_args()


if __name__ == "__main__":
    build_vectorstore(parse_args())
