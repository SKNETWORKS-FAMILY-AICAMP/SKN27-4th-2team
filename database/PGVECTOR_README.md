# PostgreSQL + pgvector 적재 가이드

## 목적

DBeaver에서 확인할 수 있는 PostgreSQL 데이터베이스에 원천 데이터 테이블과 RAG 검색용 embedding index를 함께 적재한다.

핵심 설계는 다음과 같다.

```text
원천 데이터는 source별 테이블로 분리한다.
검색 효율을 위해 chunk/embedding만 rag_chunks에 통합한다.
```

즉, `rag_chunks`는 원천 데이터를 대체하는 테이블이 아니라 검색을 위한 임베딩 인덱스 테이블이다.

## 전체 흐름

```text
Docker로 PostgreSQL(pgvector) 실행
↓
all_chunks.jsonl 읽기
↓
source별 원천 테이블 적재
↓
OpenAI embedding 생성
↓
rag_chunks에 text + embedding + FK 저장
```

## 생성된 파일

```text
docker-compose.yml
database/tools/build_pgvector_db.py
database/tools/test_pgvector_retrieval.py
database/PGVECTOR_README.md
```

## .env 설정

프로젝트 루트의 `.env`에 아래 값들이 있어야 한다.

```text
OPENAI_API_KEY=...
OPENAI_EMBEDDING_MODEL=text-embedding-3-small
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=dog_rag
POSTGRES_USER=dog_user
POSTGRES_PASSWORD=dog_password
PGVECTOR_TABLE=rag_chunks
```

## DBeaver 접속 정보

```text
Host: localhost
Port: 5432
Database: dog_rag
Username: dog_user
Password: dog_password
```

## 실행 순서

### 1. Docker PostgreSQL 실행

```powershell
docker compose up -d postgres
```

### 2. 적재

처음부터 테이블을 새로 만들 때만 `--reset`을 사용한다.

```powershell
.\.venv\Scripts\python.exe database\tools\build_pgvector_db.py --reset
```

OpenAI rate limit 등으로 중간에 멈췄다면, 다시 `--reset`을 붙이지 말고 아래처럼 실행한다.
이미 저장된 `chunk_id`는 건너뛰고 남은 chunk부터 이어서 적재한다.

```powershell
.\.venv\Scripts\python.exe database\tools\build_pgvector_db.py
```

rate limit이 자주 발생하면 batch 크기를 더 줄여 실행한다.

```powershell
.\.venv\Scripts\python.exe database\tools\build_pgvector_db.py --batch-size 25
```

