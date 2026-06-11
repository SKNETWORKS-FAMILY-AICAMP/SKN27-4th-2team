"""Build a QnA quiz bank for the Django test quiz page.

실행 목적:
- QnA 원본 JSONL 또는 PGVector 테이블에서 QnA 문서를 가져온다.
- 원본 Question / Answer를 바탕으로 짧은 O/X 또는 4지선다 퀴즈를 생성한다.
- 생성된 quiz bank JSON은 Django test 페이지에서 랜덤 10문제를 뽑는 원천 데이터로 사용한다.

권장 방식:
- 기본값은 --source loader 이다.
- PGVector에는 청킹된 문서가 들어가므로 긴 Answer가 중간에서 잘릴 수 있다.
- 퀴즈 정답/해설은 원문 전체가 중요하므로 원본 QnA 파일을 읽는 loader 방식이 더 적합하다.

생성 파일:
- 기본 경로: database/quiz/qna_quiz_bank.json

실행 예시:
- 혼합 퀴즈 10개 생성:
  python database/tools/build_qna_quiz_bank.py --limit 10 --preview 3

- 원문 QnA만 확인:
  python database/tools/build_qna_quiz_bank.py --quiz-mode source --limit 10 --preview 3
"""

from __future__ import annotations

import argparse
import json
import os
import re
from pathlib import Path
from typing import Any

import psycopg
from dotenv import load_dotenv
from langchain_core.documents import Document
from openai import OpenAI

from loader import get_qna_loader


DATABASE_DIR = Path(__file__).resolve().parents[1]
PROJECT_DIR = DATABASE_DIR.parent
DEFAULT_COLLECTION_NAME = "dog_rag_documents"
DEFAULT_OUTPUT_PATH = DATABASE_DIR / "quiz" / "qna_quiz_bank.json"
DEFAULT_CHAT_MODEL = "gpt-4o-mini"

QUESTION_ANSWER_PATTERN = re.compile(
    r"Question:\s*(?P<question>.*?)\s*Answer:\s*(?P<answer>.*)",
    re.DOTALL,
)

BANNED_CHOICE_TEXTS = {
    "모르겠다",
    "잘 모르겠다",
    "상관없다",
    "관련 없다",
    "전혀 위험하지 않은 질환",
    "위 보기 모두",
    "모두 해당된다",
    "모두 아니다",
    "정답 없음",
    "기타",
}
BANNED_OX_WORDS = ("항상", "무조건", "절대", "전혀")


QUIZ_JSON_SCHEMA = {
    "name": "qna_quiz_item",
    "schema": {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "type": {"type": "string", "enum": ["ox", "multiple_choice"]},
            "question": {"type": "string"},
            "choices": {
                "type": "array",
                "items": {"type": "string"},
                "minItems": 2,
                "maxItems": 4,
            },
            "answer": {"type": "string"},
            "explanation": {"type": "string"},
        },
        "required": ["type", "question", "choices", "answer", "explanation"],
    },
}


def load_environment() -> None:
    """프로젝트 .env 파일을 로드한다.

    - DB 접속 정보가 .env에 있으면 그 값을 사용한다.
    - 없으면 docker-compose.yml에서 쓰는 기본값을 사용한다.
    - OpenAI API 키도 여기서 로드한다.
    """
    load_dotenv(PROJECT_DIR / ".env", override=True, encoding="utf-8-sig")


def db_config() -> dict[str, Any]:
    """PostgreSQL 접속 설정을 만든다."""
    return {
        "host": os.getenv("POSTGRES_HOST", "localhost"),
        "port": int(os.getenv("POSTGRES_PORT", "5432")),
        "dbname": os.getenv("POSTGRES_DB", "pet_dog"),
        "user": os.getenv("POSTGRES_USER", "admin"),
        "password": os.getenv("POSTGRES_PASSWORD", "admin1234"),
    }


