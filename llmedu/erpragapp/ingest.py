"""
ingest.py
──────────────────────────────────────────────────────────────
PDF 문서를 "페이지 단위 청크"로 나누어 erpdocuments2 테이블에 적재한다.
- pypdf 로 페이지별 텍스트 추출 (별도의 텍스트 스플리터 사용 안 함)
- 1 페이지 = 1 청크 = 1 임베딩 = 1 row
"""
from io import BytesIO
from typing import List, Tuple

from pypdf import PdfReader

from db import get_connection
from embedding import get_embeddings_batch

# 산업 섹션 자동 태깅용 키워드 (프론트엔드 필터: 제약/의료기기/화장품)
SECTION_KEYWORDS = {
    "제약": ["제약", "GMP", "마약류", "LIMS", "일련번호"],
    "의료기기": ["의료기기", "BOM", "MES", "설계 변경"],
    "화장품": ["화장품", "CGMP", "K-뷰티", "사방넷", "3PL"],
}


def detect_section(text: str) -> str:
    """페이지 텍스트에 등장하는 키워드 빈도로 산업 섹션을 단순 추정한다."""
    scores = {sec: 0 for sec in SECTION_KEYWORDS}
    for sec, keywords in SECTION_KEYWORDS.items():
        for kw in keywords:
            scores[sec] += text.count(kw)

    best_section = max(scores, key=scores.get)
    return best_section if scores[best_section] > 0 else "공통"


def extract_pages(file_bytes: bytes) -> List[str]:
    """PDF 바이트를 받아 페이지별 텍스트 리스트를 반환한다 (인덱스 0 = 1페이지)."""
    reader = PdfReader(BytesIO(file_bytes))
    return [(page.extract_text() or "").strip() for page in reader.pages]


def ingest_pdf(filename: str, file_bytes: bytes) -> int:
    """
    PDF를 페이지 단위로 쪼개 임베딩 후 DB에 저장한다.
    반환값: 실제로 적재된 페이지 수 (텍스트가 없는 페이지는 제외)
    """
    pages = extract_pages(file_bytes)

    valid_pages: List[Tuple[int, str]] = [
        (page_no, text) for page_no, text in enumerate(pages, start=1) if text
    ]
    if not valid_pages:
        return 0

    texts = [text for _, text in valid_pages]
    embeddings = get_embeddings_batch(texts)

    conn = get_connection()
    try:
        with conn.cursor() as cur:
            for (page_no, text), embedding in zip(valid_pages, embeddings):
                section = detect_section(text)
                cur.execute(
                    """
                    INSERT INTO erpdocuments2
                        (filename, page_number, section, content, embedding)
                    VALUES (%s, %s, %s, %s, %s)
                    """,
                    (filename, page_no, section, text, embedding),
                )
        conn.commit()
    finally:
        conn.close()

    return len(valid_pages)
