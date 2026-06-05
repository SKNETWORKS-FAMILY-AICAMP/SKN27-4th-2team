"""Unified chunk builder for the dog knowledge RAG corpus.

- 목적:
  - 여러 JSON/JSONL 산출물을 하나의 공통 chunk schema로 통합한다.
  - 긴 문서만 문단 기준으로 나누고, 짧은 문서는 원문 단위 그대로 유지
  - 벡터DB 저장 시 사용할 수 있도록 chunk_id를 고유하게 생성
  - 동일 텍스트는 삭제하지 않고 리포트에 duplicate_text_count로만 기록

- 최종 산출물:
  - database/chunks/all_chunks.jsonl: 벡터DB 입력용 최종 chunk 파일
  - database/chunks/chunk_build_report.json: 청킹 결과 요약 리포트
"""

from __future__ import annotations

import argparse, hashlib, json, re
from collections import Counter
from pathlib import Path
from typing import Any

# - max_chars: 한 chunk의 최대 문자 수 기준
# - overlap: 긴 문서를 창 단위로 자를 때 앞 chunk와 겹치게 둘 문자 수
# - 현재는 토큰 계산 라이브러리 없이 문자 수 기준으로 안정적으로 처리
MAX_CHARS = 2600
OVERLAP = 250


def jload(p: Path):
    """JSON 배열 파일을 읽는다.

    - 대상 파일:
      - database/docs/article_*.json
      - database/docs/youtube_basic_instruction.json
      - database/docs/youtube_vet_knowledge.json
      - database/akc/preprocessed/akc_breed_info_vector_documents.json
    - 전제:
      - 파일 최상위 구조는 list[dict] 형태다.
    """
    with p.open('r', encoding='utf-8') as f:
        return json.load(f)


