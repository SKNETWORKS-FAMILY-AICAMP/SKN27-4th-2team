# 견종도감 DB 적재 최종 가이드

견종도감 화면에서 사용할 한글 견종 데이터를 PostgreSQL에 적재하는 최종 가이드다.

## 최종 데이터

```text
database/contents/dog_api/dog_images_110.csv
database/contents/dog_api/dog_images_110.json
```

```text
전체 견종 수: 110
이미지URL 있음: 110
이미지URL 없음: 0
```

`dog_images_110.csv`는 확인용이고, DB 적재는 `dog_images_110.json`으로 한다.

## DB 설정

Django는 Docker PostgreSQL의 `pet_dog` DB를 사용한다.

`web/config/settings.py`:

```python
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

컨테이너 확인:

```powershell
docker ps
```

DB 접속:

```powershell
docker exec -it pet_dog psql -U admin -d pet_dog
```

## 적재 대상 테이블

```text
dog_breed_dictionary_ko
```

주요 매핑:

```text
breed_name_en             <- 견종명_영문
breed_name_ko             <- 견종명_한글
breed_group               <- 견종그룹명
breed_group_number        <- 견종그룹번호
breed_group_description   <- 견종그룹설명
image_url                 <- 이미지URL
```

적재 스크립트:

```text
database/tools/build_RDB.py
```

## DB 재적재

프로젝트 루트에서 실행:

```powershell
python database\tools\build_RDB.py --json database\contents\dog_api\dog_images_110.json
```


## 적재 확인

```powershell
docker exec pet_dog psql -U admin -d pet_dog -c "SELECT COUNT(*) FROM dog_breed_dictionary_ko;"
```

예상:

```text
110
```

이미지 개수 확인:

```powershell
docker exec pet_dog psql -U admin -d pet_dog -c "SELECT COUNT(*) AS total, COUNT(image_url) AS with_image, COUNT(*) - COUNT(image_url) AS without_image FROM dog_breed_dictionary_ko;"
```

예상:

```text
total: 110
with_image: 110
without_image: 0
```

## 웹 연결 파일

```text
web/dog/models.py
web/dog/services.py
web/dog/views.py
web/dog/urls.py
web/templates/dog/search.html
web/templates/dog/detail.html
```

목록 페이지:

```text
/dog/search/
```

상세 페이지:

```text
/dog/<id>/
```

검색 기준:

```text
한글명 + 영문명
```

정렬 기준:

```text
한글명
```

## Django 실행

```powershell
cd web
python manage.py check
python manage.py migrate
python manage.py runserver
```

접속:

```text
http://127.0.0.1:8000/dog/search/
```

## 팀원 공유 파일

필수:

```text
database/DOG_BREED_DICTIONARY_KO_README.md
database/contents/dog_api/dog_images_110.csv
database/contents/dog_api/dog_images_110.json
database/tools/build_RDB.py
```

웹 작업 파일: ((동혁님과 겹치지 않는 선에서 수정했습니다!))

```text
web/config/settings.py (database sqlite3 -> PostgreSQL 변경 위해 수정)
web/dog/models.py
web/dog/services.py
web/dog/views.py
web/dog/urls.py
web/templates/dog/search.html
web/templates/dog/detail.html
```

## 요약

```text
최종 DB 적재 파일: dog_images_110.json
최종 CSV: dog_images_110.csv
DB: PostgreSQL pet_dog
테이블: dog_breed_dictionary_ko
총 견종 수: 110
이미지URL 있음: 110
이미지URL 없음: 0
견종그룹: 한국 기준 10그룹
```
