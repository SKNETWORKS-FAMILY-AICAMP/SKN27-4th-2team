# 유기견/보호동물 데이터 형태 정의

이 문서는 공공데이터포털 `국가동물보호정보시스템 구조동물 조회 서비스` 응답을 프로젝트에서 사용하는 형태로 정리한 기준이다.

## 원본 API 주요 필드

| 원본 필드 | 의미 | 프로젝트 활용 |
| --- | --- | --- |
| `desertionNo` | 유기번호/고유 식별자 | DB unique key, 상세 id |
| `noticeNo` | 공고번호 | 상세 정보 표시 |
| `happenDt` | 발견일 | 필터/상세 정보 |
| `happenPlace` | 발견 장소 | 상세 정보 |
| `kindFullNm` | 전체 품종명 예: `[개] 말티즈` | 카드 제목, 추천 견종 매칭 |
| `kindNm` | 품종명 예: `말티즈` | 카드 제목, 추천 견종 매칭 |
| `kindCd` | 품종 코드 | API 조회/DB 필터 |
| `upKindCd` | 축종 코드 | 강아지 `417000` |
| `upKindNm` | 축종명 | `개` |
| `colorCd` | 색상 | 상세 정보 |
| `age` | 나이 | 카드/상세 정보 |
| `weight` | 체중 | 상세 정보 |
| `sexCd` | 성별 코드 | `M=수컷`, `F=암컷`, `Q=미상` |
| `neuterYn` | 중성화 여부 | `Y=예`, `N=아니오`, `U=미상` |
| `specialMark` | 특징 | 상세 정보 |
| `careRegNo` | 보호소 등록번호 | 보호소 상세 연결 |
| `careNm` | 보호소명 | 카드/상세 정보 |
| `careTel` | 보호소 전화번호 | 문의 버튼 |
| `careAddr` | 보호소 주소 | 상세 정보/지도 확장 |
| `orgNm` | 관할 기관/지역명 | 지역 필터 |
| `noticeSdt` | 공고 시작일 | 공고기간 표시 |
| `noticeEdt` | 공고 종료일 | 공고기간 표시 |
| `processState` | 처리상태 | 상태 배지/필터 |
| `popfile1` | 대표 이미지 URL | 카드/상세 이미지 |
| `popfile2` | 추가 이미지 URL | 상세 이미지 확장 |
| `updTm` | API 데이터 수정 시각 | 갱신 판단 |

## 프로젝트 내부 표준 형태

화면과 API 응답에서는 아래 형태를 우선 사용한다.

```json
{
  "id": "desertionNo",
  "notice_no": "noticeNo",
  "breed": "kindFullNm/kindNm에서 [개] 접두어를 제거한 품종명",
  "raw_breed": "원본 kindFullNm 또는 kindNm",
  "age": "나이",
  "sex": "수컷/암컷/미상",
  "sex_code": "M/F/Q",
  "neutered": "예/아니오/미상",
  "neuter_code": "Y/N/U",
  "color": "색상",
  "weight": "체중",
  "image_url": "popfile1 우선",
  "thumbnail_url": "목록 카드용 이미지 URL",
  "happen_place": "발견 장소",
  "special_mark": "특징",
  "shelter_name": "보호소명",
  "shelter_tel": "보호소 전화번호",
  "shelter_address": "보호소 주소",
  "notice_start_date": "공고 시작일",
  "notice_end_date": "공고 종료일",
  "status": "처리상태",
  "raw": "원본 응답 전체"
}
```

## DB 적재 기준

전체 적재 시에는 공공데이터 원본 필드를 최대한 보존한다.

핵심 원칙:

```text
화면에 필요한 정규화 필드만 저장하지 않는다.
원본 raw_data JSONB를 반드시 함께 저장한다.
desertionNo를 unique key로 사용한다.
상태 변경에 대비해 upsert 방식으로 적재한다.
```

추천 테이블명:

```text
shelter_animals
```

자세한 테이블 설계와 적재 흐름은 `database/animal_protection/README.md`를 참고한다.

## 추천 견종과 연결하는 방식

```text
추천 결과 견종명
-> database/animal_protection/breed_mapping.json
-> database/animal_protection/breed_code_mapping.json
-> kind_cd 확인
-> shelter_animals 테이블에서 kind_cd 기준 조회
```

초기 API 실시간 조회 방식에서는 `kind_cd`를 공공 API `kind` 파라미터로 전달한다.

전체 DB 적재 후에는 공공 API를 매번 호출하지 않고 `shelter_animals` 테이블에서 조회한다.

## 화면 MVP 기준

추천 결과 하단에는 최대 3개만 노출한다.

```text
image_url
breed
age
sex
shelter_name
shelter_address
notice_start_date
notice_end_date
status
id
```

별도 보호동물 페이지에서는 목록 카드와 상세 패널에서 같은 표준 형태를 사용한다.