def jl_load(p: Path):
    """JSONL 파일을 한 줄씩 읽어서 dict 목록으로 반환

    - 대상 파일:
      - database/youtube/processed/kang_qna.jsonl
      - database/youtube/processed/seol_qna.jsonl
    - 빈 줄은 건너뛴다.
    """
    rows = []
    with p.open('r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def text(v: Any) -> str:
    """텍스트를 청킹 전에 정규화

    - None은 빈 문자열로 처리한다.
    - Windows 줄바꿈과 Mac 줄바꿈을 \n으로 통일한다.
    - 탭/연속 공백을 단일 공백으로 줄인다.
    - 3개 이상 연속 줄바꿈은 문단 구분용 2개 줄바꿈으로 줄인다.
    """
    s = '' if v is None else str(v)
    s = s.replace('\r\n', '\n').replace('\r', '\n')
    s = re.sub(r'[ \t]+', ' ', s)
    return re.sub(r'\n{3,}', '\n\n', s).strip()


def h(*xs) -> str:
    """chunk_id 보조용 짧은 해시 생성

    - source, source_file, doc_id, chunk_index, chunk text 등을 섞어 해시화
    - 길고 복잡한 원본 ID를 짧게 식별하기 위해 사용
    - 최종 chunk_id에는 저장 순번도 포함되므로 완전히 같은 텍스트가 반복되어도 ID는 고유
    """
    m = hashlib.sha1()
    for x in xs:
        m.update(str(x).encode('utf-8', 'ignore')); m.update(b'|')
    return m.hexdigest()[:12]


def slug(s: Any, n=80) -> str:
    """ID에 넣기 쉬운 짧은 문자열로 바꾼다.

    - 공백/특수문자는 _로 치환한다.
    - 한글, 영문, 숫자, _, -는 유지한다.
    - 너무 긴 문자열은 n자까지만 남긴다.
    """
    s = re.sub(r'[^0-9a-zA-Z가-힣_-]+', '_', str(s or '').lower()).strip('_')
    return (s or 'doc')[:n]


def meta(d: dict[str, Any]) -> dict[str, Any]:
    """벡터DB metadata로 넣을 수 있게 값을 정리한다.

    - None 값은 제거한다.
    - metadata key는 영문/숫자/_ 중심으로 정리한다.
    - 문자열/숫자/bool은 그대로 둔다.
    - list/dict 같은 복합 타입은 JSON 문자열로 저장한다.
    """
    out = {}
    for k, v in d.items():
        if v is None:
            continue
        k = re.sub(r'[^0-9a-zA-Z_]+', '_', str(k)).strip('_') or 'field'
        out[k] = v if isinstance(v, (str, int, float, bool)) else json.dumps(v, ensure_ascii=False, sort_keys=True)
    return out


def split(t: str, max_chars=MAX_CHARS, overlap=OVERLAP) -> list[str]:
    """긴 텍스트만 chunk로 나눈다.

    - max_chars 이하 문서는 그대로 1개 chunk로 유지한다.
    - max_chars 초과 문서는 문단 단위로 먼저 묶는다.
    - 문단 하나가 너무 길면 문자 창 기준으로 나누고 overlap을 둔다.
    - 이 방식은 article/youtube 긴 본문에 주로 적용된다.
    """
    t = text(t)
    if not t:
        return []
    if len(t) <= max_chars:
        return [t]
    chunks, cur = [], ''
    for p in [x.strip() for x in re.split(r'\n\s*\n', t) if x.strip()]:
        if len(p) > max_chars:
            if cur:
                chunks.append(cur); cur = ''
            start = 0
            while start < len(p):
                end = min(start + max_chars, len(p))
                chunks.append(p[start:end].strip())
                if end >= len(p): break
                start = max(0, end - overlap)
        else:
            cand = p if not cur else cur + '\n\n' + p
            if len(cand) <= max_chars:
                cur = cand
            else:
                chunks.append(cur); cur = p
    if cur:
        chunks.append(cur)
    return [c for c in chunks if c]


def add(rows, doc_id, source, body, md, max_chars, overlap):
    """하나의 원본 문서를 공통 chunk schema로 변환해 rows에 추가한다.

    - 입력:
      - doc_id: 원본 문서 식별자
      - source: akc_breed, qna, article, youtube_training, youtube_vet 중 하나
      - body: 실제 임베딩 대상 텍스트
      - md: 원본 추적용 metadata
    - chunk_id:
      - source + doc_id 일부 + 저장 순번 + 해시 + chunk index로 구성한다.
      - 저장 순번(seq)을 포함하므로 동일 텍스트가 반복되어도 chunk_id는 중복되지 않는다.
    - metadata:
      - chunk_index, chunk_count, is_chunked, text_length를 추가한다.
    """
    parts = split(body, max_chars, overlap)
    for i, part in enumerate(parts):
        seq = len(rows)
        cid = f"{slug(source)}_{slug(doc_id, 50)}_{seq:06d}_{h(source, md.get('source_file'), doc_id, i, part)}_chunk_{i:03d}"
        if len(cid) > 180:
            cid = f"{slug(source, 40)}_{seq:06d}_{h(source, md.get('source_file'), doc_id, i, part)}_chunk_{i:03d}"
        rows.append({
            'chunk_id': cid,
            'doc_id': doc_id,
            'source': source,
            'text': part,
            'metadata': meta({**md, 'chunk_index': i, 'chunk_count': len(parts), 'is_chunked': len(parts) > 1, 'text_length': len(part)})
        })


def build(base: Path, max_chars: int, overlap: int):
    """전체 전처리 산출물을 읽어 최종 chunk 목록과 리포트를 만든다.

    - 처리 순서:
      - AKC 품종 벡터 문서
      - 강형욱/설채현 QnA JSONL
      - database/docs/article_*.json 전체
      - youtube_basic_instruction.json, youtube_vet_knowledge.json
    - duplicate_text_count:
      - 동일 source 안에서 같은 text가 반복된 횟수다.
      - 데이터는 삭제하지 않고, 품질 점검용 리포트 숫자로만 남긴다.
    """
    rows = []
    docs = Counter()
    chunked = Counter()

    # - AKC 품종 정보는 이미 section 단위로 전처리된 벡터 문서다.
    # - breed/section 정보를 text와 metadata 양쪽에 보존한다.
    akc = base/'database'/'akc'/'preprocessed'/'akc_breed_info_vector_documents.json'
    if akc.exists():
        for r in jload(akc):
            body = text(f"Breed: {r.get('breed_name','')}\nSection: {r.get('section_title') or r.get('section','')}\n\n{r.get('content','')}")
            if not body: continue
            before = len(rows)
            add(rows, str(r.get('doc_id') or h(r)), 'akc_breed', body, {'source_file': akc.name, **(r.get('metadata') or {}), 'doc_type': r.get('doc_type'), 'breed_name': r.get('breed_name'), 'section': r.get('section'), 'section_title': r.get('section_title')}, max_chars, overlap)
            docs['akc_breed'] += 1
            if len(rows) - before > 1: chunked['akc_breed'] += 1

    # - QnA는 question + answer 한 쌍을 하나의 chunk로 유지한다.
    # - 질문 문구를 metadata에도 남겨 추후 검색 결과 확인에 쓰기 좋게 한다.
    for name in ['kang_qna', 'seol_qna']:
        p = base/'database'/'youtube'/'processed'/f'{name}.jsonl'
        if not p.exists(): continue
        for i, r in enumerate(jl_load(p)):
            q, a = text(r.get('question')), text(r.get('answer'))
            if not q or not a: continue
            add(rows, f'{name}:{i:04d}:{h(q,a)}', 'qna', f'Question: {q}\nAnswer: {a}', {'source_file': p.name, 'qna_source': name, 'question': q, 'doc_type': 'qna'}, max_chars, overlap)
            docs['qna'] += 1

    # - article_*.json은 2차 확장 대상 전체다.
    # - full_text_for_embedding이 있으면 우선 사용하고, 없으면 content를 사용한다.
    docs_dir = base/'database'/'docs'
    for p in sorted(docs_dir.glob('article_*.json')) if docs_dir.exists() else []:
        cat = p.stem.replace('article_', '')
        for r in jload(p):
            body = text(r.get('full_text_for_embedding') or r.get('content'))
            if not body: continue
            before = len(rows)
            add(rows, str(r.get('id') or h(p.name, body)), 'article', body, {'source_file': p.name, 'source_category': cat, 'doc_type': 'article', **(r.get('metadata') or {})}, max_chars, overlap)
            docs['article'] += 1
            if len(rows) - before > 1: chunked['article'] += 1

    # - YouTube 기초교육/수의학 문서는 article과 별도 source로 구분한다.
    # - 향후 검색 필터에서 훈련/수의학 출처를 분리하기 위함이다.
    for source, fname in [('youtube_training','youtube_basic_instruction.json'), ('youtube_vet','youtube_vet_knowledge.json')]:
        p = docs_dir/fname
        if not p.exists(): continue
        for r in jload(p):
            body = text(r.get('full_text_for_embedding') or r.get('content'))
            if not body: continue
            before = len(rows)
            add(rows, str(r.get('id') or h(p.name, body)), source, body, {'source_file': p.name, 'doc_type': source, **(r.get('metadata') or {})}, max_chars, overlap)
            docs[source] += 1
            if len(rows) - before > 1: chunked[source] += 1

    # - source_chunks: source별 최종 chunk 수
    # - source_documents: source별 원본 문서 수
    # - chunked_documents: 실제로 2개 이상 chunk로 쪼개진 원본 문서 수
    # - duplicate_text_count: 삭제하지 않은 동일 텍스트 반복 수
    chunks = Counter(r['source'] for r in rows)
    text_counts = Counter(h(r['source'], r['text']) for r in rows)
    duplicate_text_count = sum(count - 1 for count in text_counts.values() if count > 1)
    return rows, {'base_dir': str(base), 'max_chars': max_chars, 'overlap_chars': overlap, 'total_chunks': len(rows), 'source_documents': dict(sorted(docs.items())), 'source_chunks': dict(sorted(chunks.items())), 'chunked_documents': dict(sorted(chunked.items())), 'duplicate_text_count': duplicate_text_count}


def main():
    """CLI entrypoint.

    - --base-dir: 프로젝트 루트 경로를 지정한다.
    - --max-chars: chunk 최대 문자 수를 조정한다.
    - --overlap-chars: 긴 문서 분할 시 겹침 길이를 조정한다.
    - --out-dir: 산출물 저장 폴더를 지정한다. 기본값은 database/chunks다.
    """
    ap = argparse.ArgumentParser()
    ap.add_argument('--base-dir', type=Path, default=Path(__file__).resolve().parents[1])
    ap.add_argument('--max-chars', type=int, default=MAX_CHARS)
    ap.add_argument('--overlap-chars', type=int, default=OVERLAP)
    ap.add_argument('--out-dir', type=Path)
    a = ap.parse_args()
    base = a.base_dir.resolve()
    out = a.out_dir or base/'database'/'chunks'
    out.mkdir(parents=True, exist_ok=True)
    rows, report = build(base, a.max_chars, a.overlap_chars)

    # - all_chunks.jsonl은 벡터DB 저장 단계에서 직접 읽을 최종 입력 파일이다.
    with (out/'all_chunks.jsonl').open('w', encoding='utf-8', newline='\n') as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False, sort_keys=True) + '\n')

    # - chunk_build_report.json은 청킹 결과 검증용 요약 파일이다.
    with (out/'chunk_build_report.json').open('w', encoding='utf-8') as f:
        json.dump(report, f, ensure_ascii=False, indent=2, sort_keys=True)
    print(json.dumps(report, ensure_ascii=True, sort_keys=True))


if __name__ == '__main__':
    main()
