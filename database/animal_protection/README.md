# 유기견/보호동물 연동 및 적재 가이드

## 먼저 정리

이 문서는 공공데이터포털 동물보호 API를 프로젝트에 연결하고, 추후 전체 유기견/보호동물 데이터를 DB에 적재하기 위한 기준 문서다.

현재 프로젝트의 기준 견종 데이터는 아래 테이블을 사용할 예정이다.

```text
dog_breed_dictionary_ko
```

즉, 기존 영문 CSV 기반 테이블인 `breeds`, `breed_scores`, `breed_attributes`가 아니라 한글 JSON 기반 `dog_breed_dictionary_ko`를 기준으로 추천/설명/화면 데이터를 맞춘다.

## 현재 구현 상태

현재까지 구현된 것은 전체 DB 적재가 아니라 API 연동 검증과 화면 연결 준비다.

```text
완료:
1. 공공데이터 API 키 연동
2. 시도/시군구/강아지 품종/구조동물 API 호출 코드 작성
3. 공공데이터 응답을 화면용 데이터로 정규화
4. 추천 견종명 -> 공공데이터 품종 코드 매핑 생성
5. 추천 견종 기준 보호동물 조회 테스트
6. Django 보호동물 페이지 /shelter/ 생성

아직 필요:
1. 전체 유기견/보호동물 적재 테이블 설계 확정
2. 전체 데이터 수집 스크립트 작성
3. DB upsert 적재 구현
4. 적재 주기/갱신 정책 결정
5. 추천 결과 화면 하단에 보호동물 섹션 연결
```

## 파일 역할

### backend/integrations/animal_protection/client.py

공공데이터 API 호출 클라이언트다.

역할:

```text
- .env의 ANIMAL_API_SERVICE_KEY 읽기
- 시도 조회
- 시군구 조회
- 강아지 품종 조회
- 구조동물 조회
- 보호소 상세 조회 확장 가능
- API 원본 응답을 화면용 데이터로 정규화
```

주요 함수:

```text
AnimalProtectionClient.get_sido()
AnimalProtectionClient.get_sigungu()
AnimalProtectionClient.get_kind()
AnimalProtectionClient.get_abandonments()
normalize_abandonments()
```

### backend/integrations/animal_protection/schemas.py

보호동물 한 마리를 프로젝트 내부에서 어떤 형태로 다룰지 정의한다.

대표 필드:

```text
id
notice_no
breed
age
sex
neutered
image_url
happen_place
special_mark
shelter_name
shelter_tel
shelter_address
notice_start_date
notice_end_date
status
raw
```

### backend/integrations/animal_protection/recommendation.py

추천 견종명과 보호동물 조회를 연결한다.

예:

```text
말티즈
-> breed_code_mapping.json에서 kind_code 찾기
-> abandonmentPublic_v2 API에 kind 조건으로 전달
-> 말티즈 보호동물 목록 반환
```

### database/animal_protection/breed_mapping.json

프로젝트 추천 견종명과 공공데이터 품종명 후보를 연결하는 수동 매핑표다.

추천 견종이 추가되면 이 파일에도 추가해야 한다.

### database/animal_protection/breed_code_mapping.json

`breed_mapping.json`과 공공데이터 강아지 품종 목록을 비교해서 생성한 결과 파일이다.

이 파일이 있어야 추천 결과에서 실제 보호동물 API 조회로 넘어갈 수 있다.

### database/animal_protection/data_shape.md

공공데이터 원본 필드와 프로젝트 내부 표준 필드를 비교한 문서다.

화면 구현자, DB 설계자, API 연동자가 함께 보면 된다.

### database/animal_protection/responses/

API 응답 검증 결과를 임시 저장하는 폴더다.

주의:

```text
responses/*.json 파일은 검증용 산출물이다.
커밋 대상이 아니다.
현재는 .gitkeep만 유지한다.
```

### database/tools/fetch_animal_protection_responses.py

API 응답 구조를 확인하기 위한 테스트 스크립트다.

실행:

```powershell
.\.venv\Scripts\python.exe database\tools\fetch_animal_protection_responses.py
```

이 스크립트는 응답 확인용이며, 전체 DB 적재용이 아니다.

### database/tools/build_animal_breed_code_mapping.py

추천 견종명과 공공데이터 품종 코드를 연결하는 `breed_code_mapping.json`을 생성한다.

실행:

```powershell
.\.venv\Scripts\python.exe database\tools\build_animal_breed_code_mapping.py
```

### database/tools/fetch_recommended_shelter_animals.py

추천 견종 기준으로 보호동물을 조회하는 테스트 스크립트다.

실행 예:

```powershell
.\.venv\Scripts\python.exe database\tools\fetch_recommended_shelter_animals.py --breed 말티즈 --upr-cd 6110000 --limit 3 --save
```

이 스크립트도 전체 DB 적재용이 아니라 기능 검증용이다.

### web/shelter/

보호동물 목록 페이지를 위한 Django 앱이다.

현재 URL:

```text
/shelter/?breed=말티즈&upr_cd=6110000
```

## 전체 유기견/보호동물 데이터를 적재하려면

사용자가 요구하는 최종 방향은 공공 API에서 보호동물 데이터를 모두 불러와 DB에 적재하는 것이다.

이 경우 실시간 조회 중심 구조에서 아래 구조로 확장해야 한다.

```text
공공 API 전체 수집
-> shelter_animals 테이블 upsert
-> shelter_centers 테이블 upsert 선택
-> 화면은 공공 API가 아니라 우리 DB 조회
```

## 추천 테이블 설계

### shelter_animals

구조동물/보호동물 원천 데이터를 저장하는 핵심 테이블이다.