def parse_qna_document(document: str) -> tuple[str, str] | None:
    """Document.page_content 문자열에서 Question / Answer를 분리한다."""
    match = QUESTION_ANSWER_PATTERN.search(document or "")
    if not match:
        return None

    question = match.group("question").strip()
    answer = match.group("answer").strip()
    if not question or not answer:
        return None

    return question, answer


def load_qna_documents_from_loader(limit: int | None = None) -> list[Document]:
    """원본 QnA JSONL 파일을 loader.py로 읽는다."""
    qna_specs = [
        (
            DATABASE_DIR / "youtube" / "processed" / "final_seol_qna.jsonl",
            "final_seol_qna",
        ),
        (
            DATABASE_DIR / "youtube" / "processed" / "kang_qna.jsonl",
            "kang_qna",
        ),
    ]

    documents: list[Document] = []
    for file_path, qna_source in qna_specs:
        loader = get_qna_loader(str(file_path), qna_source)
        loaded = loader.load()
        documents.extend(loaded)
        print(f"loaded {len(loaded):>4} qna docs from {file_path}")

        if limit is not None and len(documents) >= limit:
            return documents[:limit]

    return documents


def fetch_qna_rows_from_pgvector(collection_name: str, limit: int | None = None) -> list[dict[str, Any]]:
    """langchain_pg_embedding에서 QnA chunk만 조회한다.

    - DB 적재 결과를 확인하고 싶을 때만 사용한다.
    - 기본 퀴즈 생성에는 원본 loader 방식이 더 적합하다.
    """
    sql = """
        SELECT
            e.id::text AS embedding_id,
            e.document,
            e.cmetadata
        FROM langchain_pg_embedding AS e
        JOIN langchain_pg_collection AS c
          ON c.uuid = e.collection_id
        WHERE c.name = %s
          AND e.cmetadata->>'source' = 'qna'
          AND e.document LIKE 'Question:%%Answer:%%'
        ORDER BY e.cmetadata->>'qna_source', e.cmetadata->>'seq_num', e.id::text
    """
    params: list[Any] = [collection_name]

    if limit is not None:
        sql += "\n        LIMIT %s"
        params.append(limit)

    with psycopg.connect(**db_config()) as conn:
        with conn.cursor() as cur:
            cur.execute(sql, params)
            rows = cur.fetchall()

    return [
        {
            "source_id": row[0],
            "page_content": row[1],
            "metadata": row[2] or {},
        }
        for row in rows
    ]


def documents_to_rows(documents: list[Document]) -> list[dict[str, Any]]:
    """LangChain Document를 공통 row 형태로 변환한다."""
    return [
        {
            "source_id": f"loader:{index}",
            "page_content": document.page_content,
            "metadata": document.metadata or {},
        }
        for index, document in enumerate(documents, start=1)
    ]


def normalize_metadata(metadata: dict[str, Any]) -> dict[str, Any]:
    """화면에서 사용할 metadata만 정리한다."""
    return {
        "source": metadata.get("source"),
        "doc_type": metadata.get("doc_type"),
        "qna_source": metadata.get("qna_source"),
        "source_file": metadata.get("source_file"),
        "expert": metadata.get("expert"),
        "expert_role": metadata.get("expert_role"),
        "channel": metadata.get("channel"),
        "content_category": metadata.get("content_category"),
    }


def choose_quiz_type(index: int, quiz_mode: str) -> str:
    """문제 유형을 결정한다.

    - mixed: O/X와 4지선다를 번갈아 생성한다.
    - ox: O/X만 생성한다.
    - multiple_choice: 4지선다만 생성한다.
    """
    if quiz_mode == "mixed":
        return "ox" if index % 2 == 1 else "multiple_choice"
    return quiz_mode


def create_openai_client() -> OpenAI:
    """OpenAI 클라이언트를 생성한다."""
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY is empty. Fill it in the project .env file first.")
    return OpenAI(api_key=api_key)


