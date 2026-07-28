"""
scripts/ingest_local.py
──────────────────────────────────────────────────────────────
API 서버를 거치지 않고, 로컬 PDF 파일을 바로 DB에 적재하는 CLI 스크립트.
강의 실습 시 샘플 문서(erp.pdf)를 미리 적재해둘 때 사용한다.

사용법:
    python scripts/ingest_local.py ./erp.pdf
"""
import sys
import os

# 상위 디렉토리(프로젝트 루트)의 모듈을 import 하기 위한 경로 추가
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

from db import init_db
from ingest import ingest_pdf


def main():
    if len(sys.argv) != 2:
        print("사용법: python scripts/ingest_local.py <PDF 경로>")
        sys.exit(1)

    pdf_path = sys.argv[1]
    if not os.path.isfile(pdf_path):
        print(f"파일을 찾을 수 없습니다: {pdf_path}")
        sys.exit(1)

    print("DB 초기화 확인 중...")
    init_db()

    with open(pdf_path, "rb") as f:
        file_bytes = f.read()

    filename = os.path.basename(pdf_path)
    print(f"'{filename}' 적재를 시작합니다...")

    inserted = ingest_pdf(filename, file_bytes)
    print(f"완료: {inserted}개 페이지가 erpdocuments2 테이블에 적재되었습니다.")


if __name__ == "__main__":
    main()
