from __future__ import annotations

import argparse
from pathlib import Path


def extract_pdf(path: Path) -> str:
    try:
        from pypdf import PdfReader
    except ImportError as exc:
        raise RuntimeError("pypdf가 필요합니다. pip install pypdf 후 다시 실행하세요.") from exc

    reader = PdfReader(str(path))
    pages: list[str] = []
    for page_number, page in enumerate(reader.pages, start=1):
        text = page.extract_text() or ""
        if text.strip():
            pages.append(f"\n\n## page {page_number}\n{text.strip()}")
    return "".join(pages).strip()


def extract_hwp(path: Path) -> str:
    raise RuntimeError(
        f"HWP는 자동 추출 환경 차이가 큽니다: {path.name}. "
        "한글 또는 LibreOffice에서 PDF/DOCX/TXT로 변환한 뒤 raw 폴더에 저장하는 방식을 권장합니다."
    )


def extract_text(path: Path) -> str:
    suffix = path.suffix.lower()
    if suffix == ".pdf":
        return extract_pdf(path)
    if suffix == ".hwp":
        return extract_hwp(path)
    if suffix in {".txt", ".md"}:
        return path.read_text(encoding="utf-8")
    raise RuntimeError(f"지원하지 않는 파일 형식입니다: {path.suffix}")


def main() -> None:
    parser = argparse.ArgumentParser(description="가이드 원문 문서에서 텍스트를 추출합니다.")
    parser.add_argument("sources", nargs="+", help="추출할 PDF/TXT 파일 경로")
    parser.add_argument("--out-dir", default="database/guide/raw", help="추출 텍스트 저장 폴더")
    args = parser.parse_args()

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    for source in args.sources:
        source_path = Path(source)
        text = extract_text(source_path)
        output_path = out_dir / f"{source_path.stem}.txt"
        output_path.write_text(text, encoding="utf-8")
        print(f"saved: {output_path} ({len(text):,} chars)")


if __name__ == "__main__":
    main()