def generate_quiz_with_openai(
    client: OpenAI,
    model: str,
    quiz_type: str,
    source_question: str,
    source_answer: str,
) -> dict[str, Any]:
    """원본 QnA를 품질 기준이 있는 O/X 또는 4지선다 퀴즈로 변환한다."""
    if quiz_type == "ox":
        task = """
O/X 퀴즈 1개를 생성하세요.
- choices는 반드시 ["O", "X"]입니다.
- answer는 반드시 "O" 또는 "X"입니다.
- 문장은 너무 뻔한 일반상식이나 말장난이면 안 됩니다.
- "항상", "무조건", "절대", "전혀" 같은 단어로 억지 오답을 만들지 마세요.
- 원문에서 보호자가 실제로 배워야 할 주의점, 원인, 관리 방법 중 하나를 묻습니다.
""".strip()
    else:
        task = """
4지선다 퀴즈 1개를 생성하세요.
- choices는 정확히 4개입니다.
- answer는 choices 중 하나와 완전히 일치해야 합니다.
- 오답 3개는 모두 정답과 같은 범주의 그럴듯한 선택지여야 합니다.
- 질문에 대한 정답은 반드시 하나만 명확해야 합니다.
- 원문상 여러 보기가 동시에 정답이 될 수 있는 질문은 만들지 마세요.
- 오답은 원문에 포함된 다른 정답 후보이면 안 됩니다.
- 오답은 원문 내용과 명확히 구분되는 틀린 선택지여야 합니다.
- 원문에 여러 원인/방법/전파 경로가 나오면, 그 주제로 사지선다를 만들지 말고 하나만 명확한 다른 핵심 사실을 물으세요.
- 질문이 "이유"를 물으면 모든 보기는 이유여야 하고, "방법"을 물으면 모든 보기는 방법이어야 합니다.
- 정답이 원인/결과/주의사항/예방법 중 무엇인지 헷갈리게 섞지 마세요.
- "모르겠다", "상관없다", "모두 해당된다", "정답 없음", "기타" 같은 무성의한 보기는 금지합니다.
- 하나만 너무 길거나 너무 짧은 보기, 누가 봐도 말이 안 되는 보기는 금지합니다.
""".strip()

    prompt = f"""
당신은 반려견 교육/건강 콘텐츠를 바탕으로 보호자용 퀴즈를 만드는 출제자입니다.
아래 원본 QnA만 근거로 사용하세요. 원문에 없는 내용은 만들지 마세요.

출제 목표:
- 사용자가 반려견 건강/행동/훈련 지식을 제대로 이해했는지 확인합니다.
- 문제는 실제 서비스 화면에 바로 노출될 수 있을 만큼 자연스러워야 합니다.
- 너무 쉽거나 터무니없는 문제는 실패입니다.

요구사항:
- {task}
- question은 한국어 1문장으로, 20~70자 정도로 작성하세요.
- explanation은 원문 Answer를 근거로 2문장 이내로 작성하세요.
- 전문용어는 필요할 때만 쓰고, 보호자가 이해할 수 있게 쉽게 작성하세요.
- 원본 Question을 그대로 복사하지 말고, 원본 Answer의 핵심 내용을 짧은 문제로 재구성하세요.
- 사지선다는 반드시 하나의 정답만 존재해야 합니다.
- 사지선다 보기는 모두 같은 문법과 같은 의미 범주로 작성하세요.
- 예: 질문이 "원인"을 물으면 보기 4개 모두 원인 후보여야 합니다.
- 예: 질문이 "예방법"을 물으면 보기 4개 모두 예방법 후보여야 합니다.
- 원문에서 둘 이상이 맞는 내용이면 그 주제로 사지선다를 만들지 말고 더 좁은 주제로 바꾸세요.
- 나쁜 예: 원문에 혈액, 타액, 구토물, 분변 접촉이 모두 전파 경로로 나오는데 이들을 서로 보기로 두는 것.
- 좋은 예: "SFTS를 매개하는 주요 외부기생충은 무엇인가요?"처럼 정답이 하나로 좁혀지는 문제.

원본 Question:
{source_question}

원본 Answer:
{source_answer[:6000]}
""".strip()

    last_error: Exception | None = None
    for attempt in range(3):
        retry_note = "" if attempt == 0 else (
            "\n이전 응답은 퀴즈 품질 기준을 통과하지 못했습니다. "
            "터무니없는 보기, 너무 쉬운 문장, 금지 표현을 피해서 다시 생성하세요."
        )
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": "Return only valid JSON that matches the given schema."},
                {"role": "user", "content": prompt + retry_note},
            ],
            response_format={"type": "json_schema", "json_schema": {**QUIZ_JSON_SCHEMA, "strict": True}},
            temperature=0.25,
        )

        content = response.choices[0].message.content or "{}"
        quiz = json.loads(content)
        try:
            return validate_generated_quiz(quiz, quiz_type)
        except ValueError as exc:
            last_error = exc

    raise ValueError(f"Failed to generate valid quiz: {last_error}")

