import argparse
import csv
import json
import os
import re
import sys
import time
import unicodedata
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent
ROOT_DIR = BASE_DIR.parents[1]
PROCESSED_DIR = BASE_DIR / "processed"
OUTPUT_PATH = PROCESSED_DIR / "seol_qna.jsonl"
QUESTION_WORKING_PATH = PROCESSED_DIR / "seol_qna_question_korean_working.jsonl"

RESPONSES_URL = "https://api.openai.com/v1/responses"
DEFAULT_MODEL = "gpt-5-mini"


def load_env_file(path: Path) -> None:
    if not path.exists():
        return

    with path.open("r", encoding="utf-8") as file:
        for line in file:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def normalize_space(text: str) -> str:
    text = re.sub(r"\s+", " ", str(text or ""))
    text = re.sub(r"\s+([,.?!])", r"\1", text)
    text = re.sub(r"([,.?!])(?=[^\s,.?!])", r"\1 ", text)
    return text.strip()


def remove_emoji(text: str) -> str:
    cleaned = []
    for char in str(text or ""):
        category = unicodedata.category(char)
        if category in {"So", "Sk"}:
            continue
        if char in {"\ufe0f", "\u200d", "\u200b"}:
            continue
        cleaned.append(char)
    return "".join(cleaned)


def clean_title(title: str) -> str:
    text = unicodedata.normalize("NFKC", str(title or ""))
    text = remove_emoji(text)
    text = re.sub(r"\|.*$", "", text)
    text = re.sub(r"\[[^\]]*(?:event|이벤트)[^\]]*\]", "", text, flags=re.IGNORECASE)
    text = re.sub(r"\b(?:Behavioral Veterinarian|Veterinarian|Seol Chae-hyun|Dr\.?\s*Seol).*", "", text, flags=re.IGNORECASE)
    text = re.sub(r"\bQ\s*&\s*A\b", "", text, flags=re.IGNORECASE)
    text = re.sub(r"\bl\s*$", "", text, flags=re.IGNORECASE)
    text = text.replace("...", "")
    return normalize_space(text).strip(" -_|")


def clean_caption(caption: str) -> str:
    text = unicodedata.normalize("NFKC", str(caption or ""))
    text = text.replace(">>", " ")
    text = re.sub(r"\[(?:음악|박수|Music)\]", " ", text, flags=re.IGNORECASE)
    text = re.sub(r"\((?:음악|박수|Music)\)", " ", text, flags=re.IGNORECASE)
    text = re.sub(r"\b(?:subscribe|like|event)\b", " ", text, flags=re.IGNORECASE)
    text = re.sub(r"안녕하세요[,.]?\s*.{0,80}?(?:입니다|수의사입니다|설쌤입니다|설채현입니다)", " ", text)
    text = re.sub(r"안녕하세요[,.]?\s*(?:설친|설춘|여러분)[,.]?", " ", text)
    text = re.sub(r"이번\s*시간(?:에는|은|도)?\s*", " ", text)
    text = re.sub(r"구독과\s*좋아요.{0,60}", " ", text)
    text = re.sub(r"좋아요와\s*구독.{0,60}", " ", text)
    for phrase in [
        "참고하세요",
        "꼭 참고하세요",
        "이렇게 하세요",
        "이렇게 하셔야 해요",
        "이것만 알아두세요",
        "꼭 체크해 주세요",
    ]:
        text = text.replace(phrase, " ")
    return normalize_space(text)


def find_seol_csv() -> Path:
    candidates = list(BASE_DIR.glob("*QnA.csv"))
    if not candidates:
        raise FileNotFoundError("No QnA CSV file found")
    # The Seol QnA file is the larger of the two QnA CSVs in this folder.
    return max(candidates, key=lambda path: path.stat().st_size)


def read_source_rows() -> list[dict]:
    source_path = find_seol_csv()
    rows = []
    seen = set()
    with source_path.open("r", encoding="utf-8-sig", newline="") as file:
        for row in csv.DictReader(file):
            video_id = row.get("video_id", "").strip()
            if not video_id or video_id in seen or row.get("error", "").strip():
                continue
            seen.add(video_id)
            title = clean_title(row.get("title", ""))
            answer = clean_caption(row.get("caption", ""))
            if title and answer:
                rows.append(
                    {
                        "playlist_index": row.get("playlist_index", "").strip(),
                        "video_id": video_id,
                        "title": title,
                        "answer": answer,
                    }
                )
    rows.sort(key=lambda row: int(row["playlist_index"]))
    return rows


def read_existing_questions() -> dict[str, dict]:
    if not QUESTION_WORKING_PATH.exists():
        return {}
    records = {}
    with QUESTION_WORKING_PATH.open("r", encoding="utf-8") as file:
        for line in file:
            if not line.strip():
                continue
            record = json.loads(line)
            records[record["video_id"]] = record
    return records


