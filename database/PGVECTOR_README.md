# PostgreSQL + PGVector / 퀴즈 데이터 적재 가이드

## 목적

DBeaver에서 확인할 수 있는 PostgreSQL 데이터베이스에 RAG 검색용 벡터 스토어를 적재하고, Django `test` 페이지에서 사용하는 QnA 퀴즈 데이터를 생성한다.

현재 프로젝트의 최신 흐름은 두 갈래다.

```text
1. RAG 검색용 벡터 적재
   원본 문서 -> loader.py -> chunk 분할 -> OpenAI embedding -> PGVector 저장

2. 퀴즈 페이지용 데이터 생성
   원본 QnA JSONL -> build_qna_quiz_bank.py -> database/quiz/qna_quiz_bank.json
```

중요한 점은 `qna_quiz_bank.json`은 PostgreSQL 테이블에 적재하는 데이터가 아니라, Django 퀴즈 페이지가 직접 읽는 JSON 파일이라는 것이다.

## 현재 기준 파일

```text
docker-compose.yml
database/tools/build_vectorstore.py
database/tools/build_qna_quiz_bank.py
database/tools/loader.py
database/quiz/qna_quiz_bank.json
web/test/views.py
web/templates/main/test.html
database/PGVECTOR_README.md
```

예전 문서에 있던 `database/tools/build_pgvector_db.py`는 현재 프로젝트에 없다. 최신 벡터 적재 파일은 `database/tools/build_vectorstore.py`다.

## .env 설정

프로젝트 루트 `.env`에 아래 값들이 있어야 한다.

```text
OPENAI_API_KEY=...
OPENAI_EMBEDDING_MODEL=text-embedding-3-small
OPENAI_CHAT_MODEL=gpt-4o-mini

POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=pet_dog
POSTGRES_USER=admin
POSTGRES_PASSWORD=admin1234

PGVECTOR_COLLECTION=dog_rag_documents
```

`OPENAI_CHAT_MODEL`은 퀴즈 생성용 모델이다. 값이 없으면 `build_qna_quiz_bank.py` 기본값인 `gpt-4o-mini`를 사용한다.

## DBeaver 접속 정보

`docker-compose.yml` 기준 접속 정보는 다음과 같다.

```text
Host: localhost
Port: 5432
Database: pet_dog
Username: admin
Password: admin1234
```

컨테이너 이름은 다음과 같다.

```text
pet_dog
```

## 실행 순서

### 1. Docker PostgreSQL 실행

```powershell
docker compose up -d postgres
```

실행 확인:

```powershell
docker ps
```

## 2. RAG 벡터 데이터 적재

RAG 검색용 벡터 스토어는 `database/tools/build_vectorstore.py`로 적재한다.

처음부터 새로 만들 때만 `--reset`을 사용한다.

```powershell
.\.venv\Scripts\python.exe database\tools\build_vectorstore.py --reset
```

중간에 멈췄거나 이어서 넣고 싶다면 `--reset` 없이 실행한다.

```powershell
.\.venv\Scripts\python.exe database\tools\build_vectorstore.py
```

테스트로 일부 문서만 적재하려면 `--limit`을 사용한다.

```powershell
.\.venv\Scripts\python.exe database\tools\build_vectorstore.py --limit 20 --reset
```

OpenAI rate limit이 자주 발생하면 batch 크기를 줄인다.

```powershell
.\.venv\Scripts\python.exe database\tools\build_vectorstore.py --batch-size 25
```

기본 collection 이름은 다음과 같다.

```text
dog_rag_documents
```

DBeaver에서는 LangChain PGVector가 만든 아래 테이블을 확인하면 된다.

```text
langchain_pg_collection
langchain_pg_embedding
```

## 3. 퀴즈 데이터 생성

Django 퀴즈 페이지는 DB 테이블을 직접 조회하지 않고 아래 JSON 파일을 읽는다.

```text
database/quiz/qna_quiz_bank.json
```

따라서 퀴즈 데이터 최신화는 PostgreSQL 적재가 아니라 `qna_quiz_bank.json` 생성/갱신 작업이다.

### 권장 방식: loader 기반 생성

퀴즈는 기본적으로 원본 QnA JSONL에서 생성하는 것이 좋다.

이유:

```text
PGVector에는 청킹된 문서가 들어가므로 Answer가 중간에서 잘릴 수 있다.
퀴즈 정답/해설은 원문 전체가 중요하므로 loader 방식이 더 안전하다.
```

혼합 퀴즈 생성:

```powershell
.\.venv\Scripts\python.exe database\tools\build_qna_quiz_bank.py --source loader --quiz-mode mixed --limit 50 --preview 3
```

O/X 퀴즈만 생성:

```powershell
.\.venv\Scripts\python.exe database\tools\build_qna_quiz_bank.py --source loader --quiz-mode ox --limit 50 --preview 3
```

4지선다만 생성:

```powershell
.\.venv\Scripts\python.exe database\tools\build_qna_quiz_bank.py --source loader --quiz-mode multiple_choice --limit 50 --preview 3
```

원문 QnA 확인용으로만 생성:

```powershell
.\.venv\Scripts\python.exe database\tools\build_qna_quiz_bank.py --source loader --quiz-mode source --limit 10 --preview 3
```

생성 결과:

```text
database/quiz/qna_quiz_bank.json
```

### PGVector 기반 생성은 확인용

PGVector에 적재된 QnA chunk에서 퀴즈를 만들 수도 있다.

```powershell
.\.venv\Scripts\python.exe database\tools\build_qna_quiz_bank.py --source pgvector --collection-name dog_rag_documents --quiz-mode mixed --limit 50 --preview 3
```

다만 기본 추천 방식은 아니다. 퀴즈 생성은 원본 QnA를 읽는 `--source loader` 방식을 우선 사용한다.

## 4. Django 퀴즈 페이지 확인

퀴즈 페이지는 다음 파일을 읽는다.

```text
web/test/views.py
-> database/quiz/qna_quiz_bank.json
```

Django 실행 후 아래 URL에서 확인한다.

```text
http://127.0.0.1:8000/test/
```

퀴즈 페이지에서 랜덤으로 10문제를 보여준다.

```text
QUESTION_COUNT = 10
```

## 5. 적재/생성 결과 확인

### 퀴즈 JSON 개수 확인

```powershell
.\.venv\Scripts\python.exe -c "import json; data=json.load(open('database/quiz/qna_quiz_bank.json', encoding='utf-8')); print(len(data)); print(data[0].keys() if data else 'empty')"
```

### Django 시스템 체크

```powershell
.\.venv\Scripts\python.exe web\manage.py check
```

### PGVector collection 확인

```powershell
docker exec pet_dog psql -U admin -d pet_dog -c "SELECT * FROM langchain_pg_collection;"
```

embedding row 수 확인:

```powershell
docker exec pet_dog psql -U admin -d pet_dog -c "SELECT COUNT(*) FROM langchain_pg_embedding;"
```

## 핵심 요약

```text
RAG 검색용 벡터 적재:
-> database/tools/build_vectorstore.py
-> PostgreSQL PGVector
-> langchain_pg_collection / langchain_pg_embedding

퀴즈 데이터 생성:
-> database/tools/build_qna_quiz_bank.py
-> database/quiz/qna_quiz_bank.json
-> Django test 페이지가 직접 읽음

퀴즈는 DB 적재가 아니라 JSON 생성/갱신 작업
```