def is_low_quality_choice(choice: str) -> bool:
    """사지선다 보기 품질을 검사한다."""
    normalized = " ".join(str(choice).strip().split())
    if not normalized:
        return True
    if normalized in BANNED_CHOICE_TEXTS:
        return True
    if len(normalized) < 3:
        return True
    return False


def validate_generated_quiz(quiz: dict[str, Any], quiz_type: str) -> dict[str, Any]:
    """생성된 퀴즈 JSON의 형식과 보기 품질을 검증한다."""
    quiz["type"] = quiz_type
    quiz["question"] = str(quiz.get("question", "")).strip()
    quiz["answer"] = str(quiz.get("answer", "")).strip()
    quiz["explanation"] = str(quiz.get("explanation", "")).strip()

    if len(quiz["question"]) < 10:
        raise ValueError("Question is too short.")
    if len(quiz["explanation"]) < 15:
        raise ValueError("Explanation is too short.")

    if quiz_type == "ox":
        quiz["choices"] = ["O", "X"]
        if quiz.get("answer") not in {"O", "X"}:
            raise ValueError(f"Invalid O/X answer: {quiz.get('answer')}")
        if any(word in quiz["question"] for word in BANNED_OX_WORDS):
            raise ValueError(f"O/X question is too absolute: {quiz['question']}")
    else:
        choices = [str(choice).strip() for choice in (quiz.get("choices") or [])]
        if len(choices) != 4:
            raise ValueError(f"Multiple choice quiz must have 4 choices: {choices}")
        if len(set(choices)) != 4:
            raise ValueError(f"Choices must be unique: {choices}")
        if any(is_low_quality_choice(choice) for choice in choices):
            raise ValueError(f"Low quality choices: {choices}")
        if quiz.get("answer") not in choices:
            raise ValueError("Multiple choice answer must be one of choices.")
        quiz["choices"] = choices

    return quiz

