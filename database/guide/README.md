# 가이드 데이터 작업 흐름

## 목적

처음 반려견을 키우는 사용자를 위해 공공 문서 내용을 6개 주제로 정리하고, `/guide/` 화면과 추후 RAG 검색에 활용한다.

## 화면 주제

1. 입양 전 준비
2. 입양 신청/설문
3. 반려견 공공예절
4. 재난 대응
5. 문제행동/행동지도
6. 맹견·사고견 참고

## 생성 파일

```text
database/guide/source_documents.json
database/guide/processed/guide_sections.json
database/guide/raw/.gitkeep
database/tools/extract_guide_documents.py
web/guide/guide_pages.py
web/guide/urls.py
web/templates/guide/guide.html
```

## 현재 단계

현재는 화면 구현용 정리 데이터인 `guide_sections.json`을 기준으로 `/guide/` 페이지를 표시한다.
원문 PDF/HWP 전체를 RAG에 넣은 상태는 아니다.

## 문서 전처리 순서

1. PDF 문서를 텍스트로 추출한다.
2. HWP 문서는 PDF/DOCX/TXT로 변환한 뒤 텍스트화한다.
3. 추출한 텍스트를 `database/guide/raw/`에 저장한다.
4. 초보 보호자용 표현으로 요약해 `database/guide/processed/guide_sections.json`을 보강한다.
5. 이후 RAG용 chunk를 생성하고 pgvector에 적재한다.

## PDF 텍스트 추출 예시

```powershell
.\.venv\Scripts\python.exe database\tools\extract_guide_documents.py "C:\Users\pc\Downloads\별첨 5. 반려견 공공예절교육.pdf"
```

여러 파일도 한 번에 넘길 수 있다.

```powershell
.\.venv\Scripts\python.exe database\tools\extract_guide_documents.py "C:\Users\pc\Downloads\별첨 5. 반려견 공공예절교육.pdf" "C:\Users\pc\Downloads\반려동물 가족을 위한 재난 대응 가이드라인(국민용).pdf"
```

## HWP 처리

HWP는 실행 환경에 따라 자동 추출 안정성이 낮다. 우선 한글 또는 LibreOffice에서 PDF/DOCX/TXT로 변환한 뒤 `database/guide/raw/`에 저장하는 방식을 권장한다.

## 추후 RAG 연결

```text
guide_sections.json 또는 raw txt
→ guide chunk 생성
→ embedding 생성
→ langchain_pg_embedding에 guide 문서로 저장
→ 챗봇에서 가이드 문서 기반 답변
```
