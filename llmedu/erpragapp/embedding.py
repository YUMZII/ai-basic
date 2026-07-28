"""
embedding.py
──────────────────────────────────────────────────────────────
OpenAI SDK를 직접 호출한다 (LangChain 등 프레임워크 미사용).
- 임베딩: text-embedding-3-small (1536차원)
- 답변 생성: gpt-4o-mini
"""
import os
from typing import List, Dict

from openai import OpenAI

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

EMBEDDING_MODEL = "text-embedding-3-small"
CHAT_MODEL = "gpt-4o-mini"

# 임베딩 API 1회 호출당 넣을 최대 텍스트 개수 (긴 PDF 대비 배치 처리)
EMBEDDING_BATCH_SIZE = 20


def get_embedding(text: str) -> List[float]:
    """단일 텍스트를 임베딩 벡터로 변환한다."""
    cleaned = text.replace("\n", " ").strip()
    resp = client.embeddings.create(model=EMBEDDING_MODEL, input=cleaned)
    return resp.data[0].embedding


def get_embeddings_batch(texts: List[str]) -> List[List[float]]:
    """
    여러 텍스트를 배치로 임베딩한다.
    (PDF 페이지 수가 많아도 API 호출 횟수를 줄여 적재 속도를 높인다)
    """
    cleaned_texts = [t.replace("\n", " ").strip() for t in texts]
    all_embeddings: List[List[float]] = []

    for i in range(0, len(cleaned_texts), EMBEDDING_BATCH_SIZE):
        batch = cleaned_texts[i:i + EMBEDDING_BATCH_SIZE]
        resp = client.embeddings.create(model=EMBEDDING_MODEL, input=batch)
        all_embeddings.extend(d.embedding for d in resp.data)

    return all_embeddings


def ask_llm(question: str, context_chunks: List[Dict]) -> str:
    """검색된 청크(페이지)를 컨텍스트로 삼아 답변을 생성한다."""
    context_text = "\n\n".join(
        f"[출처: {c['filename']} p.{c['page_number']}]\n{c['content']}"
        for c in context_chunks
    )

    system_prompt = (
        "당신은 제공된 ERP 백서 문서를 근거로만 답변하는 어시스턴트입니다. "
        "컨텍스트에 없는 내용은 추측하지 말고 '문서에서 확인되지 않습니다'라고 답하세요. "
        "답변은 한국어로 작성하고, 필요하면 목록으로 정리해 간결하게 설명하세요."
    )
    user_prompt = f"[컨텍스트]\n{context_text}\n\n[질문]\n{question}"

    resp = client.chat.completions.create(
        model=CHAT_MODEL,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0.2,
    )
    return resp.choices[0].message.content
