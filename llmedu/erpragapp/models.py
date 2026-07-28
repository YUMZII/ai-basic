"""
models.py
──────────────────────────────────────────────────────────────
FastAPI 요청/응답에 사용하는 Pydantic 모델 모음.
"""
from typing import List, Optional

from pydantic import BaseModel


class AskRequest(BaseModel):
    question: str
    section: Optional[str] = None


class SourceItem(BaseModel):
    content: str
    section: str
    page: int
    chunkIndex: int


class AskResponse(BaseModel):
    answer: str
    sources: List[SourceItem]


class IngestResponse(BaseModel):
    filename: str
    pages_inserted: int
    message: str


class CountResponse(BaseModel):
    count: int
