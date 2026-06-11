# 견종도감 데이터 전처리 기록

Dog API와 AKC 데이터를 기반으로 견종도감 화면에서 사용할 한글 데이터를 만든 과정이다.

## 최종 공유 파일

현재 팀 공유 및 DB 적재 기준 최종 파일은 아래 2개다.

```text
database/contents/dog_api/dog_images_110.csv
database/contents/dog_api/dog_images_110.json
```

상태:

```text
전체 견종 수: 110
이미지URL 있음: 110
이미지URL 없음: 0
```

이미지 URL이 없는 견종은 최종 공유 파일에서 제외했다.

DB 적재는 JSON 파일을 사용한다.

```powershell
python database\tools\build_RDB.py --json database\contents\dog_api\dog_images_110.json --truncate
```

## 원본 파일

```text
database/contents/dog_api/dogapi_akc_matched_breeds.csv
```

원본은 Dog API 데이터와 AKC 데이터를 견종명 기준으로 매칭한 CSV다.

## 1차 한글 전처리

생성 파일:

```text
database/contents/dog_api/dogapi_akc_matched_breeds_ko.csv
```

생성 스크립트:

```text
database/contents/dog_api/build_korean_breed_csv.py
```

처리 내용:

```text
1. 영문 텍스트를 OpenAI API로 한글 번역
2. 컬럼명을 견종도감에서 쓰기 쉬운 한글명으로 변경
3. AKC 체중 lb 값을 kg으로 변환
4. AKC 키 inch 값을 cm로 변환
5. 출신, 성격, 털 타입, 털 길이 등 짧은 값은 매핑 사전으로 정리
```

단위 변환:

```text
1 lb = 0.453592 kg
1 inch = 2.54 cm
```

중복 컬럼 처리:

```text
평균수명, 체중, 키는 Dog API 값 대신 AKC 기준 컬럼만 사용
```

제거한 Dog API 중복 컬럼:

```text
dogapi_life_span
dogapi_weight_metric
dogapi_height_metric
```

유지한 AKC 기준 컬럼:

```text
akc_life_expectancy_min
akc_life_expectancy_max
akc_weight_min
akc_weight_max
akc_height_min
akc_height_max
```

## 고정 매핑 사전 적용

AI 번역만 사용하면 짧은 카테고리 값이 어색하게 번역될 수 있어 고정 매핑 사전을 추가 적용했다.

사용 스크립트:

```text
database/contents/dog_api/apply_korean_mapping_dictionary.py
```

주요 대상:

```text
견종그룹
성격
출신
털_타입
털_길이
털_색상
무늬
```

예:

```text
Toy -> 토이
Hound -> 하운드
Terrier -> 테리어
Working -> 워킹
Sporting -> 스포팅
Herding -> 목양견
Non-Sporting -> 논스포팅
```

출신 컬럼은 국가 이름만 남기도록 정리했다.

예:

```text
Yorkshire, England -> 영국
Wasilla, Alaska, United States -> 미국
Malta, Mediterranean Basin -> 몰타
```

## 한국 기준 10그룹 재분류

AKC 그룹명은 국내 사용자에게 익숙하지 않아 한국애견연맹/FCI식 10그룹 기준으로 다시 분류했다.

중간 생성 파일:

```text
database/contents/dog_api/dogapi_akc_matched_breeds_ko_kc10groups.csv
database/contents/dog_api/dogapi_akc_matched_breeds_ko_kc10groups.json
```

생성 스크립트:

```text
database/contents/dog_api/build_korean_10group_csv.py
```

참고한 견종그룹 설명 출처:

```text
한국애견연맹 견종그룹 설명
https://www.thekkf.or.kr/new_home/07_dogshow/01_about_dogshow_3.php
```

기존 `견종그룹` 컬럼은 AKC 기준 값이므로 최종 10그룹 파일에서는 삭제했다.

추가 컬럼:

