from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from django.http import HttpRequest, HttpResponse
from django.shortcuts import render


PROJECT_DIR = Path(__file__).resolve().parents[2]
GUIDE_DATA_PATH = PROJECT_DIR / "database" / "guide" / "processed" / "guide_sections.json"
DEFAULT_TOPIC = "adoption-ready"


def _load_guide_sections() -> list[dict[str, Any]]:
    with GUIDE_DATA_PATH.open("r", encoding="utf-8-sig") as file:
        return json.load(file)


def guide_page(request: HttpRequest) -> HttpResponse:
    guides = _load_guide_sections()
    requested_topic = request.GET.get("topic", DEFAULT_TOPIC)
    selected_guide = next((guide for guide in guides if guide["slug"] == requested_topic), guides[0])

    return render(
        request,
        "guide/guide.html",
        {
            "guides": guides,
            "selected_guide": selected_guide,
        },
    )


