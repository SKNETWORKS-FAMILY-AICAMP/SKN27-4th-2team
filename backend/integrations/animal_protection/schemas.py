"""Typed shapes for rescued/protected animal data used by the app."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


SEX_LABELS = {"M": "수컷", "F": "암컷", "Q": "미상"}
NEUTER_LABELS = {"Y": "예", "N": "아니오", "U": "미상"}


@dataclass(frozen=True)
class ShelterAnimal:
    """Normalized structure for one protected animal card/detail view."""

    id: str
    notice_no: str
    breed: str
    raw_breed: str
    age: str
    sex: str
    sex_code: str
    neutered: str
    neuter_code: str
    color: str
    weight: str
    image_url: str
    thumbnail_url: str
    happen_place: str
    special_mark: str
    shelter_name: str
    shelter_tel: str
    shelter_address: str
    notice_start_date: str
    notice_end_date: str
    status: str
    charge_name: str
    office_tel: str
    raw: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def clean_breed_name(value: str | None) -> str:
    """Convert public API breed text like '[개] 말티즈' into '말티즈'."""
    if not value:
        return ""
    cleaned = value.strip()
    for prefix in ("[개]", "[고양이]", "[기타축종]"):
        cleaned = cleaned.replace(prefix, "")
    return cleaned.strip()
