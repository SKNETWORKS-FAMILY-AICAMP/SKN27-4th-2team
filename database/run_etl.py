"""
ETL 파이프라인 실행
    - 관계형 데이터베이스에 데이터 적재(tools/build_RDB.py)
    - 벡터 스토어 구축(tools/build_vectorstore.py)
"""

import argparse
import sys
import subprocess
from pathlib import Path


DATABASE_DIR = Path(__file__).resolve().parent

# === 필수 문서 경로 정의 ===
REQUIRED_FILES_FOR_RDB = [
    DATABASE_DIR / "contents" / "dog_api" / "dogapi_akc_matched_breeds_ko.json",
]

REQUIRED_FILES_FOR_VECTORSTORE = [
    DATABASE_DIR / "docs" / "akc_dog_info" / "akc_breed_info_vector_documents.json",
    DATABASE_DIR / "docs" / "youtube" / "youtube_basic_instruction.json",
    DATABASE_DIR / "docs" / "youtube" / "youtube_vet_knowledge.json",
    DATABASE_DIR / "docs" / "youtube_qna" / "final_seol_qna.jsonl",
    DATABASE_DIR / "docs" / "youtube_qna" / "kang_qna.jsonl",
]


def check_file_exists(file_path: Path, description: str) -> bool:
    """파일 존재 여부 확인"""
    if file_path.exists():
        print(f"✓ {description}: {file_path}")
        return True
    else:
        print(f"✗ {description}: 파일 없음 - {file_path}")
        return False


def check_article_files() -> bool:
    """article_*.json 파일 존재 여부 확인"""
    article_files = sorted((DATABASE_DIR / "docs").glob("article_*.json"))
    if article_files:
        print(f"✓ Article 문서: {len(article_files)}개 파일 발견")
        return True
    else:
        print(f"✗ Article 문서: 파일 없음 (database/docs/article_*.json)")
        return False


def check_rdb_requirements() -> bool:
    """RDB 적재에 필요한 모든 파일 확인"""
    print("\n=== RDB 적재 필수 문서 확인 ===")
    all_exist = True
    
    for file_path in REQUIRED_FILES_FOR_RDB:
        if not check_file_exists(file_path, "개 품종 데이터 JSON"):
            all_exist = False
    
    return all_exist


def check_vectorstore_requirements() -> bool:
    """VectorStore 구축에 필요한 모든 파일 확인"""
    print("\n=== VectorStore 구축 필수 문서 확인 ===")
    all_exist = True
    
    for file_path in REQUIRED_FILES_FOR_VECTORSTORE:
        file_type = file_path.stem.replace("_", " ").title()
        if not check_file_exists(file_path, f"{file_type} 문서"):
            all_exist = False
    
    if not check_article_files():
        all_exist = False
    
    return all_exist


def run_build_rdb(args: argparse.Namespace) -> bool:
    """build_RDB.py 실행"""
    print("\n" + "=" * 60)
    print("RDB 적재 시작")
    print("=" * 60)
    
    try:
        cmd = ["python", "tools/build_RDB.py"]
        if args.truncate_rdb:
            cmd.append("--truncate")
        
        result = subprocess.run(cmd, cwd=DATABASE_DIR, check=True)
        print("✓ RDB 적재 완료")
        return True
    except subprocess.CalledProcessError as e:
        print(f"✗ RDB 적재 실패: {e}")
        return False
    except Exception as e:
        print(f"✗ RDB 적재 중 오류: {e}")
        return False


def run_build_vectorstore(args: argparse.Namespace) -> bool:
    """build_vectorstore.py 실행"""
    print("\n" + "=" * 60)
    print("VectorStore 구축 시작")
    print("=" * 60)
    
    try:
        cmd = ["python", "tools/build_vectorstore.py"]
        if args.reset_vectorstore:
            cmd.append("--reset")
        if args.limit:
            cmd.extend(["--limit", str(args.limit)])
        if args.batch_size:
            cmd.extend(["--batch-size", str(args.batch_size)])
        
        result = subprocess.run(cmd, cwd=DATABASE_DIR, check=True)
        print("✓ VectorStore 구축 완료")
        return True
    except subprocess.CalledProcessError as e:
        print(f"✗ VectorStore 구축 실패: {e}")
        return False
    except Exception as e:
        print(f"✗ VectorStore 구축 중 오류: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(
        description="Dog Breed ETL Pipeline - RDB와 VectorStore 구축"
    )
    
    parser.add_argument(
        "--mode",
        choices=["all", "rdb", "vectorstore"],
        default="all",
        help="실행 모드 (기본값: all)"
    )
    parser.add_argument(
        "--skip-check",
        action="store_true",
        help="문서 존재 여부 확인 생략"
    )
    parser.add_argument(
        "--truncate-rdb",
        action="store_true",
        help="RDB 기존 데이터 삭제 후 재생성"
    )
    parser.add_argument(
        "--reset-vectorstore",
        action="store_true",
        help="VectorStore 기존 collection 삭제 후 재생성"
    )
    parser.add_argument(
        "--limit",
        type=int,
        help="VectorStore 구축 시 테스트용 문서 개수 제한"
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        help="VectorStore 구축 시 배치 크기 조정"
    )
    
    args = parser.parse_args()
    
    # 문서 존재 여부 확인
    if not args.skip_check:
        rdb_ok = check_rdb_requirements()
        vectorstore_ok = check_vectorstore_requirements()
        
        if args.mode == "rdb" and not rdb_ok:
            print("\n❌ RDB 적재에 필요한 문서가 부족합니다.")
            sys.exit(1)
        elif args.mode == "vectorstore" and not vectorstore_ok:
            print("\n❌ VectorStore 구축에 필요한 문서가 부족합니다.")
            sys.exit(1)
        elif args.mode == "all" and (not rdb_ok or not vectorstore_ok):
            print("\n❌ ETL 파이프라인 실행에 필요한 문서가 부족합니다.")
            sys.exit(1)
    
    # 파이프라인 실행
    print("\n" + "=" * 60)
    print("ETL 파이프라인 시작")
    print("=" * 60)
    
    success = True
    
    if args.mode in ["all", "rdb"]:
        if not run_build_rdb(args):
            success = False
    
    if args.mode in ["all", "vectorstore"]:
        if not run_build_vectorstore(args):
            success = False
    
    # 최종 결과
    print("\n" + "=" * 60)
    if success:
        print("✓ ETL 파이프라인 완료!")
    else:
        print("✗ ETL 파이프라인 중 오류 발생")
        sys.exit(1)
    print("=" * 60)


if __name__ == "__main__":
    main()