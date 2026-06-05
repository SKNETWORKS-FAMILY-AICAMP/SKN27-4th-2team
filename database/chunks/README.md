# Chunks 산출물 정리

## 작업 목적

RAG/vector DB 구축에 사용할 수 있도록 하나의 공통 chunk 형식으로 통합한 결과를 보관

- 서로 다른 구조의 JSON/JSONL 파일을 하나의 schema로 통일
- 긴 문서만 청킹하고, 이미 적절히 짧은 문서는 원문 단위로 유지
- 벡터DB 저장 시 사용할 수 있도록 `chunk_id`를 중복 없이 생성
- 동일 텍스트 중복은 임의로 삭제하지 않고 리포트에만 기록
- 이후 embedding -> vector DB 저장 -> 검색 테스트 단계에서 바로 사용할 최종 입력 파일 생성 예정

## 생성된 파일

### 1. 최종 청킹 파일

```text
SKN27-4th-2team\database\chunks\all_chunks.jsonl
```

- 벡터DB 저장 단계에서 직접 읽을 파일
- JSONL 형식이라 한 줄에 chunk 하나가 들어 있음
- 총 20,550개 chunk가 들어 있음
- `chunk_id` 중복은 0개로 검증 완료

각 줄의 기본 구조는 다음과 같다.

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

### 2. 청킹 결과 리포트

```text
SKN27-4th-2team\database\chunks\chunk_build_report.json
```

이 파일은 청킹 결과를 검증하기 위한 요약 리포트

현재 최종 결과는 다음과 같다.

```text
총 chunk 수: 20,550
chunk_id 중복: 0
동일 텍스트 중복 기록: 415
max_chars: 2,600
overlap_chars: 250
```

source별 원본 문서 수

```text
akc_breed: 2,885
article: 14,982
qna: 280
youtube_training: 140
youtube_vet: 97
```

source별 최종 chunk 수

```text
akc_breed: 2,898
article: 17,049
qna: 342
youtube_training: 142
youtube_vet: 119
```

실제로 2개 이상 chunk로 분할된 문서 수

```text
akc_breed: 7
article: 1,639
youtube_training: 2
youtube_vet: 22
```

## build_chunks.py

```text
SKN27-4th-2team\database\tools\build_chunks.py
```

 `all_chunks.jsonl`과 `chunk_build_report.json`을 생성

주요 역할은 다음과 같다.

- AKC 품종 문서 읽기
- 강형욱/설채현 QnA JSONL 읽기
- `database/docs/article_*.json` 전체 읽기
- YouTube 기초교육/수의학 JSON 읽기
- 모든 문서를 공통 chunk schema로 변환
- 긴 문서만 `max_chars=2600`, `overlap_chars=250` 기준으로 분할
- `chunk_id`를 고유하게 생성
- 동일 텍스트 중복 수를 리포트에 기록


### AKC 품종 정보

```text
database\akc\preprocessed\akc_breed_info_vector_documents.json
```

- 이미 section 단위로 잘게 정리되어 있어 대부분 그대로 chunk로 사용

### QnA

```text
database\youtube\processed\kang_qna.jsonl
database\youtube\processed\seol_qna.jsonl
```

- `question`, `answer` 필드를 합쳐서 하나의 chunk로 만들었다.

### YouTube 기초교육/수의학

```text
database\docs\youtube_basic_instruction.json
database\docs\youtube_vet_knowledge.json
```

- `full_text_for_embedding`이 있으면 우선 사용하고, 없으면 `content`를 사용

### AKC article 자료

```text
database\docs\article_*.json
```

- `article_dog-breeds.json`, `article_health.json`, `article_training.json` 등 article 전체를 포함
- 이번 작업에서는 2차 확장 대상으로 모두 포함
- `full_text_for_embedding`이 있으면 우선 사용하고, 없으면 `content`를 사용


## chunk_id 중복 처리 방식

초기 검증에서 `chunk_id` 중복이 발견. 원인은 일부 article 데이터에 같은 `doc_id`, 같은 text, 같은 chunk index를 가진 문서 조각이 반복되었기 때문이다.

최종적으로는 `chunk_id`에 저장 순번을 포함해 중복을 제거

* 현재 `chunk_id` 구성 방식

```text
source + doc_id 일부 + 저장 순번 + 해시 + chunk index
```

- 같은 텍스트가 반복되어도 chunk_id는 고유화
- 벡터DB 저장 시 ID 충돌이 발생하지 않음 
- 원본 문서 ID와 source 정보도 어느 정도 눈으로 확인할 수 있다.
