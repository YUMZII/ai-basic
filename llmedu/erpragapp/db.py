"""
db.py
──────────────────────────────────────────────────────────────
PostgreSQL(pgvector) 연결과 테이블 초기화를 담당한다.
- ORM/프레임워크 없이 순수 psycopg2만 사용
- pgvector.psycopg2 의 register_vector() 로 VECTOR 컬럼을
  파이썬 list[float] <-> DB vector 타입으로 자동 변환한다.
"""
import os

import psycopg2
from psycopg2.extras import RealDictCursor
from pgvector.psycopg2 import register_vector

# 임베딩 모델(text-embedding-3-small)의 벡터 차원
EMBEDDING_DIM = 1536

DB_CONFIG = {
    "host": os.getenv("DB_HOST", "localhost"),
    "port": os.getenv("DB_PORT", "5432"),
    "dbname": os.getenv("DB_NAME", "edudb"),
    "user": os.getenv("DB_USER", "edu"),
    "password": os.getenv("DB_PASSWORD", "1234"),
}


def get_connection():
    """
    요청마다 새 커넥션을 생성한다.
    register_vector(conn) 을 커넥션 단위로 호출해야
    해당 커넥션에서 vector 타입 어댑터가 활성화된다.
    """
    conn = psycopg2.connect(**DB_CONFIG, cursor_factory=RealDictCursor)
    register_vector(conn)
    return conn


def init_db():
    """
    앱 시작 시 1회 호출.
    - vector 확장(extension) 활성화
    - erpdocuments 테이블 생성 (페이지 단위 청크 저장)
    - 코사인 유사도 검색을 위한 ivfflat 인덱스 생성
    """
    conn = psycopg2.connect(**DB_CONFIG)
    conn.autocommit = True
    try:
        with conn.cursor() as cur:
            cur.execute("CREATE EXTENSION IF NOT EXISTS vector;")

            cur.execute(f"""
                CREATE TABLE IF NOT EXISTS erpdocuments2 (
                    id           SERIAL PRIMARY KEY,
                    filename     VARCHAR(255) NOT NULL,
                    page_number  INTEGER NOT NULL,
                    section      VARCHAR(50) DEFAULT '공통',
                    content      TEXT NOT NULL,
                    embedding    VECTOR({EMBEDDING_DIM}) NOT NULL,
                    created_at   TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)

            # ivfflat 인덱스는 데이터가 어느 정도 있어야 효율적이지만
            # 교육용 예제에서는 미리 생성해도 무방하다.
            cur.execute("""
                CREATE INDEX IF NOT EXISTS idx_erpdocuments2_embedding
                ON erpdocuments2 USING ivfflat (embedding vector_cosine_ops)
                WITH (lists = 100);
            """)
    finally:
        conn.close()