def extract_output_text(response: dict) -> str:
    if response.get("output_text"):
        return response["output_text"].strip()
    chunks = []
    for item in response.get("output", []):
        for content in item.get("content", []):
            text = content.get("text")
            if content.get("type") in {"output_text", "text"} and text:
                chunks.append(text)
    return "\n".join(chunks).strip()


def parse_question(text: str) -> str:
    text = text.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[-1].strip()
        if text.endswith("```"):
            text = text[:-3].strip()
    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end != -1:
        parsed = json.loads(text[start : end + 1])
        question = parsed.get("question", "")
    else:
        question = text
    question = remove_emoji(normalize_space(question)).strip('"')
    if not question:
        raise ValueError("empty question")
    return question


def build_prompt(title: str) -> str:
    return f"""
아래 유튜브 영상 제목을 반려견 보호자가 묻는 자연스러운 한국어 질문으로 바꿔라.

규칙:
- 한국어 질문 한 문장으로 작성한다.
- 이모지, 채널명, 의사 이름, 장식 문구는 제거한다.
- 제목의 의미를 바꾸거나 없는 정보를 추가하지 않는다.
- 출력은 JSON 객체 하나만 쓴다.

출력 형식:
{{"question":"한국어 질문"}}

제목:
{title}
""".strip()


def call_openai(prompt: str, model: str, api_key: str, timeout: int, max_retries: int) -> str:
    payload = {"model": model, "input": prompt, "max_output_tokens": 800}
    data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    for attempt in range(max_retries + 1):
        request = urllib.request.Request(RESPONSES_URL, data=data, headers=headers, method="POST")
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                parsed = json.loads(response.read().decode("utf-8"))
                return parse_question(extract_output_text(parsed))
        except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError, ValueError, json.JSONDecodeError) as error:
            if attempt >= max_retries:
                raise
            print(f"retry after error: {error}", flush=True)
            time.sleep(min(2**attempt, 20))
    raise RuntimeError("OpenAI request failed")


def translate_row(row: dict, model: str, api_key: str, timeout: int, max_retries: int) -> dict:
    try:
        question = call_openai(build_prompt(row["title"]), model, api_key, timeout, max_retries)
    except Exception as error:
        question = remove_emoji(normalize_space(row["title"]))
        if not question.endswith("?"):
            question = f"{question}에 대해 알려주세요?"
        print(f"fallback question for {row['playlist_index']}: {error}", flush=True)
    return {
        "playlist_index": row["playlist_index"],
        "video_id": row["video_id"],
        "title": row["title"],
        "question": question,
    }


def append_jsonl(path: Path, record: dict) -> None:
    with path.open("a", encoding="utf-8", newline="\n") as file:
        file.write(json.dumps(record, ensure_ascii=False) + "\n")


def write_output(source_rows: list[dict], questions: dict[str, dict]) -> None:
    output_rows = []
    for row in source_rows:
        question = questions[row["video_id"]]["question"]
        output_rows.append(
            {
                "question": remove_emoji(normalize_space(question)),
                "answer": normalize_space(row["answer"]),
            }
        )

    with OUTPUT_PATH.open("w", encoding="utf-8", newline="\n") as file:
        for row in output_rows:
            file.write(json.dumps(row, ensure_ascii=False) + "\n")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--timeout", type=int, default=60)
    parser.add_argument("--max-retries", type=int, default=3)
    args = parser.parse_args()

    load_env_file(ROOT_DIR / ".env")
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY is missing")

    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    source_rows = read_source_rows()
    questions = read_existing_questions()
    pending = [row for row in source_rows if row["video_id"] not in questions]

    with ThreadPoolExecutor(max_workers=args.workers) as executor:
        future_map = {
            executor.submit(translate_row, row, args.model, api_key, args.timeout, args.max_retries): row
            for row in pending
        }
        for future in as_completed(future_map):
            record = future.result()
            append_jsonl(QUESTION_WORKING_PATH, record)
            questions[record["video_id"]] = record
            print(f"{len(questions)}/{len(source_rows)} - {record['question']}", flush=True)

    if len(questions) != len(source_rows):
        raise RuntimeError(f"Question translation incomplete: {len(questions)}/{len(source_rows)}")

    write_output(source_rows, questions)
    result = {
        "rows": len(source_rows),
        "output": str(OUTPUT_PATH),
        "fields": ["question", "answer"],
    }
    sys.stdout.buffer.write((json.dumps(result, ensure_ascii=False, indent=2) + "\n").encode("utf-8"))


if __name__ == "__main__":
    main()
