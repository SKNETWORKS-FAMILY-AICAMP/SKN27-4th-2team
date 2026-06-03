import json
import unicodedata
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent
PROCESSED_DIR = BASE_DIR / "processed"
OUTPUT_PATH = PROCESSED_DIR / "kang_qna.jsonl"


def normalize_space(text: str) -> str:
    return " ".join(str(text or "").split()).strip()


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


def read_jsonl(path: Path) -> list[dict]:
    with path.open("r", encoding="utf-8") as file:
        return [json.loads(line) for line in file if line.strip()]


def write_jsonl(path: Path, rows: list[dict]) -> None:
    with path.open("w", encoding="utf-8", newline="\n") as file:
        for row in rows:
            file.write(json.dumps(row, ensure_ascii=False) + "\n")


def main() -> None:
    rows = read_jsonl(OUTPUT_PATH)
    final_rows = []

    for row in rows:
        question = remove_emoji(normalize_space(row.get("question", "")))
        answer = remove_emoji(normalize_space(row.get("answer", "")))
        if not question or not answer:
            continue
        final_rows.append({"question": question, "answer": answer})

    write_jsonl(OUTPUT_PATH, final_rows)
    print(
        json.dumps(
            {
                "rows": len(final_rows),
                "output": str(OUTPUT_PATH),
                "fields": ["question", "answer"],
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
