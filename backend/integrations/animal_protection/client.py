"""Client for data.go.kr animal protection APIs.

This module intentionally does not modify existing app code. It is a small
integration layer that can later be imported by Django views or services.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any
from urllib.parse import urlencode
from urllib.request import urlopen

from .schemas import NEUTER_LABELS, SEX_LABELS, ShelterAnimal, clean_breed_name


ABANDONMENT_BASE_URL = "https://apis.data.go.kr/1543061/abandonmentPublicService_v2"
SHELTER_BASE_URL = "https://apis.data.go.kr/1543061/animalShelterSrvc_v2"
DOG_UP_KIND_CODE = "417000"


class AnimalProtectionClient:
    def __init__(self, service_key: str | None = None, timeout: int = 20) -> None:
        self.service_key = service_key or os.getenv("ANIMAL_API_SERVICE_KEY", "")
        self.timeout = timeout
        if not self.service_key:
            raise RuntimeError("ANIMAL_API_SERVICE_KEY is not set.")

    def get_sido(self, *, page_no: int = 1, num_of_rows: int = 50) -> dict[str, Any]:
        return self._get_abandonment("sido_v2", pageNo=page_no, numOfRows=num_of_rows)

    def get_sigungu(self, upr_cd: str, *, page_no: int = 1, num_of_rows: int = 100) -> dict[str, Any]:
        return self._get_abandonment("sigungu_v2", upr_cd=upr_cd, pageNo=page_no, numOfRows=num_of_rows)

    def get_kind(self, up_kind_cd: str = DOG_UP_KIND_CODE, *, page_no: int = 1, num_of_rows: int = 300) -> dict[str, Any]:
        return self._get_abandonment("kind_v2", up_kind_cd=up_kind_cd, pageNo=page_no, numOfRows=num_of_rows)

    def get_abandonments(self, **params: Any) -> dict[str, Any]:
        defaults = {"upkind": DOG_UP_KIND_CODE, "pageNo": 1, "numOfRows": 10}
        defaults.update({key: value for key, value in params.items() if value not in (None, "")})
        return self._get_abandonment("abandonmentPublic_v2", **defaults)

    def get_shelter_info(self, **params: Any) -> dict[str, Any]:
        return self._request(f"{SHELTER_BASE_URL}/shelterInfo_v2", params)

    def _get_abandonment(self, operation: str, **params: Any) -> dict[str, Any]:
        return self._request(f"{ABANDONMENT_BASE_URL}/{operation}", params)

    def _request(self, url: str, params: dict[str, Any]) -> dict[str, Any]:
        query = {"serviceKey": self.service_key, "_type": "json", **params}
        request_url = f"{url}?{urlencode(query)}"
        with urlopen(request_url, timeout=self.timeout) as response:
            payload = response.read().decode("utf-8")
        return json.loads(payload)


def extract_items(response: dict[str, Any] | None) -> list[dict[str, Any]]:
    if not response:
        return []
    body = response.get("response", {}).get("body", {})
    items = body.get("items", {})
    item = items.get("item", []) if isinstance(items, dict) else []
    if isinstance(item, dict):
        return [item]
    if isinstance(item, list):
        return item
    return []


def normalize_abandonment_item(item: dict[str, Any]) -> ShelterAnimal:
    raw_breed = str(item.get("kindFullNm") or item.get("kindNm") or item.get("kindCd") or "")
    sex_code = str(item.get("sexCd", ""))
    neuter_code = str(item.get("neuterYn", ""))
    image_url = str(item.get("popfile") or item.get("popfile1") or item.get("filename") or "")

    return ShelterAnimal(
        id=str(item.get("desertionNo", "")),
        notice_no=str(item.get("noticeNo", "")),
        breed=clean_breed_name(raw_breed),
        raw_breed=raw_breed,
        age=str(item.get("age", "")),
        sex=SEX_LABELS.get(sex_code, sex_code or "미상"),
        sex_code=sex_code,
        neutered=NEUTER_LABELS.get(neuter_code, neuter_code or "미상"),
        neuter_code=neuter_code,
        color=str(item.get("colorCd", "")),
        weight=str(item.get("weight", "")),
        image_url=image_url,
        thumbnail_url=image_url,
        happen_place=str(item.get("happenPlace", "")),
        special_mark=str(item.get("specialMark", "")),
        shelter_name=str(item.get("careNm", "")),
        shelter_tel=str(item.get("careTel", "")),
        shelter_address=str(item.get("careAddr", "")),
        notice_start_date=str(item.get("noticeSdt", "")),
        notice_end_date=str(item.get("noticeEdt", "")),
        status=str(item.get("processState", "")),
        charge_name=str(item.get("chargeNm", "")),
        office_tel=str(item.get("officetel", "")),
        raw=item,
    )


def normalize_abandonments(response: dict[str, Any]) -> list[dict[str, Any]]:
    return [normalize_abandonment_item(item).to_dict() for item in extract_items(response)]


def load_dotenv_file(path: str | Path) -> None:
    """Minimal .env loader for scripts, avoiding extra runtime assumptions."""
    env_path = Path(path)
    if not env_path.exists():
        return
    for line in env_path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, value = stripped.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))

