# Chunks 산출물 정리

## 목적

이 폴더는 RAG/vector DB 구축에 사용할 수 있는 chunk 산출물을 보관한다.

현재 프로젝트에서 실제 벡터 적재는 아래 스크립트가 담당한다.

```text
database/tools/build_vectorstore.py
```

주의:

```text
예전 문서에 언급되던 database/tools/build_chunks.py는 현재 프로젝트에 없다.
현재 벡터 적재는 loader.py가 원본 문서를 읽고, build_vectorstore.py가 필요 시 문서를 분할한 뒤 PGVector에 저장하는 방식이다.
```

## 현재 남아 있는 주요 산출물

### all_chunks.jsonl

```text
database/chunks/all_chunks.jsonl
```

과거 청킹 작업으로 생성된 통합 chunk JSONL 파일이다.

기본 구조는 다음과 같다.

```json
{
  "chunk_id": "...",
  "doc_id": "...",
  "source": "akc_breed | qna | article | youtube_training | youtube_vet",
  "text": "임베딩할 실제 텍스트",
  "metadata": {
    "source_file": "...",
    "chunk_index": 0,
    "chunk_count": 1,
    "is_chunked": false,
    "text_length": 1234
  }
}
```

## 현재 벡터 적재 흐름

최신 흐름은 `all_chunks.jsonl`을 직접 읽는 방식이 아니라, `database/tools/loader.py`와 `database/tools/build_vectorstore.py`를 사용한다.

```text
원본 문서
-> database/tools/loader.py
-> database/tools/build_vectorstore.py
-> OpenAI embedding 생성
-> PostgreSQL PGVector 저장
```

실행 예:

```powershell
.\.venv\Scripts\python.exe database\tools\build_vectorstore.py --reset
```

테스트로 일부 문서만 적재:

```powershell
.\.venv\Scripts\python.exe database\tools\build_vectorstore.py --limit 20 --reset
```

rate limit이 있으면 batch 크기를 줄인다.

```powershell
.\.venv\Scripts\python.exe database\tools\build_vectorstore.py --batch-size 25
```

## build_vectorstore.py가 읽는 원본

`build_vectorstore.py`는 현재 아래 원본들을 loader로 읽는다.

```text
database/docs/akc_dog_info/akc_breed_info_vector_documents.json
database/docs/article_*.json
database/docs/youtube/youtube_basic_instruction.json
database/docs/youtube/youtube_vet_knowledge.json
database/docs/youtube_qna/final_seol_qna.jsonl
database/docs/youtube_qna/kang_qna.jsonl
```

## 퀴즈 데이터와의 관계

퀴즈 페이지는 이 폴더의 `all_chunks.jsonl`을 직접 사용하지 않는다.

Django 퀴즈 페이지는 아래 파일을 읽는다.

```text
database/quiz/qna_quiz_bank.json
```

퀴즈 데이터 생성은 아래 스크립트로 한다.

```powershell
.\.venv\Scripts\python.exe database\tools\build_qna_quiz_bank.py --source loader --quiz-mode mixed --limit 50 --preview 3
```

정리하면 다음과 같다.

```text
RAG 검색용 벡터 적재:
-> database/tools/build_vectorstore.py

퀴즈 문제 은행 생성:
-> database/tools/build_qna_quiz_bank.py

과거 chunk 산출물 확인:
-> database/chunks/all_chunks.jsonl
```

## 제거/주의 대상

아래 파일명은 현재 프로젝트 기준으로 사용하지 않는다.

```text
database/tools/build_chunks.py
```

만약 새로 chunk 산출물을 만드는 방식으로 되돌릴 계획이 없다면, 문서나 코드에서 이 파일을 실행하라고 안내하면 안 된다.
