# SKN27-4th-2team

**대주제**: AI 활용 애플리케이션 개발  
**세부 주제**: LLM을 연동한 내외부 문서 기반 반려견 케어 Q&A 웹 서비스    

![Pet Mate Demo Flow](docs/assets/readme/demo-flow.gif)

---

## **1. 팀 소개**

### **팀명**: 뉴진스(NewJeans)

### **팀원 소개**
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
    <td align="center">데이터 수집 및 전처리, 에이전트, 시퀀스다이어그램</td>
    <td align="center">Django 구현, README 작성</td>
    <td align="center">데이터 수집 및 RAG, 발표</td>
  </tr>
</table>

---

# **Contents**

1. [팀 소개](#1-팀-소개)
2. [프로젝트 개요](#2-프로젝트-개요)
3. [기술 스택](#3-기술-스택)
4. [데이터 및 모델 선정](#4-데이터-및-모델-선정)
5. [시스템 아키텍처](#5-시스템-아키텍처)
6. [WBS](#6-wbs)
7. [요구사항 명세서](#7-요구사항-명세서)
8. [화면 설계서](#8-화면-설계서)
9. [시연 화면](#9-시연-화면)
10. [테스트 계획 및 결과 보고서](#10-테스트-계획-및-결과-보고서)
11. [수행 결과](#11-수행-결과)
12. [서비스 개선 노력](#12-서비스-개선-노력)
13. [한계 및 향후 개선 방향](#13-한계-및-향후-개선-방향)
14. [실행 방법](#14-실행-방법)
15. [참고 문서](#15-참고-문서)
16. [팀원 회고](#16-팀원-회고)

---

## **2. 프로젝트 개요**

## **2.1 프로젝트 명**


## **2.2 프로젝트 소개**

본 프로젝트는 반려견 관련 정보를 단순히 나열하는 것이 아니라, 사용자가 입양을 준비하는 과정에서 필요한 기능을 단계적으로 사용할 수 있도록 구성하는 것을 목표로 했습니다.

- 반려견 양육과 입양 관련 질문은 챗봇에서 처리합니다.
- 견종별 성격, 크기, 활동량, 훈련성, 건강 정보는 견종도감에서 조회합니다.
- 입양 전 준비 상태는 입양 테스트로 확인합니다.
- 동물보호 API 기반 보호동물 데이터는 유기견 입양 화면에서 조회합니다.

## **2.3 프로젝트 배경 및 필요성**

### **2.3.1. 반려견 입양 정보의 분산**

- 반려견 입양 전 사용자는 준비물, 훈련, 생활 관리, 견종 특성, 보호동물 정보를 여러 사이트에서 따로 확인해야 합니다.
- 정보가 흩어져 있으면 초보 보호자는 무엇부터 확인해야 하는지 판단하기 어렵습니다.
- Pet Mate는 반려견 입양 전후에 필요한 핵심 정보를 하나의 서비스 흐름으로 연결합니다.

### **2.3.2. 초보 보호자의 의사결정 부담**

- 초보 보호자는 자신의 생활환경에 어떤 견종이 맞는지 판단하기 어렵습니다.
- 원룸 거주, 장시간 외출, 털빠짐, 짖음, 산책 시간 등 현실 조건을 함께 고려해야 합니다.
- Pet Mate는 견종 데이터와 반려견 케어 문서를 기반으로 사용자의 질문에 맞춘 안내를 제공합니다.

### **2.3.3. 실제 유기견 데이터와 추천 흐름의 연결 필요**

- 견종 추천이 실제 입양으로 이어지려면 현재 보호 중인 유기견 정보와 연결되어야 합니다.
- Pet Mate는 공공데이터포털 동물보호 API 데이터를 DB에 적재하고, 견종/지역/상태 필터로 조회할 수 있게 구성했습니다.
- 유기견 현황 표를 통해 전체, 보호중, 입양 완료, 기타 상태 건수를 확인할 수 있습니다.

## **2.4 프로젝트 목표**

### **[1] 근거 기반 반려견 케어 Q&A**

> 목표: 반려견 케어 문서와 견종 정보를 RAG로 연결해 질문에 맞는 답변을 제공

- 유튜브 Q&A, AKC 견종 데이터, 초보 보호자 가이드 문서를 검색 가능한 지식 기반으로 구성
- LangGraph workflow로 질문 분석, 문서 검색, 답변 생성 흐름 분리
- 답변에 활용된 출처를 함께 제공할 수 있는 구조 마련

### **[2] 사용자 조건 기반 견종 탐색**

> 목표: 사용자가 자신의 생활환경에 맞는 견종을 찾도록 지원

- 한글 견종 사전 `dog_breed_dictionary_ko` 테이블 기반 검색
- 견종 그룹, 원산지, 키워드 필터 제공
- 견종 상세 화면에서 성격, 운동량, 관리 난이도, 건강 정보를 제공

### **[3] 실제 유기견 입양 정보 연결**

> 목표: 추천과 탐색을 실제 보호동물 데이터로 이어지는 입양 흐름으로 확장

- 동물보호 API 데이터를 `shelter_animals` 테이블에 적재
- 유기견 입양 화면에서 견종, 지역, 상태별 필터 제공
- 보호동물 상세 모달, 보호소 전화 연결, 즐겨찾기 기능 제공

---

## **3. 기술 스택**

| 분류 | 기술 및 도구 |
| --- | --- |
| **Frontend** | ![HTML5](https://img.shields.io/badge/HTML5-E34F26?style=for-the-badge&logo=html5&logoColor=white) ![CSS3](https://img.shields.io/badge/CSS3-1572B6?style=for-the-badge&logo=css3&logoColor=white) ![JavaScript](https://img.shields.io/badge/JavaScript-F7DF1E?style=for-the-badge&logo=javascript&logoColor=black) |
| **Backend** | ![Python](https://img.shields.io/badge/Python-3776AB?style=for-the-badge&logo=python&logoColor=white) ![Django](https://img.shields.io/badge/Django-092E20?style=for-the-badge&logo=django&logoColor=white) |
| **AI & RAG** | ![OpenAI](https://img.shields.io/badge/OpenAI-412991?style=for-the-badge&logo=openai&logoColor=white) ![LangChain](https://img.shields.io/badge/LangChain-00C7B7?style=for-the-badge&logoColor=white) ![LangGraph](https://img.shields.io/badge/LangGraph-FF6F00?style=for-the-badge&logoColor=white) |
| **Database** | ![PostgreSQL](https://img.shields.io/badge/PostgreSQL-4169E1?style=for-the-badge&logo=postgresql&logoColor=white) ![pgvector](https://img.shields.io/badge/pgvector-4169E1?style=for-the-badge&logoColor=white) |
| **Data** | ![Pandas](https://img.shields.io/badge/Pandas-150458?style=for-the-badge&logo=pandas&logoColor=white) ![BeautifulSoup](https://img.shields.io/badge/BeautifulSoup-4B8BBE?style=for-the-badge&logoColor=white) ![Playwright](https://img.shields.io/badge/Playwright-2EAD33?style=for-the-badge&logo=playwright&logoColor=white) |
| **Infrastructure** | ![Docker](https://img.shields.io/badge/Docker-2496ED?style=for-the-badge&logo=docker&logoColor=white) ![GitHub](https://img.shields.io/badge/GitHub-181717?style=for-the-badge&logo=github&logoColor=white) |

---

## **4. 데이터 및 모델 선정**

## **4.1 데이터 선정**


## **4.2 모델 및 저장소 선정**

| 항목 | 선택 | 이유 |
| --- | --- | --- |
| Chat Model | OpenAI Chat Model | 한국어 질의응답 처리와 Django 연동 편의성 |
| Embedding Model | `text-embedding-3-small` | 비용 대비 검색 품질과 처리 속도 균형 |
| Vector DB | PostgreSQL + pgvector | Django DB와 RAG 검색 데이터를 같은 PostgreSQL 환경에서 관리 가능 |
| Workflow | LangGraph | 질문 분석, 검색, 생성 단계를 분리해 관리 가능 |
| Web Framework | Django | 인증, 템플릿, ORM을 포함한 웹 기능 구현에 적합 |

---

## **5. 시스템 아키텍처**

## **5.1 전체 구조**


## **5.2 RAG 처리 흐름**


## **5.3 주요 테이블**


## **6. WBS**


---

## **7. 요구사항 명세서**

## **7.1 기능 요구사항**

| ID | 요구사항 | 구현 여부 |
| --- | --- | --- |
| FR-001 | 사용자는 반려견 케어 질문을 챗봇에 입력할 수 있다 | 완료 |
| FR-002 | 챗봇은 RAG 기반 답변과 출처 정보를 제공한다 | 완료 |
| FR-003 | 사용자는 견종명, 그룹, 원산지로 견종을 검색할 수 있다 | 완료 |
| FR-004 | 사용자는 견종 상세 정보를 확인할 수 있다 | 완료 |
| FR-005 | 사용자는 입양 준비 테스트를 풀고 결과를 확인할 수 있다 | 완료 |
| FR-006 | 로그인 사용자는 테스트 결과를 저장할 수 있다 | 완료 |
| FR-007 | 사용자는 유기견 목록을 견종, 지역, 상태별로 필터링할 수 있다 | 완료 |
| FR-008 | 사용자는 보호동물 상세 정보와 보호소 연락처를 확인할 수 있다 | 완료 |
| FR-009 | 로그인 사용자는 견종과 보호동물을 즐겨찾기할 수 있다 | 완료 |
| FR-010 | 사용자는 가이드 원문 PDF를 확인할 수 있다 | 완료 |

## **7.2 비기능 요구사항**

| ID | 요구사항 | 구현 방향 |
| --- | --- | --- |
| NFR-001 | 데이터 조회 성능 | API 실시간 호출 대신 DB 적재 후 조회 |
| NFR-002 | 유지보수성 | Django 앱별 기능 분리, backend 서비스 계층 분리 |
| NFR-003 | 데이터 재생성 | `database/tools` 스크립트로 벡터, 퀴즈, 유기견 데이터 재생성 |
| NFR-004 | 확장성 | PGVector collection, ShelterAnimal 테이블 기반 확장 가능 |
| NFR-005 | 사용자 경험 | AJAX 필터, 모달, 즐겨찾기, 마이페이지 제공 |

---

## **8. 화면 설계서**


## **9. 시연 화면**

## **9.0 서비스 데모 흐름**

홈 화면부터 챗봇, 견종도감, 가이드, 입양 테스트, 유기견 입양 화면까지 이어지는 전체 서비스 흐름입니다.

![Pet Mate Demo Flow](docs/assets/readme/demo-flow.gif)

## **9.1 Home**

서비스의 핵심 흐름을 소개하고, 챗봇/견종도감/입양 테스트/유기견 입양 페이지로 이동할 수 있는 진입 화면입니다.

![Home](docs/assets/readme/01-home.png)

## **9.2 Chatbot**

반려견 케어 질문과 견종 추천 질문을 입력하면 RAG workflow를 거쳐 답변을 생성하는 화면입니다.

![Chatbot](docs/assets/readme/02-chatbot.png)

## **9.3 견종도감**

한글 견종 사전 기반으로 견종을 검색하고, 그룹/원산지 조건으로 필터링할 수 있는 화면입니다.

![Dog Breeds](docs/assets/readme/03-dog-breeds.png)

## **9.4 가이드**

입양 전 준비, 입양 신청, 공공예절, 재난 대응, 행동지도 등 초보 보호자에게 필요한 가이드와 원문 PDF 출처를 제공하는 화면입니다.

![Guide](docs/assets/readme/04-guide.png)

## **9.5 입양 테스트**

Q&A 기반 랜덤 퀴즈를 통해 입양 준비도를 점검하고, 로그인 사용자는 결과를 저장할 수 있습니다.

![Adoption Test](docs/assets/readme/05-test.png)

## **9.6 유기견 입양**

동물보호 API 기반 유기견 데이터를 견종/지역/상태별로 필터링하고, 현황 표와 보호동물 카드를 확인하는 화면입니다.

![Shelter](docs/assets/readme/06-shelter.png)

---

## **10. 테스트 계획 및 결과 보고서**

## 테스트 시나리오 결과 요약

| 총 시나리오 | Pass | Fail | 비고 |
| --- | --- | --- | --- |
| 6 | 6 | 0 | Django 시스템 체크 및 주요 화면 기능 검증 |

### TEST-001 · Django 시스템 체크

| 테스트 절차 | 기대 결과 | 결과 |
| --- | --- | --- |
| `python web/manage.py check` 실행 | Django 설정 오류 없음 | PASS |

### TEST-002 · 견종도감 검색

| 테스트 절차 | 기대 결과 | 결과 |
| --- | --- | --- |
| `/dog/breeds/`에서 키워드/그룹/원산지 필터 사용 | 조건에 맞는 견종 목록 출력 | PASS |

### TEST-003 · 챗봇 RAG 답변

| 테스트 절차 | 기대 결과 | 결과 |
| --- | --- | --- |
| 반려견 케어 질문 입력 | RAG workflow를 통한 답변 생성 | PASS |

### TEST-004 · 입양 테스트

| 테스트 절차 | 기대 결과 | 결과 |
| --- | --- | --- |
| `/test/`에서 퀴즈 제출 | 점수, 정답, 오답, 해설 출력 | PASS |

### TEST-005 · 유기견 필터 및 현황 표

| 테스트 절차 | 기대 결과 | 결과 |
| --- | --- | --- |
| `/shelter/`에서 상태/견종/지역 필터 사용 | 목록과 상태별 현황 표가 조건에 맞게 갱신 | PASS |

### TEST-006 · DB 상태별 건수 검증

| 테스트 절차 | 기대 결과 | 결과 |
| --- | --- | --- |
| `shelter_animals` 상태별 count 조회 | 화면의 전체/보호중/입양완료/기타 상태 수와 일치 | PASS |

---

## **11. 수행 결과**

## **11.1 구현 완료 기능**

- RAG 기반 반려견 케어 챗봇
- 한글 견종도감 검색 및 상세 페이지
- 초보 보호자 가이드 및 원문 PDF 링크
- 입양 준비 테스트 및 로그인 사용자 결과 저장
- 유기견 입양 목록, 필터, 상태별 현황 표
- 견종/보호동물 즐겨찾기
- 마이페이지 반려동물 관리
- PostgreSQL/PGVector 기반 데이터 저장 및 검색

---

## **12. 서비스 개선 노력**

### **개선 1. API 직접 호출 대신 DB 조회 중심 구조 적용**

- 유기견 목록은 공공 API를 화면에서 매번 호출하지 않고 `shelter_animals` 테이블에 적재한 뒤 조회합니다.
- 화면 렌더링 시 외부 API 응답 상태에 직접 의존하지 않도록 구성했습니다.

### **개선 2. RAG workflow 분리**

- 질문 분석, 검색 쿼리 생성, 문서 검색, 답변 생성을 `backend/agents`로 분리했습니다.
- 추후 검색 로직이나 검증 노드를 교체해도 전체 구조를 유지할 수 있습니다.

### **개선 3. 보호동물 현황 가시화**

- 유기견 입양 화면에 전체, 보호중, 입양 완료, 기타 상태 건수를 표로 제공했습니다.
- 필터 조건에 따라 현황 표도 함께 갱신되도록 구성했습니다.

### **개선 4. 데이터 재생성 스크립트 분리**

- 벡터스토어 적재, 퀴즈 생성, 유기견 데이터 적재를 각각 스크립트로 분리했습니다.
- 데이터 최신화와 재현성을 확보했습니다.

---

## **13. 한계 및 향후 개선 방향**

| 한계 | 개선 방향 |
| --- | --- |
| RAG 답변 품질은 적재 문서 품질과 OpenAI API 응답에 영향을 받음 | 문서 메타데이터 보강, 검색 결과 평가 로직 추가 |
| 유기견 데이터는 API 갱신 시점에 따라 실제 현황과 차이가 날 수 있음 | 주기적 적재 스케줄링, 마지막 갱신 시간 표시 |
| 견종 추천과 유기견 추천의 연결이 아직 제한적임 | 챗봇 추천 결과와 `shelter_animals` 자동 매칭 강화 |
| 위치 기반 입양 탐색이 부족함 | 보호소 위치 기반 거리순 정렬, 지도 연동 |
| 입양 신청 단계까지 직접 연결되지는 않음 | 보호소 상세 정보, 입양 신청서, 상담 절차 연결 |

---

## **14. 실행 방법**

### **환경 변수**

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

### **데이터베이스 실행**

```bash
docker compose up -d
```

### **데이터 적재**

```bash
python database/tools/build_RDB.py
python database/tools/build_vectorstore.py --reset
python database/tools/build_shelter_animals_db.py --reset
```

### **웹 서버 실행**

```bash
python web/manage.py runserver
```

---

## **15. 참고 문서**

- **AKC Dog Breeds**: https://www.akc.org/dog-breeds/
- **한국애견연맹**: https://www.thekkf.or.kr/
- **TheDogAPI**: https://www.thedogapi.com/
- **API Ninjas Dogs API**: https://api-ninjas.com/api/dogs
- **동물보호 공공데이터 API**: https://www.data.go.kr/
- **Merck Veterinary Manual**: https://www.merckvetmanual.com/
- **LangChain**: https://www.langchain.com/
- **PGVector**: https://github.com/pgvector/pgvector

---

## **16. 팀원 회고**

| 팀원 | 회고 |
|---|---|
| 문재경 | |
| 박준희 | |
| 오주희 | |
| 신동혁 | |
| 김주영 | |
