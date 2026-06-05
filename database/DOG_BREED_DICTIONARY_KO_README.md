# 한글 견종도감 DB 적재 가이드

## 목적

`database/contents/dog_api/dogapi_akc_matched_breeds_ko.json` 파일을 PostgreSQL에 적재해 견종도감 페이지에서 사용할 수 있도록 한다.

이 데이터는 RAG 검색용 embedding 데이터가 아니라, 화면에 직접 보여줄 견종도감 원천 데이터다.

```text
dogapi_akc_matched_breeds_ko.json
↓
dog_breed_dictionary_ko 테이블
↓
Django 견종도감 페이지 조회
```

## pgvector 적재와의 차이

`database/PGVECTOR_README.md`는 챗봇/RAG 검색을 위한 문서다.

```text
rag_chunks
-> 문서 조각 + embedding vector 저장
-> 챗봇 검색용
```

이 문서는 견종도감 화면용 데이터 적재를 설명한다.

```text
dog_breed_dictionary_ko
-> 견종명, 그룹, 출신, 체중, 키, 성격, 설명 저장
-> 견종도감 화면 표시용
```

## 사용 파일

```text
database/contents/dog_api/dogapi_akc_matched_breeds_ko.json
database/tools/build_RDB.py
docker-compose.yml
```

## 적재 대상 테이블

```text
dog_breed_dictionary_ko
```

주요 컬럼:

```text
breed_name_en
breed_name_ko
dogapi_id
breed_group
temperament
origin
image_url
height_min_cm
height_max_cm
weight_min_kg
weight_max_kg
life_expectancy_min
life_expectancy_max
coat_type
coat_length
colors
markings
about
health
grooming
exercise
training
nutrition
history
raw_data
```

## .env 설정

프로젝트 루트의 `.env`에 PostgreSQL 접속 정보가 있어야 한다.

```text
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=pet_dog
POSTGRES_USER=admin
POSTGRES_PASSWORD=admin1234
```

값을 생략하면 `build_RDB.py`는 위 기본값을 사용한다.

## 실행 순서

### 1. PostgreSQL 실행

```powershell
docker compose up -d
```

컨테이너 이름은 `docker-compose.yml` 기준으로 다음과 같다.

```text
pet_dog
```

### 2. Python 의존성 설치

`build_RDB.py`는 PostgreSQL 연결을 위해 `psycopg`가 필요하다.

```powershell
pip install -r requirements.txt
```

### 3. 한글 견종도감 데이터 적재


```powershell
python database\tools\build_RDB.py
```


## 적재 확인

```powershell
docker exec pet_dog psql -U admin -d pet_dog -c "SELECT COUNT(*) FROM dog_breed_dictionary_ko;"
```

정상 적재 시 결과는 다음과 같아야 한다.

```text
256
```

샘플 조회:

```powershell
docker exec pet_dog psql -U admin -d pet_dog -c "SELECT breed_name_en, breed_name_ko, breed_group, origin FROM dog_breed_dictionary_ko LIMIT 5;"
```

## Django에서 조회하려면

현재 Django 설정이 SQLite를 바라보고 있으면 PostgreSQL에 적재한 데이터를 바로 조회할 수 없다.

`web/config/settings.py`의 `DATABASES`를 PostgreSQL로 맞춰야 한다.

```python
import os

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "HOST": os.getenv("POSTGRES_HOST", "localhost"),
        "PORT": os.getenv("POSTGRES_PORT", "5432"),
        "NAME": os.getenv("POSTGRES_DB", "pet_dog"),
        "USER": os.getenv("POSTGRES_USER", "admin"),
        "PASSWORD": os.getenv("POSTGRES_PASSWORD", "admin1234"),
    }
}
```

이미 스크립트가 만든 테이블을 Django 모델로 연결할 때는 `managed = False`를 사용한다.

```python
class DogBreedDictionaryKo(models.Model):
    breed_name_en = models.CharField(max_length=150, unique=True)
    breed_name_ko = models.CharField(max_length=150)

    class Meta:
        managed = False
        db_table = "dog_breed_dictionary_ko"
```

## 주의사항

`build_RDB.py`는 현재 한글 JSON 기준 적재 스크립트로 사용한다.

기존 영문 CSV 기반의 `breeds`, `breed_scores`, `breed_attributes` 적재 흐름과는 다르다.
단일 테이블 적재됨

```text
기존 영문 CSV 적재 (재경님이 한거 -> 삭제해야함)
-> breeds / breed_scores / breed_attributes

현재 한글 JSON 적재 (주영님(나^^)가 한거 -> 적재해야함)
-> dog_breed_dictionary_ko
```

따라서 팀원이 기존 `build_RDB.py`의 동작을 기대하지 않도록 README나 커밋 메시지에 변경 목적을 명확히 남기는 것이 좋다.
