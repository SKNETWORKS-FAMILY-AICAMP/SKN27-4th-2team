from __future__ import annotations

import argparse
import html
import json
import os
import re
import sys
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any


PROJECT_DIR = Path(__file__).resolve().parents[2]
WEB_DIR = PROJECT_DIR / "web"
REPORT_DIR = PROJECT_DIR / "reports" / "chatbot_quality"
UUID_PATTERN = re.compile(
    r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class Scenario:
    name: str
    question: str
    expected_intent: str
    must_include_any: list[str] = field(default_factory=list)
    must_not_include: list[str] = field(default_factory=list)
    source_must_include_any: list[str] = field(default_factory=list)
    top_source_must_include_any: list[str] = field(default_factory=list)


SCENARIOS = [
    Scenario(
        name="second_dog_with_pomeranian",
        question="내가 포메라니언을 키우는 중인데, 한마리 강아지를 더 분양받으려고 해. 어떤 점을 고려해야 해?",
        expected_intent="일반 상담",
        must_include_any=["포메라니언", "사회화", "성격", "합사", "천천히", "적응"],
        must_not_include=["오류", "UUID"],
    ),
    Scenario(
        name="apartment_breed_recommendation",
        question="아파트에서 키우기 쉬운 견종 추천해줘",
        expected_intent="견종 추천",
        must_include_any=["아파트", "견종", "적응", "에너지", "짖"],
        must_not_include=["/shelter/?breed=", "Q&A 참고 문서"],
        source_must_include_any=["AKC", "Apartment Recommendation"],
    ),
    Scenario(
        name="shelter_adoption_process",
        question="유기견 입양 절차를 알고 싶어",
        expected_intent="일반 상담",
        must_include_any=["입양", "보호소", "신청", "준비", "적응"],
        must_not_include=["YouTube Q&A - YouTube Q&A", "Q&A 참고 문서"],
        source_must_include_any=["YouTube", "강형욱", "설채현"],
        top_source_must_include_any=["입양", "보호소", "분양"],
    ),
    Scenario(
        name="food_amount_calculation",
        question="강아지 사료 급여량은 어떻게 계산해?",
        expected_intent="일반 상담",
        must_include_any=["체중", "칼로리", "사료", "급여", "활동량"],
        must_not_include=["오류", "Q&A 참고 문서"],
        top_source_must_include_any=["사료", "급여", "영양", "칼로리", "다이어트"],
    ),
    Scenario(
        name="training_priority",
        question="강아지 훈련할 때 가장 중요한 게 뭐야?",
        expected_intent="일반 상담",
        must_include_any=["훈련", "일관", "보상", "칭찬", "반복"],
        must_not_include=["오류", "Q&A 참고 문서"],
        top_source_must_include_any=["훈련", "교육", "기다려", "보상"],
    ),
]


def main() -> int:
    parser = argparse.ArgumentParser(description="Run Pet Mate chatbot quality scenarios.")
    parser.add_argument("--no-screenshots", action="store_true", help="Skip Playwright screenshot capture.")
    parser.add_argument("--output-dir", type=Path, default=None)
    args = parser.parse_args()

    output_dir = args.output_dir or REPORT_DIR / datetime.now().strftime("%Y%m%d_%H%M%S")
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "screenshots").mkdir(exist_ok=True)

    setup_django()

    results = []
    for index, scenario in enumerate(SCENARIOS, start=1):
        print(f"[{index}/{len(SCENARIOS)}] {scenario.question}")
        results.append(run_scenario(index, scenario))

    json_path = output_dir / "chatbot_quality_results.json"
    html_path = output_dir / "chatbot_quality_report.html"
    json_path.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
    html_path.write_text(render_report(results), encoding="utf-8")

    screenshot_paths: list[str] = []
    if not args.no_screenshots:
        screenshot_paths = capture_screenshots(html_path, output_dir / "screenshots")

    summary = {
        "passed": sum(1 for result in results if result["passed"]),
        "failed": sum(1 for result in results if not result["passed"]),
        "json": str(json_path),
        "html": str(html_path),
        "screenshots": screenshot_paths,
    }
    summary_path = output_dir / "summary.json"
    summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")

    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0 if summary["failed"] == 0 else 1


def setup_django() -> None:
    sys.path.insert(0, str(PROJECT_DIR))
    sys.path.insert(0, str(WEB_DIR))
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

    import django

    django.setup()


def run_scenario(index: int, scenario: Scenario) -> dict[str, Any]:
    from django.test import RequestFactory
    from chatbot.views import build_reply

    request = RequestFactory().post("/chatbot/", HTTP_HOST="127.0.0.1:8000")
    reply = build_reply(scenario.question, request=request)
    answer = str(reply.get("answer") or "")
    sources = list(reply.get("sources") or [])
    intent = str(reply.get("intent") or "")

    visible_source_text = json.dumps(
        [
            {
                "display_title": source.get("display_title"),
                "title": source.get("title"),
                "source": source.get("source"),
                "url": source.get("url"),
            }
            for source in sources
        ],
        ensure_ascii=False,
    )
    top_source_title = ""
    if sources:
        top_source_title = str(
            sources[0].get("display_title")
            or sources[0].get("title")
            or sources[0].get("source")
            or ""
        )

    checks = [
        check("intent", intent == scenario.expected_intent, f"expected={scenario.expected_intent}, actual={intent}"),
        check("answer_length", len(answer.strip()) >= 80, f"length={len(answer.strip())}"),
        check("no_uuid_in_answer", UUID_PATTERN.search(answer) is None, "answer contains UUID"),
        check(
            "no_uuid_in_visible_sources",
            UUID_PATTERN.search(visible_source_text) is None,
            "visible source title/url contains UUID",
        ),
        check(
            "no_duplicate_qna_label",
            "YouTube Q&A - YouTube Q&A" not in visible_source_text,
            "visible source contains duplicated YouTube Q&A label",
        ),
    ]

    if scenario.must_include_any:
        checks.append(
            check(
                "answer_keyword",
                any(keyword in answer for keyword in scenario.must_include_any),
                f"one of={scenario.must_include_any}",
            )
        )

    for forbidden in scenario.must_not_include:
        checks.append(check(f"not_include:{forbidden}", forbidden not in answer, forbidden))

    if scenario.source_must_include_any:
        checks.append(
            check(
                "source_keyword",
                any(keyword in visible_source_text for keyword in scenario.source_must_include_any),
                f"one of={scenario.source_must_include_any}",
            )
        )

    if scenario.top_source_must_include_any:
        checks.append(
            check(
                "top_source_relevance",
                any(keyword in top_source_title for keyword in scenario.top_source_must_include_any),
                f"top_source={top_source_title}, expected one of={scenario.top_source_must_include_any}",
            )
        )

    return {
        "index": index,
        "name": scenario.name,
        "question": scenario.question,
        "expected_intent": scenario.expected_intent,
        "intent": intent,
        "answer": answer,
        "sources": sources,
        "checks": checks,
        "passed": all(item["passed"] for item in checks),
    }