```sql
CREATE TABLE IF NOT EXISTS shelter_animals (
    id BIGSERIAL PRIMARY KEY,
    desertion_no VARCHAR(50) UNIQUE NOT NULL,
    notice_no VARCHAR(100),
    happen_dt DATE,
    happen_place TEXT,
    up_kind_cd VARCHAR(20),
    up_kind_nm VARCHAR(50),
    kind_cd VARCHAR(20),
    kind_nm VARCHAR(150),
    kind_full_nm VARCHAR(200),
    color_cd VARCHAR(100),
    age VARCHAR(100),
    weight VARCHAR(100),
    sex_cd VARCHAR(10),
    neuter_yn VARCHAR(10),
    special_mark TEXT,
    care_reg_no VARCHAR(50),
    care_nm VARCHAR(200),
    care_tel VARCHAR(100),
    care_addr TEXT,
    org_nm VARCHAR(200),
    notice_sdt DATE,
    notice_edt DATE,
    process_state VARCHAR(100),
    popfile1 TEXT,
    popfile2 TEXT,
    raw_data JSONB NOT NULL,
    api_updated_at TIMESTAMPTZ,
    fetched_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
```

추천 인덱스:

```sql
CREATE INDEX IF NOT EXISTS idx_shelter_animals_kind_cd ON shelter_animals (kind_cd);
CREATE INDEX IF NOT EXISTS idx_shelter_animals_process_state ON shelter_animals (process_state);
CREATE INDEX IF NOT EXISTS idx_shelter_animals_notice_sdt ON shelter_animals (notice_sdt);
CREATE INDEX IF NOT EXISTS idx_shelter_animals_org_nm ON shelter_animals (org_nm);
```

### shelter_centers 선택

보호센터 정보 조회 API까지 적재하려면 별도 테이블을 둔다.

```sql
CREATE TABLE IF NOT EXISTS shelter_centers (
    id BIGSERIAL PRIMARY KEY,
    care_reg_no VARCHAR(50) UNIQUE,
    care_nm VARCHAR(200),
    care_tel VARCHAR(100),
    care_addr TEXT,
    org_nm VARCHAR(200),
    raw_data JSONB NOT NULL,
    fetched_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
```

## 전체 적재 스크립트

전체 적재 스크립트는 아래 파일이다.

```text
database/tools/build_shelter_animals_db.py
```

이 파일이 하는 일:

```text
1. .env에서 ANIMAL_API_SERVICE_KEY와 PostgreSQL 접속 정보 읽기
2. 시도 목록 조회
3. 시도별 시군구 목록 조회
4. 강아지 기준 upkind=417000으로 구조동물 조회
5. pageNo/numOfRows를 돌며 전체 페이지 수집
6. desertionNo 기준으로 shelter_animals에 upsert
7. 원본 응답은 raw_data JSONB에 저장
8. popfile1/popfile2 이미지 URL 저장
9. 실행 결과 count/report 출력
```

## 전체 적재 실행 흐름

```powershell
# 1. PostgreSQL 실행
docker compose up -d postgres

# 2. 최초 전체 적재
.\.venv\Scripts\python.exe database\tools\build_shelter_animals_db.py --reset

# 3. 이후 갱신 적재
.\.venv\Scripts\python.exe database\tools\build_shelter_animals_db.py

# 4. 특정 기간만 갱신
.\.venv\Scripts\python.exe database\tools\build_shelter_animals_db.py --bgnde 20260601 --endde 20260608
```

특정 시도만 적재하려면 `--sido-cd`를 사용한다.

```powershell
.\.venv\Scripts\python.exe database\tools\build_shelter_animals_db.py --sido-cd 6110000
```

보호중 데이터만 적재하려면 `--state`를 사용한다.

```powershell
.\.venv\Scripts\python.exe database\tools\build_shelter_animals_db.py --state protect
```

API 호출 간격을 늘리고 싶으면 `--sleep`을 사용한다.

```powershell
.\.venv\Scripts\python.exe database\tools\build_shelter_animals_db.py --sleep 0.2
```

## 전체 적재 시 주의할 점

### 1. API 호출량

전국 데이터를 모두 가져오면 호출량이 많아질 수 있다.

권장:

```text
numOfRows는 100~1000 사이에서 테스트
처음에는 최근 30일만 적재
전체 적재는 페이지 수와 응답 시간을 확인 후 진행
```

### 2. 상태 변경

보호동물은 시간이 지나면 상태가 바뀐다.

예:

```text
보호중
종료
입양
반환
자연사
안락사
```

따라서 `desertion_no` 기준 upsert가 필요하다.

### 3. 삭제하지 말고 상태를 갱신

API에서 안 보인다고 바로 DB에서 삭제하면 안 된다.

추천 정책:

```text
공공 API에서 다시 조회된 데이터는 upsert
더 이상 안 보이는 데이터는 바로 삭제하지 않고 별도 inactive 처리 여부 검토
```

### 4. 이미지 URL

이미지는 `popfile1`, `popfile2`로 내려온다.

현재는 URL만 저장한다.
이미지 파일 자체를 다운로드해서 저장하는 것은 후순위다.

## 전체 적재 후 화면 흐름

전체 DB 적재가 끝나면 `/shelter/` 페이지는 공공 API 직접 호출 대신 DB 조회로 바꾸는 것이 좋다.

```text
현재:
/shelter/ -> 공공 API 실시간 조회

변경 후:
/shelter/ -> shelter_animals 테이블 조회
```

추천 결과 화면도 같은 DB를 사용한다.

```text
추천 견종: 말티즈
-> dog_breed_dictionary_ko에서 추천 결과 표시
-> breed_code_mapping.json 또는 kind_cd 매핑
-> shelter_animals에서 말티즈 보호동물 조회
-> 추천 결과 하단에 3건 노출
```



