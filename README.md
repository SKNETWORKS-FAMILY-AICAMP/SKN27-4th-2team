# Pet Mate

> 초보 보호자와 예비 보호자를 위한 반려견 케어 Q&A 및 입양 지원 서비스

## Contents

1. [팀 소개](#1-팀-소개)
2. [프로젝트 소개](#2-프로젝트-소개)
3. [기술 스택](#3-기술-스택)
4. [시스템 아키텍처](#4-시스템-아키텍처)
5. [주요 기능](#6-주요-기능)
6. [데이터 파이프라인](#7-데이터-파이프라인)
7. [VectorDB 적재](#8-vectordb-적재)
8. [RAG 설계 및 시퀀스 다이어그램](#8-rag-설계-및-시퀀스-다이어그램)
9. [실행 방법](#10-실행-방법)
10. [시연 화면](#11-시연-화면)
11. [기대 효과 및 결론](#12-기대-효과-및-결론)
12. [참고 자료](#14-참고-자료)
13. [팀원 회고](#13-팀원-회고)


---

## 1. 팀 소개

### 팀명

**뉴진스(NewJeans)**

### 팀원 소개

<table align="center" width="100%">
  <tr>
    <td align="center" width="20%"><img src="https://postfiles.pstatic.net/MjAyNjA2MDlfMTk3/MDAxNzgwOTg3NzA4NTE1.jArqE2CKKQN-d2tdVpssrd8F1g64dWmI3k7LSppzL7Mg.J07ASomAPh6TzCAr7MBT1xcMbUEqpwmYJRhKlj074Lgg.PNG/%EC%A3%BC%EC%98%81.png?type=w966" width="120" height="120" alt="김주영" /></td>
    <td align="center" width="20%"><img src="https://postfiles.pstatic.net/MjAyNjA2MDlfMTc3/MDAxNzgwOTg3NzA4NTEy.1VneL8J-6Epqh2neG8bz0zM2wjfXNdie3B3lOujcmkcg.15FPyFOhyA2WZrNM8Edlr9EO4Anmp_mXv0o-Evq06Nsg.PNG/%EC%9E%AC%EA%B2%BD.png?type=w966" width="120" height="120" alt="문재경" /></td>
    <td align="center" width="20%"><img src="https://postfiles.pstatic.net/MjAyNjA2MDlfNzcg/MDAxNzgwOTg3NzYyOTU3.Fy8Aah8ioa3BlUrXs8kUYsTNmyvBV3WhKGso2bBHsRgg.O_ArPGjIIQ2ILrXlN-9sEqbOge5Y5c6_1wiY5Fk9vHIg.PNG/%EC%A4%80%ED%9D%AC.png?type=w966" width="120" height="120" alt="박준희" /></td>
    <td align="center" width="20%"><img src="https://postfiles.pstatic.net/MjAyNjA2MDlfMjQw/MDAxNzgwOTg3NzA4NTIy.2bCCMI-7N0r2YrV97IaQ-NnR5MN-Lc9pXSr58E3uprMg.8uGM2iLfZjKuEP7qjBBhqBgQCb5ZdgUCCANT37PWIhcg.PNG/%EB%8F%99%ED%98%81.png?type=w966" width="120" height="120" alt="신동혁" /></td>
    <td align="center" width="20%"><img src="https://postfiles.pstatic.net/MjAyNjA2MDlfNDkg/MDAxNzgwOTg3NzA4NTIy.tUmhBTl0HIbIZjK-MqmmXIdHH0yAmHLRuf_kcWh5vtAg.Xu7utC824enN6OJZ19RW67kxzvuKEMrFLyWmLUnUoU4g.PNG/%EC%A3%BC%ED%9D%AC.png?type=w966" width="120" height="120" alt="오주희" /></td>
  </tr>
  <tr>
    <td align="center"><b>김주영</b></td>
    <td align="center"><b>문재경</b></td>
    <td align="center"><b>박준희</b></td>
    <td align="center"><b>신동혁</b></td>
    <td align="center"><b>오주희</b></td>
  </tr>
  <tr>
    <td align="center">팀원</td>
    <td align="center">팀원</td>
    <td align="center">팀원</td>
    <td align="center">팀원</td>
    <td align="center">팀원</td>
  </tr>
    <tr>
    <td align="center">데이터 수집 및 전처리, 발표</td>
    <td align="center">데이터 전처리 및 감독</td>
    <td align="center">데이터 수집 및 전처리</td>
    <td align="center">Django 구현, README 작성</td>
    <td align="center">데이터 수집 및 RAG, 발표</td>
  </tr>
</table>


---

## 2. 프로젝트 소개

### 프로젝트명

**Pet Mate**

### 한 줄 소개

반려견 행동, 건강, 견종 특성, 입양 정보를 통합하여 초보 보호자가 신뢰할 수 있는 답변과 입양 탐색 경험을 제공하는 RAG 기반 반려견 케어 서비스이다.

### 개발 배경

반려견 입양과 양육은 장기적인 책임을 동반한다. 하지만 초보 보호자와 예비 보호자는 유튜브, 블로그, 견종 백과, 공공데이터 등 여러 곳에 흩어진 정보를 직접 찾아야 하며, 정보의 신뢰도와 본인 상황에 맞는 적합성을 판단하기 어렵다.

본 프로젝트는 다음 문제를 해결하기 위해 설계했다.

| 문제 | 해결 방향 |
|---|---|
| 반려견 관련 정보가 여러 출처에 흩어져 있음 | 유튜브 Q&A, 수의학 자료, 견종 데이터, 공공 유기동물 데이터를 통합 |
| 초보 보호자가 질문에 맞는 답을 찾기 어려움 | RAG 기반 챗봇으로 자연어 질문에 근거 기반 답변 제공 |
| 견종별 성향과 관리 난이도를 비교하기 어려움 | 견종도감과 검색/필터 기능으로 견종 특성 탐색 지원 |
| 입양 전 실제 보호 동물 정보를 확인하기 어려움 | 동물보호 공공데이터 API 기반 유기견 목록 제공 |
| 입양 준비도와 기본 지식 점검이 부족함 | 초보 보호자 가이드와 반려견 지식 퀴즈 제공 |

### 프로젝트 목표

- 반려견 케어 질문에 대한 RAG 기반 답변 제공
- PostgreSQL/PGVector 기반 문서 검색 체계 구축
- 견종별 성향, 건강, 활동량, 관리 정보를 탐색할 수 있는 견종도감 제공
- 동물보호 공공데이터 기반 보호 동물 목록 및 상세 정보 제공
- 초보 보호자를 위한 가이드와 입양 준비도 확인 기능 제공
- 로그인 사용자의 채팅 내역, 관심 견종, 관심 유기견, 테스트 결과 관리

---

## 3. 기술 스택

| 분류 | 기술 |
|---|---|
| Language | Python |
| Web Framework | Django 6.0.5 |
| Backend | Django App, LangChain, LangGraph |
| LLM / Embedding | OpenAI API, LangChain OpenAI |
| RDB / VectorDB | PostgreSQL 16, PGVector |
| Data Processing | pandas, BeautifulSoup4, Playwright |
| Database Driver | psycopg |
| Infra | Docker, Docker Compose |
| Frontend | Django Template, HTML, CSS |

---

## 4. 시스템 아키텍처

### 전체 구조

```text
[사용자]
   |
   v
[Django Web]
   |-- Main/Home
   |-- Chatbot
   |-- Dog Dictionary
   |-- Shelter Animals
   |-- Guide
   |-- Test
   |-- User Profile
   |
   v
[Backend Services]
   |-- RAG Workflow
   |-- Response Generator
   |-- User Analysis
   |-- Shelter Recommendation
   |
   v
[PostgreSQL + PGVector]
   |-- dog_breed_dictionary_ko
   |-- shelter_animals
   |-- langchain_pg_collection
   |-- langchain_pg_embedding
```

### 프로젝트 구조

```text
SKN27-4th-2team/
├─ backend/
│  ├─ agents/
│  ├─ integrations/
│  │  ├─ animal_protection/
│  │  └─ rag/
│  ├─ schemas/
│  └─ services/
├─ database/
│  ├─ akc/
│  ├─ animal_protection/
│  ├─ contents/
│  ├─ docs/
│  ├─ guide/
│  ├─ merck_vet/
│  ├─ tools/
│  └─ dumps/
├─ web/
│  ├─ chatbot/
│  ├─ dog/
│  ├─ guide/
│  ├─ shelter/
│  ├─ test/
│  ├─ user/
│  ├─ templates/
│  └─ static/
├─ docker-compose.yml
├─ requirements.txt
└─ README.md
```

---


## 5. 주요 기능

| 기능 | 설명 |
|---|---|
| 반려견 Q&A 챗봇 | 반려견 행동, 건강, 훈련, 입양 준비 등에 대한 자연어 질문 처리 |
| RAG 기반 답변 | PGVector에 저장된 문서 검색 결과를 기반으로 답변 생성 |
| 견종도감 | 견종별 이미지, 성격, 크기, 수명, 건강, 미용, 활동량 등 정보 제공 |
| 견종 검색 및 필터 | 견종명, 그룹, 출신지 등 기준으로 견종 탐색 |
| 유기견 입양 정보 | 공공데이터 기반 보호 동물 목록 및 상세 정보 제공 |
| 초보 보호자 가이드 | 입양 전 준비, 공공예절, 재난 대응, 행동지도 관련 자료 제공 |
| 반려견 지식 퀴즈 | Q&A 데이터 기반 문제 풀이와 결과 확인 |
| 마이페이지 | 채팅 내역, 관심 견종, 관심 유기견, 테스트 결과 관리 |

---

## 6. 데이터 파이프라인

### 전체 흐름

```text
[원천 데이터]
   |-- AKC 견종 데이터
   |-- TheDogAPI / API Ninjas 견종 데이터
   |-- 한국애견연맹 견종 정보
   |-- Merck Veterinary Manual
   |-- 유튜브 반려견 Q&A
   |-- 동물보호 공공데이터 API
   |-- 초보 보호자 가이드 PDF
   |
   v
[전처리]
   |-- 견종명 한국어 매핑
   |-- 문서 제목 정제
   |-- Q&A JSON/JSONL 변환
   |-- 보호 동물 응답 정규화
   |
   v
[적재]
   |-- RDB 테이블 적재
   |-- PGVector 문서 임베딩 적재
   |-- 보호 동물 데이터 적재
   |
   v
[서비스]
   |-- 챗봇 검색 근거
   |-- 견종도감
   |-- 유기견 목록
   |-- 사용자 맞춤 탐색
```

### 주요 적재 스크립트

| 스크립트 | 역할 |
|---|---|
| `database/tools/build_RDB.py` | 견종 사전 RDB 적재 |
| `database/tools/build_vectorstore.py` | 문서 청킹, 임베딩, PGVector 적재 |
| `database/tools/build_shelter_animals_db.py` | 동물보호 공공데이터 기반 보호 동물 적재 |

---

## 7. VectorDB 적재

### 적재 대상

| 데이터 | 설명 | 활용 |
|---|---|---|
| 유튜브 Q&A | 반려견 행동, 건강, 훈련 관련 질의응답 | 챗봇 답변 근거 |
| 수의학 문서 | Merck Veterinary Manual 기반 반려견 건강 자료 | 건강 관련 답변 근거 |
| 가이드 문서 | 입양, 공공예절, 행동지도, 재난 대응 자료 | 초보 보호자 가이드 |
| 견종 문서 | 견종 특성과 관리 정보 | 견종 추천 및 설명 |

### 최근 적재 결과

| 항목 | 건수 |
|---|---:|
| `dog_breed_dictionary_ko` | 110 |
| `langchain_pg_collection` | 1 |
| `langchain_pg_embedding` | 6173 |
| `shelter_animals` | 4647 |

### Dump 파일

```text
database/dumps/pet_dog_2.dump
```

---

## 8. RAG 설계 및 시퀀스 다이어그램

### RAG 처리 흐름

```text
사용자 질문
   |
   v
질문 분석 및 검색 질의 생성
   |
   v
PGVector 유사 문서 검색
   |
   v
검색 문서와 사용자 컨텍스트 결합
   |
   v
LLM 답변 생성
   |
   v
출처와 함께 사용자에게 응답
```

### 시퀀스 다이어그램


---

## 9. 실행 방법

### 환경 변수

프로젝트 루트에 `.env` 파일을 생성하고 다음 값을 설정한다.

```env
OPENAI_API_KEY=
ANIMAL_API_SERVICE_KEY=
POSTGRES_DB=pet_dog
POSTGRES_USER=admin
POSTGRES_PASSWORD=
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
```

### 데이터베이스 실행

```bash
docker compose up -d
```

### 데이터 적재

```bash
python database/tools/build_RDB.py
python database/tools/build_vectorstore.py --reset
python database/tools/build_shelter_animals_db.py --reset
```

### 웹 서버 실행

```bash
python web/manage.py runserver
```

---

## 10. 시연 화면

| 화면 | 설명 | 이미지 |
|---|---|---|
| 메인 | 서비스 소개 및 주요 기능 진입 |  |
| 챗봇 | 반려견 Q&A 답변 |  |
| 견종도감 | 견종 검색 및 상세 정보 |  |
| 유기견 입양 | 보호 동물 목록 및 상세 정보 |  |
| 가이드 | 초보 보호자 가이드 |  |
| 입양 테스트 | 반려견 지식 퀴즈 |  |
| 마이페이지 | 사용자 활동 관리 |  |

---

## 11. 기대 효과 및 결론

### 기대 효과

- 초보 보호자의 정보 탐색 시간을 줄이고 신뢰 가능한 답변 제공
- 견종 특성과 보호자 생활환경을 함께 고려한 탐색 경험 제공
- 공공데이터 기반 보호 동물 정보를 연결해 실제 입양 정보 접근성 향상
- RAG 기반 검색과 출처 표시를 통해 답변의 근거 확인 가능
- 입양 전 준비 사항을 점검하여 책임 있는 입양 문화 유도

### 결론

Pet Mate는 반려견을 처음 맞이하는 사용자가 정보 탐색, 견종 이해, 입양 준비를 한 흐름 안에서 진행할 수 있도록 돕는 서비스이다. RDB와 VectorDB를 함께 활용하여 정형 데이터 탐색과 비정형 문서 기반 답변을 결합했고, 보호 동물 공공데이터를 연결해 실제 입양 행동까지 이어질 수 있는 구조를 마련했다.

---

## 12. 팀원 회고

| 팀원 | 회고 |
|---|---|
| 문재경 |  |
| 박준희 |  |
| 오주희 |  |
| 신동혁 |  |
| 김주영 |  |

---

## 12. 참고 자료

- AKC Dog Breeds: https://www.akc.org/dog-breeds/
- 한국애견연맹: https://www.thekkf.or.kr/
- TheDogAPI: https://www.thedogapi.com/
- API Ninjas Dogs API: https://api-ninjas.com/api/dogs
- 동물보호 공공데이터 API: https://www.data.go.kr/
- Merck Veterinary Manual: https://www.merckvetmanual.com/
- LangChain: https://www.langchain.com/
- PGVector: https://github.com/pgvector/pgvector

---

## 13. 팀원 회고

| 팀원 | 회고 |
|---|---|
| 문재경 |  |
| 박준희 |  |
| 오주희 |  |
| 신동혁 |  |
| 김주영 |  |