def check(name: str, passed: bool, detail: str = "") -> dict[str, Any]:
    return {"name": name, "passed": bool(passed), "detail": detail}


def render_report(results: list[dict[str, Any]]) -> str:
    cards = []
    for result in results:
        status = "PASS" if result["passed"] else "FAIL"
        sources = "".join(
            f"<li>{html.escape(str(source.get('display_title') or source.get('title') or source.get('source')))}</li>"
            for source in result["sources"]
        )
        checks = "".join(
            f"<li class=\"{'ok' if item['passed'] else 'bad'}\">{html.escape(item['name'])}: "
            f"{'PASS' if item['passed'] else 'FAIL'}"
            f"{' - ' + html.escape(item['detail']) if item.get('detail') else ''}</li>"
            for item in result["checks"]
        )
        cards.append(
            f"""
            <section class="card" id="case-{result['index']}">
              <div class="case-head">
                <span class="status {'ok' if result['passed'] else 'bad'}">{status}</span>
                <span>Case {result['index']}: {html.escape(result['name'])}</span>
              </div>
              <h2>{html.escape(result['question'])}</h2>
              <p class="intent">Intent: {html.escape(result['intent'])}</p>
              <pre>{html.escape(result['answer'])}</pre>
              <h3>참고한 정보</h3>
              <ul>{sources or '<li>없음</li>'}</ul>
              <h3>Checks</h3>
              <ul>{checks}</ul>
            </section>
            """
        )

    passed = sum(1 for result in results if result["passed"])
    failed = len(results) - passed
    return f"""<!doctype html>
<html lang="ko">
<head>
  <meta charset="utf-8">
  <title>Pet Mate Chatbot Quality Report</title>
  <style>
    body {{ margin: 0; padding: 32px; font-family: Arial, 'Noto Sans KR', sans-serif; background: #f6f6f3; color: #151515; }}
    header {{ margin-bottom: 24px; }}
    h1 {{ margin: 0 0 8px; font-size: 28px; }}
    .summary {{ color: #555; }}
    .card {{ margin: 0 0 24px; padding: 24px; border: 1px solid #ddd; border-radius: 16px; background: white; page-break-after: always; }}
    .case-head {{ display: flex; gap: 10px; align-items: center; font-weight: 700; }}
    .status {{ padding: 4px 8px; border-radius: 999px; font-size: 12px; color: white; }}
    .status.ok {{ background: #0a7a30; }}
    .status.bad {{ background: #b42318; }}
    h2 {{ font-size: 20px; }}
    .intent {{ font-weight: 700; }}
    pre {{ white-space: pre-wrap; line-height: 1.55; padding: 16px; border-radius: 12px; background: #fafafa; }}
    li {{ margin: 4px 0; }}
    li.ok {{ color: #0a7a30; }}
    li.bad {{ color: #b42318; font-weight: 700; }}
  </style>
</head>
<body>
  <header>
    <h1>Pet Mate Chatbot Quality Report</h1>
    <div class="summary">Passed: {passed} / Failed: {failed} / Total: {len(results)}</div>
  </header>
  {''.join(cards)}
</body>
</html>"""


def capture_screenshots(html_path: Path, screenshot_dir: Path) -> list[str]:
    try:
        from playwright.sync_api import sync_playwright
    except Exception as error:  # pragma: no cover - diagnostic path
        print(f"[screenshot skipped] playwright import failed: {error}")
        return []

    paths: list[str] = []
    with sync_playwright() as playwright:
        browser = None
        for launch_args in ({"channel": "msedge"}, {"channel": "chrome"}, {}):
            try:
                browser = playwright.chromium.launch(headless=True, **launch_args)
                break
            except Exception:
                continue
        if browser is None:
            print("[screenshot skipped] no chromium-compatible browser is available")
            return []

        page = browser.new_page(viewport={"width": 1200, "height": 900}, device_scale_factor=1)
        page.goto(html_path.resolve().as_uri())
        page.screenshot(path=str(screenshot_dir / "full_report.png"), full_page=True)
        paths.append(str(screenshot_dir / "full_report.png"))

        for case in range(1, len(SCENARIOS) + 1):
            locator = page.locator(f"#case-{case}")
            path = screenshot_dir / f"case_{case:02d}.png"
            locator.screenshot(path=str(path))
            paths.append(str(path))

        browser.close()
    return paths


if __name__ == "__main__":
    raise SystemExit(main())
