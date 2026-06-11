# Merck Veterinary Manual Dog Owner RAG Data

## 목적

Merck Veterinary Manual의 Dog Owners 공개 페이지를 수집해서 챗봇 RAG 참고 자료로 사용하기 위한 데이터 파이프라인입니다.

대상 사이트:

```text
https://www.merckvetmanual.com/dog-owners
```

## 현재 방식

현재 프로젝트는 기존 YouTube/AKC RAG 적재 방식에 맞춰 Merck 원천 JSON을 직접 읽습니다.

```text
Merck Dog Owners URL 목록 수집
-> 각 페이지 본문을 raw JSON으로 저장
-> build_vectorstore.py가 raw JSON을 loader로 읽음
-> build_vectorstore.py 내부에서 chunk 분할
-> LangChain PGVector에 적재
```

따라서 별도의 `processed/merck_dog_owner_chunks.jsonl` 파일은 사용하지 않습니다.

## 폴더 구조

```text
database/merck_vet/
├─ README.md
├─ urls/
│  └─ dog_owner_urls.json
└─ raw/
   └─ *.json
```

## 생성/사용 스크립트

```text
database/tools/fetch_merck_dog_owner_urls.py
database/tools/crawl_merck_dog_owner_pages.py
database/tools/loader.py
database/tools/build_vectorstore.py
```

## 실행 순서

### 1. URL 목록 수집

```powershell
.\.venv\Scripts\python.exe database\tools\fetch_merck_dog_owner_urls.py --delay 5
```

결과:

```text
database/merck_vet/urls/dog_owner_urls.json
```

### 2. 본문 크롤링

처음 확인할 때는 5개만 테스트합니다.

```powershell
.\.venv\Scripts\python.exe database\tools\crawl_merck_dog_owner_pages.py --limit 5 --delay 5
```

전체 수집은 아래처럼 실행합니다.

```powershell
.\.venv\Scripts\python.exe database\tools\crawl_merck_dog_owner_pages.py --delay 5
```

이미 저장된 raw 파일은 기본적으로 다시 받지 않습니다. 다시 받고 싶으면 `--overwrite`를 붙입니다.

```powershell
.\.venv\Scripts\python.exe database\tools\crawl_merck_dog_owner_pages.py --delay 5 --overwrite
```

결과:

```text
database/merck_vet/raw/*.json
```

### 3. 벡터 DB 적재

Merck raw JSON은 `database/tools/loader.py`의 `get_merck_loader()`로 읽힙니다.
그 다음 `database/tools/build_vectorstore.py`에서 기존 문서들과 함께 chunk로 분할되고 PGVector에 적재됩니다.

```powershell
.\.venv\Scripts\python.exe database\tools\build_vectorstore.py --reset
```

주의: 이 단계는 OpenAI embedding API를 사용하므로 비용이 발생할 수 있습니다.

## raw JSON 구조

각 raw JSON은 대략 아래 필드를 가집니다.

```json
{
  "source": "merck_vet_manual",
  "scope": "dog-owners",
  "title": "Routine Health Care of Dogs",
  "url": "https://www.merckvetmanual.com/...",
  "category": "Routine Care of Dogs",
  "reviewed_date": "Jul 2025",
  "author": "...",
  "language": "en",
  "content": "본문 텍스트",
  "sections": [],
  "crawled_at": "2026-06-08"
}
```

## 주의 사항

- `robots.txt`의 `Crawl-delay: 5`를 지키기 위해 `--delay 5`를 사용합니다.
- Merck Veterinary Manual 콘텐츠는 저작권이 있는 자료입니다.
- 원문 전체를 서비스 화면에 그대로 노출하지 말고, 챗봇 답변에서는 요약과 출처 URL 중심으로 사용합니다.
- 의학 정보는 진단이나 처방처럼 단정하지 않습니다.
- 응급 증상이나 상태가 심한 경우 수의사 진료 안내 문구를 포함해야 합니다.

챗봇 답변 권장 문구:

```text
이 답변은 일반적인 건강 정보이며 진단이나 처방이 아닙니다. 증상이 지속되거나 상태가 심하면 수의사 진료를 받으세요.
```