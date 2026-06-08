from __future__ import annotations

import json
import random
from pathlib import Path

from django.shortcuts import render
from django.views.decorators.http import require_http_methods


PROJECT_DIR = Path(__file__).resolve().parents[2]
QUIZ_BANK_PATH = PROJECT_DIR / "database" / "quiz" / "qna_quiz_bank.json"
QUESTION_COUNT = 10


def load_quiz_bank() -> list[dict]:
    """생성된 quiz bank JSON을 읽는다.

    - database/quiz/qna_quiz_bank.json 파일을 사용한다.
    - 파일이 없거나 비어 있으면 빈 리스트를 반환한다.
    """
    if not QUIZ_BANK_PATH.exists():
        return []

    with QUIZ_BANK_PATH.open("r", encoding="utf-8") as file:
        data = json.load(file)

    return [item for item in data if item.get("question") and item.get("answer")]


def pick_random_quizzes(quiz_bank: list[dict], count: int = QUESTION_COUNT) -> list[dict]:
    """quiz bank에서 랜덤 문제를 뽑는다.

    - 새로고침할 때마다 다른 문제가 나오도록 random.sample을 사용한다.
    - 저장된 문제가 10개보다 적으면 가능한 개수만 보여준다.
    """
    if len(quiz_bank) <= count:
        return quiz_bank
    return random.sample(quiz_bank, count)


def build_result_items(quiz_bank: list[dict], selected_ids: list[str], submitted_answers: dict) -> list[dict]:
    """사용자 제출 답안을 채점 가능한 결과 목록으로 바꾼다."""
    quiz_by_id = {item["id"]: item for item in quiz_bank}
    result_items = []

    for quiz_id in selected_ids:
        quiz = quiz_by_id.get(quiz_id)
        if not quiz:
            continue

        user_answer = submitted_answers.get(quiz_id, "")
        correct_answer = quiz.get("answer", "")
        is_correct = user_answer == correct_answer

        result_items.append(
            {
                "id": quiz_id,
                "type": quiz.get("type"),
                "question": quiz.get("question"),
                "choices": quiz.get("choices", []),
                "user_answer": user_answer,
                "answer": correct_answer,
                "explanation": quiz.get("explanation"),
                "score": quiz.get("score", 10),
                "earned_score": quiz.get("score", 10) if is_correct else 0,
                "is_correct": is_correct,
                "metadata": quiz.get("metadata", {}),
            }
        )

    return result_items


@require_http_methods(["GET", "POST"])
def get_page(request):
    quiz_bank = load_quiz_bank()

    if request.method == "POST":
        selected_ids = request.POST.get("quiz_ids", "").split(",")
        selected_ids = [quiz_id for quiz_id in selected_ids if quiz_id]
        submitted_answers = {
            quiz_id: request.POST.get(f"answer_{quiz_id}", "")
            for quiz_id in selected_ids
        }
        result_items = build_result_items(quiz_bank, selected_ids, submitted_answers)
        total_score = sum(item["score"] for item in result_items)
        earned_score = sum(item["earned_score"] for item in result_items)
        correct_count = sum(1 for item in result_items if item["is_correct"])
        wrong_items = [item for item in result_items if not item["is_correct"]]

        # 로그인한 사용자일 경우 DB에 저장
        if request.user.is_authenticated:
            from .models import TestResult
            TestResult.objects.create(
                user=request.user,
                total_score=total_score,
                earned_score=earned_score,
                result_data=result_items
            )

        return render(
            request,
            "main/test.html",
            {
                "mode": "result",
                "result_items": result_items,
                "wrong_items": wrong_items,
                "total_count": len(result_items),
                "correct_count": correct_count,
                "wrong_count": len(wrong_items),
                "total_score": total_score,
                "earned_score": earned_score,
            },
        )

    quizzes = pick_random_quizzes(quiz_bank)
    return render(
        request,
        "main/test.html",
        {
            "mode": "quiz",
            "quizzes": quizzes,
            "quiz_ids": ",".join(item["id"] for item in quizzes),
            "quiz_bank_count": len(quiz_bank),
            "question_count": len(quizzes),
            "quiz_bank_exists": QUIZ_BANK_PATH.exists(),
            "quiz_bank_path": str(QUIZ_BANK_PATH),
        },
    )

from django.contrib.auth.decorators import login_required

@login_required
def view_saved_result(request, result_id):
    from .models import TestResult
    result = get_object_or_404(TestResult, id=result_id, user=request.user)
    result_items = result.result_data
    total_score = result.total_score
    earned_score = result.earned_score
    correct_count = sum(1 for item in result_items if item["is_correct"])
    wrong_items = [item for item in result_items if not item["is_correct"]]

    return render(
        request,
        "main/test.html",
        {
            "mode": "result",
            "result_items": result_items,
            "wrong_items": wrong_items,
            "total_count": len(result_items),
            "correct_count": correct_count,
            "wrong_count": len(wrong_items),
            "total_score": total_score,
            "earned_score": earned_score,
        },
    )
