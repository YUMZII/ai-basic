"""
rag.py
──────────────────────────────────────────────────────────────
질문을 임베딩한 뒤, pgvector의 코사인 거리 연산자(<=>)로
가장 유사한 페이지(청크)를 검색한다.
"""
from typing import List, Dict, Optional

from db import get_connection
from embedding import get_embedding

TOP_K = 5


def search_similar_chunks(
    question: str,
    section: Optional[str] = None,
    top_k: int = TOP_K,
) -> List[Dict]:
    """질문과 가장 유사한 청크 top_k개를 반환한다. section 지정 시 해당 산업만 검색."""
    query_embedding = get_embedding(question)

    conn = get_connection()
    try:
        with conn.cursor() as cur:
            if section:
                cur.execute(
                    """
                    SELECT filename, page_number, section, content,
                           embedding <=> %s::vector AS distance
                    FROM erpdocuments2
                    WHERE section = %s
                    ORDER BY distance ASC
                    LIMIT %s
                    """,
                    (query_embedding, section, top_k),
                )
            else:
                cur.execute(
                    """
                    SELECT filename, page_number, section, content,
                           embedding <=> %s::vector AS distance
                    FROM erpdocuments2
                    ORDER BY distance ASC
                    LIMIT %s
                    """,
                    (query_embedding, top_k),
                )
            return cur.fetchall()
    finally:
        conn.close()
