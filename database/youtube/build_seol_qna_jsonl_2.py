import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

from dotenv import load_dotenv


ROOT_DIR = Path(__file__).resolve().parents[2]
DEFAULT_INPUT = ROOT_DIR / "database" / "youtube" / "processed" / "seol_qna.jsonl"
DEFAULT_OUTPUT = ROOT_DIR / "database" / "youtube" / "processed" / "seol_qna_llm_corrected_sample.jsonl"
RESPONSES_URL = "https://api.openai.com/v1/responses"


def load_jsonl(path):
    rows = []
    with path.open("r", encoding="utf-8") as f:
        for line_no, line in enumerate(f, start=1):
            line = line.strip()
            if not line:
                continue
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError as exc:
                raise ValueError(f"Invalid JSONL at line {line_no}: {exc}") from exc
    return rows


def dump_jsonl_row(handle, row):
    handle.write(json.dumps(row, ensure_ascii=False) + "\n")
    handle.flush()


def build_prompt(question, answer):
    answer_len = len(answer)
    min_len = max(1500, int(answer_len * 0.6))
    max_len = max(min_len + 300, int(answer_len * 0.85))
    return f"""
너는 반려견 Q&A 데이터셋의 답변을 교정하는 수의학 전문가다.

질문:
{question}

원본 답변:
{answer}

작업 규칙:
- question은 절대 수정하지 않는다.
- answer만 자연스러운 한국어 Q&A 답변으로 교정한다.
- 자동 자막 오류, 반복 표현, 의미 없는 감탄사, 방송 진행 멘트, 인사말, 구독/좋아요 안내, 광고성 문장을 제거한다.
- 원문에 없는 새로운 정보는 추가하지 않는다.
- 핵심 정보와 주의사항은 유지한다.
- 질병, 중독, 응급상황, 약물, 예방 관련 내용은 과장하거나 단정하지 않는다.
- 필요한 경우 동물병원 상담 권고는 유지한다.
- 답변을 짧게 요약하지 않는다.
- 원문의 정보량, 논리 흐름, 주요 예시, 주의사항을 최대한 유지한다.
- 반복, 잡음, 방송 멘트, 광고성 문장, 불필요한 자기소개만 제거한다.
- 원본 답변 길이는 약 {answer_len}자다.
- 교정 후 답변은 반드시 {min_len}~{max_len}자 범위로 작성한다.
- 길이를 줄이기 위해 핵심 예시, 근거 수치, 관리 방법, 주의사항을 삭제하지 않는다.
- 반복과 잡음이 많더라도 정보성 내용은 가능한 한 보존한다.
- 질문에 직접 답하는 완성형 답변으로 작성한다.
- 강의자료 방식처럼 의미는 유지하고, 자연스럽고 올바른 한국어 문장으로 복원한다.

출력 형식:
{{"answer": "교정된 답변"}}
""".strip()


def extract_text(payload):
    if payload.get("output_text"):
        return payload["output_text"].strip()

    parts = []
    for item in payload.get("output", []):
        for content in item.get("content", []):
            text = content.get("text")
            if text:
                parts.append(text)
    return "\n".join(parts).strip()


def parse_answer(text):
    text = text.strip()
    if text.startswith("```"):
        text = text.strip("`")
        text = text.replace("json\n", "", 1).replace("JSON\n", "", 1).strip()

    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        start = text.find("{")
        end = text.rfind("}")
        if start == -1 or end == -1 or start >= end:
            return parse_loose_answer(text)
        try:
            data = json.loads(text[start : end + 1])
        except json.JSONDecodeError:
            return parse_loose_answer(text[start : end + 1])

    answer = str(data.get("answer", "")).strip()
    if not answer:
        raise ValueError("LLM response has empty answer")
    return answer


def parse_loose_answer(text):
    marker = '"answer"'
    marker_index = text.find(marker)
    if marker_index == -1:
        marker_index = text.find("'answer'")
    if marker_index == -1:
        cleaned = text.strip()
    else:
        colon_index = text.find(":", marker_index)
        if colon_index == -1:
            cleaned = text.strip()
        else:
            cleaned = text[colon_index + 1 :].strip()

    if cleaned.startswith('"') or cleaned.startswith("'"):
        cleaned = cleaned[1:]
    if cleaned.endswith("}"):
        cleaned = cleaned[:-1].strip()
    if cleaned.endswith('"') or cleaned.endswith("'"):
        cleaned = cleaned[:-1]

    cleaned = cleaned.replace("\\n", "\n").replace('\\"', '"').strip()
    if not cleaned:
        raise ValueError("LLM response has empty answer")
    return cleaned


def call_openai(question, answer, model, api_key, timeout=120):
    body = {
        "model": model,
        "input": build_prompt(question, answer),
    }
    data = json.dumps(body, ensure_ascii=False).encode("utf-8")
    request = urllib.request.Request(
        RESPONSES_URL,
        data=data,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )

    with urllib.request.urlopen(request, timeout=timeout) as response:
        payload = json.loads(response.read().decode("utf-8"))

    return parse_answer(extract_text(payload))


def correct_rows(rows, output_path, model, api_key, start=0, limit=None, sleep_seconds=0.2):
    selected = rows[start:]
    if limit is not None:
        selected = selected[:limit]

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8", newline="\n") as out:
        for offset, row in enumerate(selected, start=start):
            question = str(row.get("question", "")).strip()
            answer = str(row.get("answer", "")).strip()
            if not question or not answer:
                continue

            corrected = call_openai(question, answer, model=model, api_key=api_key)
            dump_jsonl_row(out, {"question": question, "answer": corrected})
            print(f"[{offset + 1}/{len(rows)}] corrected: {question[:40]}", flush=True)
            time.sleep(sleep_seconds)


def main():
    parser = argparse.ArgumentParser(description="Correct seol_qna.jsonl answers with OpenAI API.")
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--start", type=int, default=0)
    parser.add_argument("--limit", type=int, default=3)
    parser.add_argument("--model", default=None)
    args = parser.parse_args()

    load_dotenv(ROOT_DIR / ".env")
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("OPENAI_API_KEY is not set in .env", file=sys.stderr)
        return 1

    model = args.model or os.getenv("OPENAI_MODEL") or "gpt-5-mini"
    rows = load_jsonl(args.input)
    correct_rows(
        rows=rows,
        output_path=args.output,
        model=model,
        api_key=api_key,
        start=args.start,
        limit=args.limit,
    )
    print(f"Saved: {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
