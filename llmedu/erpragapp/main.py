"""
main.py
──────────────────────────────────────────────────────────────
ERP IntelliQ - FastAPI 기반 RAG 챗봇 서버
프레임워크(LangChain 등) 없이 순수 Python + psycopg2 + FastAPI로 구현했다.

실행:
    uvicorn main:app --reload
"""
from dotenv import load_dotenv
load_dotenv()  # DB_CONFIG, OPENAI_API_KEY 등을 다른 모듈이 import 하기 전에 로드

from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware

from db import init_db, get_connection
from ingest import ingest_pdf
from rag import search_similar_chunks
from embedding import ask_llm
from models import AskRequest, AskResponse, IngestResponse, CountResponse

app = FastAPI(title="ERP IntelliQ RAG API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def on_startup():
    """서버 시작 시 pgvector 확장/테이블을 준비한다."""
    init_db()


# ── 정적 페이지 ──────────────────────────────────────────────
@app.get("/")
def serve_chat_page():
    return FileResponse("static/index.html")


@app.get("/ingest")
def serve_ingest_page():
    return FileResponse("static/ingest.html")


# ── API ──────────────────────────────────────────────────────
@app.get("/api/chunks/count", response_model=CountResponse)
def get_chunk_count():
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) AS cnt FROM erpdocuments2")
            row = cur.fetchone()
        return {"count": row["cnt"]}
    finally:
        conn.close()


@app.post("/api/ingest", response_model=IngestResponse)
async def ingest_document(file: UploadFile = File(...)):
    """PDF를 업로드받아 페이지 단위로 청크를 나누고 임베딩하여 적재한다."""
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(400, "PDF 파일만 업로드할 수 있습니다.")

    file_bytes = await file.read()
    inserted = ingest_pdf(file.filename, file_bytes)

    if inserted == 0:
        raise HTTPException(422, "PDF에서 추출할 텍스트가 없습니다. (스캔본 이미지 PDF는 미지원)")

    return {
        "filename": file.filename,
        "pages_inserted": inserted,
        "message": f"'{file.filename}' 문서에서 {inserted}개 페이지가 적재되었습니다.",
    }


@app.delete("/api/chunks")
def clear_chunks():
    """적재된 모든 청크를 삭제한다 (실습 초기화용)."""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM erpdocuments2")
        conn.commit()
        return {"message": "모든 청크가 삭제되었습니다."}
    finally:
        conn.close()


@app.post("/api/ask", response_model=AskResponse)
def ask(req: AskRequest):
    """질문 -> 벡터 검색(Top-K) -> LLM 답변 생성의 RAG 파이프라인."""
    if not req.question.strip():
        raise HTTPException(400, "질문을 입력해 주세요.")

    chunks = search_similar_chunks(req.question, req.section)
    if not chunks:
        return {
            "answer": "적재된 문서가 없거나 관련 내용을 찾을 수 없습니다. 먼저 /ingest 페이지에서 PDF를 적재해 주세요.",
            "sources": [],
        }

    answer = ask_llm(req.question, chunks)

    sources = [
        {
            "content": c["content"][:300],  # 미리보기용으로 앞부분만 전달
            "section": c["section"],
            "page": c["page_number"],
            "chunkIndex": i + 1,
        }
        for i, c in enumerate(chunks)
    ]

    return {"answer": answer, "sources": sources}
