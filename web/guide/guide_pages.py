from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from django.http import HttpRequest, HttpResponse
from django.shortcuts import render
from django.templatetags.static import static


PROJECT_DIR = Path(__file__).resolve().parents[2]
GUIDE_DATA_PATH = PROJECT_DIR / "database" / "guide" / "processed" / "guide_sections.json"
DEFAULT_TOPIC = "adoption-ready"
GUIDE_SOURCE_PDFS = {
    "[별지 5] 입양 설문지": "guide/pdfs/adoption-survey.pdf",
    "[별지 6] 입양 신청서": "guide/pdfs/adoption-application.pdf",
    "별첨 5. 반려견 공공예절교육": "guide/pdfs/public-manners.pdf",
    "반려동물 가족을 위한 재난 대응 가이드라인(국민용)": "guide/pdfs/disaster-response.pdf",
    "건강한 반려문화 조성을 위한 행동지도 윤리 가이드라인": "guide/pdfs/behavior-guidance-ethics.pdf",
    "건강한 반려문화 조성을 위한 행동지도 윤리 가이드북": "guide/pdfs/behavior-guidance-handbook.pdf",
    "맹견·사고견 행동지도 프로그램": "guide/pdfs/dangerous-dog-program.pdf",
    "맹견·사고견 훈련과정 설계 및 운영지침": "guide/pdfs/dangerous-dog-training-guide.pdf",
}


def _load_guide_sections() -> list[dict[str, Any]]:
    with GUIDE_DATA_PATH.open("r", encoding="utf-8-sig") as file:
        return json.load(file)


def _attach_source_pdf_links(guide: dict[str, Any]) -> dict[str, Any]:
    guide_with_links = {**guide}
    guide_with_links["sources"] = [
        {
            "label": source,
            "pdf_url": static(pdf_path) if (pdf_path := GUIDE_SOURCE_PDFS.get(source)) else None,
        }
        for source in guide.get("sources", [])
    ]
    return guide_with_links


def guide_page(request: HttpRequest) -> HttpResponse:
    guides = _load_guide_sections()
    requested_topic = request.GET.get("topic", DEFAULT_TOPIC)
    selected_guide = next((guide for guide in guides if guide["slug"] == requested_topic), guides[0])
    selected_guide = _attach_source_pdf_links(selected_guide)

    return render(
        request,
        "guide/guide.html",
        {
            "guides": guides,
            "selected_guide": selected_guide,
        },
    )
