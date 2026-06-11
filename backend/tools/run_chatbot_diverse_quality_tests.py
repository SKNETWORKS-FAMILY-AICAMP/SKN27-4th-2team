from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path

import run_chatbot_quality_tests as base_quality_tests
from run_chatbot_quality_tests import (
    REPORT_DIR,
    Scenario,
    capture_screenshots,
    render_report,
    run_scenario,
    setup_django,
)


DIVERSE_SCENARIOS = [
    Scenario(
        name="second_dog_with_pomeranian",
        question="내가 포메라니언을 키우는 중인데, 한마리 강아지를 더 분양받으려고 해. 어떤 점을 고려해야 해?",
        expected_intent="일반 상담",
        must_include_any=["포메라니언", "사회화", "성격", "합사", "천천히", "적응"],
        must_not_include=["오류", "UUID", "Q&A 참고 문서"],
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
        source_must_include_any=["YouTube", "입양"],
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
    Scenario(
        name="maltese_characteristics",
        question="말티즈 특징은 뭐야?",
        expected_intent="일반 상담",
        must_include_any=["말티즈", "성격", "털", "작", "훈련"],
        must_not_include=["오류", "Q&A 참고 문서"],
        source_must_include_any=["AKC", "Maltese"],
        top_source_must_include_any=["Maltese", "말티즈"],
    ),
    Scenario(
        name="grass_eating_walk",
        question="강아지가 산책하다가 풀을 먹을 때 어떻게 해야 해?",
        expected_intent="일반 상담",
        must_include_any=["풀", "산책", "구토", "위험", "식물"],
        must_not_include=["오류", "Q&A 참고 문서"],
        top_source_must_include_any=["풀", "먹"],
    ),
    Scenario(
        name="head_tilt_reason",
        question="강아지가 고개를 갸우뚱하는 이유는?",
        expected_intent="일반 상담",
        must_include_any=["고개", "갸우뚱", "소리", "호기심", "주의"],
        must_not_include=["오류", "Q&A 참고 문서"],
        top_source_must_include_any=["고개", "갸우뚱", "머리"],
    ),
    Scenario(
        name="beginner_breed_recommendation",
        question="처음 강아지를 키우는 사람에게 맞는 견종 추천해줘",
        expected_intent="견종 추천",
        must_include_any=["초보", "견종", "훈련", "성격", "에너지"],
        must_not_include=["/shelter/?breed=", "Q&A 참고 문서"],
        source_must_include_any=["AKC"],
    ),
    Scenario(
        name="chocolate_danger",
        question="강아지에게 초콜릿이 왜 위험해?",
        expected_intent="일반 상담",
        must_include_any=["초콜릿", "테오브로민", "중독", "동물병원", "체중"],
        must_not_include=["오류", "Q&A 참고 문서"],
        top_source_must_include_any=["초콜릿", "먹어도", "위험"],
    ),
]


def main() -> int:
    parser = argparse.ArgumentParser(description="Run 10 diverse Pet Mate chatbot quality scenarios.")
    parser.add_argument("--no-screenshots", action="store_true", help="Skip Playwright screenshot capture.")
    parser.add_argument("--output-dir", type=Path, default=None)
    args = parser.parse_args()

    output_dir = args.output_dir or REPORT_DIR / f"diverse_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "screenshots").mkdir(exist_ok=True)

    setup_django()

    results = []
    for index, scenario in enumerate(DIVERSE_SCENARIOS, start=1):
        print(f"[{index}/{len(DIVERSE_SCENARIOS)}] {scenario.question}")
        results.append(run_scenario(index, scenario))

    json_path = output_dir / "chatbot_quality_results.json"
    html_path = output_dir / "chatbot_quality_report.html"
    json_path.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
    html_path.write_text(render_report(results), encoding="utf-8")

    screenshot_paths: list[str] = []
    if not args.no_screenshots:
        base_quality_tests.SCENARIOS = DIVERSE_SCENARIOS
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


if __name__ == "__main__":
    raise SystemExit(main())