def build_source_items(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """원본 QnA 확인용 quiz bank를 만든다."""
    quiz_items: list[dict[str, Any]] = []

    for index, row in enumerate(rows, start=1):
        parsed = parse_qna_document(row["page_content"])
        if parsed is None:
            continue

        question, answer = parsed
        metadata = row["metadata"]
        quiz_items.append(
            {
                "id": f"qna_source_{index:04d}",
                "type": "qna_source",
                "question": question,
                "choices": [],
                "answer": answer,
                "explanation": answer,
                "score": 10,
                "source_id": row["source_id"],
                "source_question": question,
                "source_answer": answer,
                "metadata": normalize_metadata(metadata),
            }
        )

    return quiz_items


def build_generated_quiz_items(rows: list[dict[str, Any]], args: argparse.Namespace) -> list[dict[str, Any]]:
    """O/X 또는 4지선다 퀴즈 bank를 만든다.

    - 품질 검증을 통과하지 못한 문제는 건너뛴다.
    - --limit 값은 원본 row 개수가 아니라 최종 생성할 퀴즈 목표 개수로 사용한다.
    - 예: --limit 100이면 검증 통과 퀴즈 100개가 찰 때까지 가능한 row를 순회한다.
    """
    client = create_openai_client()
    quiz_items: list[dict[str, Any]] = []
    target_count = args.limit

    for source_index, row in enumerate(rows, start=1):
        if target_count is not None and len(quiz_items) >= target_count:
            break

        parsed = parse_qna_document(row["page_content"])
        if parsed is None:
            continue

        source_question, source_answer = parsed
        quiz_number = len(quiz_items) + 1
        quiz_type = choose_quiz_type(quiz_number, args.quiz_mode)

        try:
            generated = generate_quiz_with_openai(
                client=client,
                model=args.model,
                quiz_type=quiz_type,
                source_question=source_question,
                source_answer=source_answer,
            )
        except ValueError as exc:
            print(f"skipped source row {source_index}: {exc}")
            continue

        quiz_items.append(
            {
                "id": f"qna_quiz_{quiz_number:04d}",
                "type": generated["type"],
                "question": generated["question"],
                "choices": generated["choices"],
                "answer": generated["answer"],
                "explanation": generated["explanation"],
                "score": 10,
                "source_id": row["source_id"],
                "source_question": source_question,
                "source_answer": source_answer,
                "metadata": normalize_metadata(row["metadata"]),
            }
        )
        total_label = target_count if target_count is not None else len(rows)
        print(f"generated {len(quiz_items)}/{total_label} quiz: {quiz_type}")

    return quiz_items

def save_quiz_bank(quiz_items: list[dict[str, Any]], output_path: Path) -> None:
    """quiz bank JSON 파일을 저장한다."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(quiz_items, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def print_preview(quiz_items: list[dict[str, Any]], preview_count: int) -> None:
    """생성된 문제 일부를 터미널에서 확인한다."""
    for item in quiz_items[:preview_count]:
        print("=" * 80)
        print(f"id: {item['id']}")
        print(f"type: {item['type']}")
        print(f"expert: {item['metadata'].get('expert')}")
        print(f"question: {item['question']}")
        if item.get("choices"):
            for choice_index, choice in enumerate(item["choices"], start=1):
                print(f"  {choice_index}. {choice}")
        print(f"answer: {item['answer']}")
        print(f"explanation: {item['explanation']}")


def build_qna_quiz_bank(args: argparse.Namespace) -> None:
    """QnA quiz bank 생성 전체 흐름을 실행한다."""
    load_environment()

    if args.source == "loader":
        documents = load_qna_documents_from_loader(limit=args.limit if args.quiz_mode == "source" else None)
        rows = documents_to_rows(documents)
    else:
        rows = fetch_qna_rows_from_pgvector(
            collection_name=args.collection_name,
            limit=args.limit if args.quiz_mode == "source" else None,
        )

    if args.quiz_mode == "source":
        quiz_items = build_source_items(rows)
    else:
        quiz_items = build_generated_quiz_items(rows, args)

    save_quiz_bank(quiz_items, Path(args.output))

    print(
        {
            "source": args.source,
            "quiz_mode": args.quiz_mode,
            "collection_name": args.collection_name if args.source == "pgvector" else None,
            "loaded_rows": len(rows),
            "saved_quiz_items": len(quiz_items),
            "output": str(Path(args.output).resolve()),
        }
    )
    print_preview(quiz_items, args.preview)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build QnA quiz bank JSON.")
    parser.add_argument("--source", choices=["loader", "pgvector"], default="loader")
    parser.add_argument("--quiz-mode", choices=["source", "mixed", "ox", "multiple_choice"], default="mixed")
    parser.add_argument("--collection-name", default=os.getenv("PGVECTOR_COLLECTION", DEFAULT_COLLECTION_NAME))
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT_PATH))
    parser.add_argument("--limit", type=int, default=None, help="테스트용으로 일부 QnA만 생성한다.")
    parser.add_argument("--preview", type=int, default=3, help="터미널에 미리 보여줄 문제 수")
    parser.add_argument("--model", default=os.getenv("OPENAI_CHAT_MODEL", DEFAULT_CHAT_MODEL))
    return parser.parse_args()


if __name__ == "__main__":
    build_qna_quiz_bank(parse_args())






