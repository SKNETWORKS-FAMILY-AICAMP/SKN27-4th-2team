# 한글 견종도감 CSV 전처리 기록

## 결과 파일

```text
database/contents/dog_api/dogapi_akc_matched_breeds_ko.csv
```

이 파일은 견종도감 페이지에서 바로 사용할 수 있도록 영문 원본 데이터를 한글화하고, 단위를 한국 서비스 기준으로 변환한 CSV다.

## 원본 파일

```text
database/contents/dog_api/dogapi_akc_matched_breeds.csv
```

원본은 Dog API 데이터와 AKC 데이터를 견종명 기준으로 매칭한 파일이다.

## 전처리 방향

중복되는 평균수명, 체중, 키 정보는 AKC 기준 컬럼만 사용했다.

원본에서 Dog API 쪽 중복 컬럼은 제거했다.

```text
dogapi_life_span
dogapi_weight_metric
dogapi_height_metric
```

AKC 기준 컬럼은 유지했다.

```text
akc_life_expectancy_min
akc_life_expectancy_max
akc_weight_min
akc_weight_max
akc_height_min
akc_height_max
```

단, AKC의 체중과 키는 미국 단위 기준이므로 한글 CSV 생성 시 다음처럼 변환했다.

```text
weight: lb -> kg
height: inch -> cm
```

변환식:

```text
1 lb = 0.453592 kg
1 inch = 2.54 cm
```

예:

```text
7-10 lb -> 3.2-4.5 kg
9-11.5 inch -> 22.9-29.2 cm
```

## 생성 스크립트

한글 CSV의 1차 생성은 아래 스크립트로 수행했다.

```text
database/contents/dog_api/build_korean_breed_csv.py
```

역할:

```text
1. dogapi_akc_matched_breeds.csv 읽기
2. OpenAI API로 텍스트 컬럼 한글 번역
3. AKC 체중 lb 값을 kg으로 변환
4. AKC 키 inch 값을 cm로 변환
5. 화면 표시용 한글 컬럼명으로 새 CSV 생성
```

생성 결과:

```text
database/contents/dog_api/dogapi_akc_matched_breeds_ko.csv
```

## OpenAI API로 번역한 항목

긴 설명문과 일반 텍스트는 OpenAI API를 사용해 한글화했다.

주요 번역 대상:

```text
matched_breed_name
dogapi_breed_group
dogapi_temperament
dogapi_origin
akc_coat_type_array
akc_coat_length_array
akc_colors_array
akc_markings_array
akc_about_the_breed
akc_health
akc_grooming
akc_exercise
akc_training
akc_nutrition
akc_history
```

긴 설명문은 다음 한글 컬럼으로 저장했다.

```text
견종소개
건강
미용
운동
훈련
영양
역사
```

## 단위 변환 컬럼

원본 AKC 컬럼:

```text
akc_weight_min
akc_weight_max
akc_height_min
akc_height_max
```

한글 CSV 컬럼:

```text
체중_최소_kg
체중_최대_kg
키_최소_cm
키_최대_cm
```

평균수명은 AKC의 최소/최대 값을 그대로 사용했다.

```text
평균수명_최소_년
평균수명_최대_년
```

## 매핑 사전 적용

AI 번역만 사용할 경우 짧은 카테고리 값이 어색하게 번역될 수 있다.

예:

```text
Toy -> 장난감
```

이를 방지하기 위해 고정 매핑 사전을 추가 적용했다.

매핑 적용 스크립트:

```text
database/contents/dog_api/apply_korean_mapping_dictionary.py
```

매핑 대상:

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

성격 예:

```text
Confident -> 자신감 있는
Alert -> 경계심이 있는
Playful -> 장난기 많은
Loyal -> 충성심 강한
Courageous -> 용감한
```

털 정보 예:

```text
Wiry -> 뻣뻣한 털
Silky -> 비단결 털
Double -> 이중모
Short -> 짧은 털
Medium -> 중간 길이 털
Long -> 긴 털
Black -> 검정
White -> 흰색
Red -> 붉은색
Tan -> 탄색
```

## 출신 컬럼 정리

원본 `dogapi_origin`은 도시, 지역, 국가가 섞여 있었다.

예:

```text
Yorkshire, England
Wasilla, Alaska, United States
Malta, Mediterranean Basin
West Africa (Sahel region: Mali, Niger, Burkina Faso)
```

한글 CSV에서는 `출신` 컬럼에 국가명만 남기도록 정리했다.

예:

```text
Yorkshire, England -> 영국
Wasilla, Alaska, United States -> 미국
Malta, Mediterranean Basin -> 몰타
West Africa (Sahel region: Mali, Niger, Burkina Faso) -> 말리, 니제르, 부르키나파소
```

## 최종 컬럼

```text
견종명_영문
견종명_한글
dogapi_id
견종그룹
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

OpenAI API 키가 `.env`에 있어야 한다.

```text
OPENAI_API_KEY=...
```

1차 한글 CSV 생성:

```powershell
python database\contents\dog_api\build_korean_breed_csv.py
```

고정 매핑 사전 적용:

```powershell
python database\contents\dog_api\apply_korean_mapping_dictionary.py
```

JSON 파일이 필요하면 CSV를 JSON으로 변환한다.

```text
database/contents/dog_api/dogapi_akc_matched_breeds_ko.json
```

## 검증 결과

최종 CSV 기준:

```text
행 수: 256
견종그룹에 '그룹' 포함: 0건
짧은 표시 컬럼에 '장난감' 표현: 0건
AKC 체중: kg 변환 완료
AKC 키: cm 변환 완료
```

첫 행 예:

```text
견종명_영문: Affenpinscher
견종명_한글: 아펜핀셔
견종그룹: 토이
출신: 독일
체중: 3.2-4.5kg
키: 22.9-29.2cm
```