```text
견종그룹번호
견종그룹명
견종그룹설명
```

10그룹 명칭:

```text
1, 쉽독·캐틀독
2, 핀셔·슈나우저·몰로시안·스위스 캐틀독
3, 테리어
4, 닥스훈트
5, 스피츠·프리미티브
6, 센트하운드
7, 포인팅 독
8, 리트리버·플러싱독·워터독
9, 컴패니언·토이 독
10, 사이트하운드
```

분류 예:

```text
Border Collie -> 1 / 쉽독·캐틀독
Bulldog -> 2 / 핀셔·슈나우저·몰로시안·스위스 캐틀독
Yorkshire Terrier -> 3 / 테리어
Dachshund -> 4 / 닥스훈트
Akita -> 5 / 스피츠·프리미티브
Beagle -> 6 / 센트하운드
Golden Retriever -> 8 / 리트리버·플러싱독·워터독
Maltese -> 9 / 컴패니언·토이 독
Afghan Hound -> 10 / 사이트하운드
```

10그룹 파일 검증 결과:

```text
전체 행 수: 256
견종그룹번호 생성 완료
견종그룹명 생성 완료
견종그룹설명 생성 완료
견종그룹설명 빈 값: 0건
```

그룹별 분포:

```text
1그룹: 32건
2그룹: 44건
3그룹: 35건
4그룹: 1건
5그룹: 44건
6그룹: 25건
7그룹: 23건
8그룹: 20건
9그룹: 22건
10그룹: 10건
```

## 이미지 URL 검수

기존 Dog API 이미지 중 일부가 견종과 맞지 않아 이미지 URL을 재검토했다.

검토한 이미지 API:

```text
Dog CEO API
TheDogAPI
API Ninjas Dogs API
```

처리 원칙:

```text
1. 정확하다고 확인한 이미지 URL만 사용
2. 확신하기 어려운 이미지는 사용하지 않음
3. 이미지 URL이 없는 견종은 최종 공유 파일에서 제외
```

이미지 검토 후 최종 공유 파일:

```text
database/contents/dog_api/dog_images_110.csv
database/contents/dog_api/dog_images_110.json
```

최종 상태:

```text
전체 견종 수: 110
이미지URL 있음: 110
이미지URL 없음: 0
```

## 최종 컬럼

최종 공유 CSV의 주요 컬럼:

```text
견종명_영문
견종명_한글
dogapi_id
견종그룹번호
견종그룹명
견종그룹설명
성격
출신
이미지URL
키_최소_cm
키_최대_cm
체중_최소_kg
체중_최대_kg
평균수명_최소_년
평균수명_최대_년
가족_친화도_점수
어린이_친화도_점수
다른개_친화도_점수
털빠짐_수준_점수
미용_필요도_점수
침흘림_수준_점수
낯선사람_친화도_점수
장난기_수준_점수
경비_보호본능_점수
적응력_점수
훈련_용이성_점수
에너지_수준_점수
짖는_수준_점수
지적자극_필요도_점수
털_타입
털_길이
털_색상
무늬
견종소개
건강
미용
운동
훈련
영양
역사
```

## 재생성 순서

필요 환경 변수:

```text
OPENAI_API_KEY=...
DOG_API_KEY=...
API_NINJAS_KEY=...
```

1차 한글 CSV 생성:

```powershell
python database\contents\dog_api\build_korean_breed_csv.py
```

고정 매핑 사전 적용:

```powershell
python database\contents\dog_api\apply_korean_mapping_dictionary.py
```

한국 기준 10그룹 CSV 생성:

```powershell
python database\contents\dog_api\build_korean_10group_csv.py
```

최종 DB 적재:

```powershell
python database\tools\build_RDB.py --json database\contents\dog_api\dog_images_110.json
```

## 참고

DB 적재 및 Django 웹 연결 절차는 아래 문서를 기준으로 한다.

```text
database/DOG_BREED_DICTIONARY_KO_README.md
```
