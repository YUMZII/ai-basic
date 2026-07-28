# ERP IntelliQ — FastAPI + pgvector RAG 챗봇

Spring Boot 버전 템플릿을 **순수 Python 스택**으로 재구현한 예제입니다.
LangChain 등 프레임워크 없이 `psycopg2` + `FastAPI` + `pypdf` + `openai` SDK만으로
RAG(Retrieval-Augmented Generation) 파이프라인을 직접 구현합니다.

## 기술 스택

| 영역 | 기술 |
|---|---|
| 웹 프레임워크 | FastAPI (Uvicorn) |
| DB 드라이버 | psycopg2-binary (순수 SQL, ORM 미사용) |
| 벡터 DB | PostgreSQL + pgvector (`ankane/pgvector` 이미지) |
| PDF 파싱 | pypdf (페이지 단위 텍스트 추출) |
| 임베딩/LLM | OpenAI SDK 직접 호출 (`text-embedding-3-small`, `gpt-4o-mini`) |
| 프론트엔드 | Vanilla HTML/CSS/JS (별도 빌드 도구 없음) |

## 청크 전략

이 프로젝트는 **PDF 1페이지 = 1청크** 방식입니다.
별도의 텍스트 스플리터(토큰 기반 슬라이딩 윈도우 등)를 쓰지 않고,
`pypdf`로 추출한 페이지 텍스트를 그대로 하나의 임베딩 단위로 저장합니다.
(과도하게 긴 페이지가 있는 문서라면 이후 토큰 기반 스플리터를 추가로 얹는 식으로 확장 가능합니다.)

## 테이블 구조 (`erpdocuments2`)

```sql
CREATE TABLE erpdocuments2 (
    id           SERIAL PRIMARY KEY,
    filename     VARCHAR(255) NOT NULL,
    page_number  INTEGER NOT NULL,
    section      VARCHAR(50) DEFAULT '공통',   -- 제약/의료기기/화장품/공통 (키워드 기반 자동 태깅)
    content      TEXT NOT NULL,
    embedding    VECTOR(1536) NOT NULL,
    created_at   TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

## 실행 방법

### 1. pgvector DB 실행

```bash
docker compose up -d
```

### 2. 가상환경 및 패키지 설치

```bash
python -m venv venv
venv\Scripts\activate        # Windows
# source venv/bin/activate   # macOS/Linux

pip install -r requirements.txt
```

### 3. 환경변수 설정

`.env.example` 을 복사해 `.env` 파일을 만들고 `OPENAI_API_KEY` 를 채워 넣습니다.

```bash
copy .env.example .env        # Windows
# cp .env.example .env        # macOS/Linux
```

### 4. 서버 실행

```bash
uvicorn main:app --reload
```

- 챗봇 화면: http://localhost:8000
- 문서 적재 화면: http://localhost:8000/ingest

### 5. 문서 적재 (둘 중 하나)

- **웹 화면에서**: `/ingest` 페이지에서 PDF를 드래그 앤 드롭
- **CLI로 바로 적재** (강의용 샘플 문서를 미리 넣어둘 때 편리):

```bash
python scripts/ingest_local.py erp.pdf
```

## API 요약

| Method | Path | 설명 |
|---|---|---|
| GET | `/api/chunks/count` | 적재된 총 페이지(청크) 수 조회 |
| POST | `/api/ingest` | PDF 업로드 → 페이지 단위 청크 적재 (multipart/form-data, key=`file`) |
| DELETE | `/api/chunks` | 전체 청크 삭제 (실습 초기화용) |
| POST | `/api/ask` | 질문 → 벡터 검색(Top-5) → GPT 답변. body: `{"question": "...", "section": "제약"}` (`section`은 선택) |

## RAG 파이프라인 흐름

1. `POST /api/ingest` : PDF → `pypdf`로 페이지별 텍스트 추출 → 페이지별 임베딩 생성 → `erpdocuments2`에 INSERT
2. `POST /api/ask` : 질문 임베딩 생성 → `embedding <=> 질문벡터` (pgvector 코사인 거리)로 Top-K 페이지 검색 → 검색된 페이지를 컨텍스트로 GPT 프롬프트 구성 → 답변 반환 (출처 페이지 목록 포함)

## 프로젝트 구조

```
erp_rag_chatbot/
├── main.py              # FastAPI 앱 (라우트 정의)
├── db.py                 # psycopg2 연결 + 테이블 초기화
├── ingest.py              # PDF 페이지 단위 청크 적재 로직
├── rag.py                 # pgvector 코사인 검색
├── embedding.py            # OpenAI 임베딩/채팅 호출
├── models.py                # Pydantic 요청/응답 모델
├── static/
│   ├── index.html           # 챗봇 채팅 화면
│   └── ingest.html          # PDF 업로드 화면
├── scripts/
│   └── ingest_local.py      # 로컬 PDF 즉시 적재 CLI
├── docker-compose.yml       # pgvector DB (ankane/pgvector)
├── requirements.txt
└── .env.example
```
