import argparse
from pathlib import Path

import os
from dotenv import load_dotenv

load_dotenv()

def get_database_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--json", type=Path, default="../../contents/dog_breed_dictionary_ko.json")
    parser.add_argument("--json", type=Path, default="../../contents/dog_api/dogapi_akc_matched_breeds_ko.json")
    parser.add_argument("--truncate", action="store_true")

    return parser.parse_args()

def get_vectorstore_args() -> argparse.Namespace:
    """명령행 옵션을 정의한다.

    - --reset: 기존 collection 삭제 후 재생성
    - --limit: 테스트용으로 일부 문서만 적재
    - --collection-name: PGVector collection 이름
    - --chunk-size: chunk 크기 조정
    - --chunk-overlap: chunk 겹침 크기 조정
    """
    parser = argparse.ArgumentParser(description="Build LangChain PGVector store for dog RAG documents.")
    parser.add_argument("--collection-name", default=os.getenv("PGVECTOR_COLLECTION", "dog_rag_documents"))
    parser.add_argument("--embedding-model", default=os.getenv("OPENAI_EMBEDDING_MODEL", "text-embedding-3-small"))
    parser.add_argument("--chunk-size", type=int, default=1000)
    parser.add_argument("--chunk-overlap", type=int, default=150)
    parser.add_argument("--limit", type=int, default=None, help="테스트용으로 앞 N개 원본 문서만 로드한다.")
    parser.add_argument("--reset", action="store_true", help="기존 PGVector collection을 삭제하고 다시 만든다.")
    parser.add_argument("--batch-size", type=int, default=50, help="한 번에 저장할 문서 수")

    return parser.parse_args()