# Paper Similarity Search System

AI/ML 논문 벡터 검색과 유사도 그래프 UI다. 논문 수집은 하지 않는다. 수집·임베딩은 [auto_collecting_paper](https://github.com/jhpps1/auto_collecting_paper)가 같은 PostgreSQL `paperdb`에 쓰고, 이 API는 그 `papers` 테이블을 읽는다. 두 프로세스는 서로를 호출하지 않는다.

## 주요 기능

### 1. 지능형 논문 검색
- **의미론적 검색**: 질의 문장을 `all-MiniLM-L6-v2`로 임베딩하고, pgvector 코사인 거리로 `papers.embedding`을 찾는다
- **필터**: 인용 수, 발행 연도, 저널명, Open Access 상태
- 응답 시간 측정값은 이 저장소에 없다

### 2. 마인드맵 시각화
- **분할 레이아웃**: 왼쪽 25% 논문 목록, 오른쪽 75% 관계 그래프
- **동적 그래프**: Vis.js 기반 force-directed 네트워크 시각화
- **유사도 연결**: 0.4 이상 유사도 기준으로 논문 간 관계 표시
- **인터랙티브**: 노드 클릭, 확대/축소, 드래그 등 다양한 상호작용

### 3. PDF 접근
- 저장된 OpenAlex `open_access.oa_url`만 연다
- 그 링크가 없으면 PDF를 찾지 않는다

### 4. 데이터
- 스키마와 임베딩이 없는 샘플 3건은 `init.sql`에 있다. 벡터 검색(`embedding IS NOT NULL`)에는 나오지 않는다
- 검색에 쓰려면 수집 저장소가 같은 DB에 논문을 넣고 `all-MiniLM-L6-v2` 임베딩을 채워야 한다

## 시스템 아키텍처

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Web Frontend  │    │   FastAPI       │    │   PostgreSQL    │
│   (HTML/JS/CSS) │────│   Backend       │────│   + pgvector    │
│                 │    │                 │    │                 │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         │              ┌─────────────────┐              │
         │              │     Redis       │              │
         └──────────────│     Cache       │──────────────┘
                        │                 │
                        └─────────────────┘
```

수집 프로세스는 이 그림 밖에 있다. OpenAlex를 호출해 `paperdb`에 쓰고 끝난다.

### 핵심 컴포넌트

#### Frontend (web/public/)
- **index.html**: 반응형 Bootstrap UI, 분할 레이아웃
- **app.js**: Vis.js 그래프, API 연동, PDF 다운로드 로직
- **style.css**: 맞춤형 스타일링, 그래프 최적화

#### Backend (api/)
- **main.py**: FastAPI 애플리케이션, CORS, 라우팅
- **search.py**: 벡터 검색, 유사도 계산, 그래프 데이터 생성
- **embedder.py**: 질의 문장을 `all-MiniLM-L6-v2`(384차원)로 임베딩
- **database.py**: PostgreSQL + Redis 연결 관리

## 기술 스택

### Backend
- **FastAPI**: 고성능 Python 웹 프레임워크
- **PostgreSQL 16**: `pgvector/pgvector:pg16`
- **Redis**: 검색 결과 캐시
- **SentenceTransformers**: all-MiniLM-L6-v2 임베딩 모델
- **asyncpg**: 비동기 PostgreSQL 드라이버
- **redis.asyncio**: 비동기 Redis 클라이언트. `requirements.txt`의 `aioredis`는 API 코드에서 쓰지 않는다

### Frontend
- **Vis.js Network**: 고성능 그래프 시각화
- **Bootstrap 5**: 반응형 UI 프레임워크
- **Axios**: HTTP 클라이언트
- **Font Awesome**: 아이콘 세트

### DevOps
- **Docker Compose**: postgres, redis, api, web을 한 번에 기동
- **uvicorn**: ASGI 서버

## 설치 및 실행

### 1. 필수 요구사항
```bash
- Docker & Docker Compose
- Git
- 최소 4GB RAM (임베딩 모델 로딩용)
```

### 2. 프로젝트 클론
```bash
git clone https://github.com/jhpps1/RSP.git
cd RSP
```

### 3. 환경 설정
```bash
# 환경 변수 파일 생성
cp .env.example .env

# 필요시 데이터베이스 설정 수정
vim .env
```

### 4. Docker Compose 실행
```bash
# 전체 서비스 시작
docker-compose up -d

# 로그 확인
docker-compose logs -f api
```

논문 행과 임베딩은 이 저장소가 만들지 않는다. `auto_collecting_paper`를 같은 `paperdb`에 연결해 수집한 뒤 `embedding_generator.py`를 실행한다. 두 저장소의 DB 이름, 계정, 임베딩 모델은 `.env.example` 기준으로 같다.

### 5. 서비스 확인
- **웹 인터페이스**: http://localhost:3000
- **API 문서**: http://localhost:8000/docs
- **헬스체크**: http://localhost:8000/health

호스트 포트 기본값은 Postgres `5433`, Redis `6380`이다. 컨테이너 안에서는 각각 `5432`, `6379`다. `.env.example`을 본다.

## API 문서

### 논문 검색
```http
POST /search
Content-Type: application/json

{
  "query": "deep learning transformer",
  "limit": 20,
  "similarity_threshold": 0.5
}
```

검색과 그래프 요청의 기본 `similarity_threshold`는 0.5다. 그래프 간선은 요청값과 별도로 0.4를 쓴다.

### 그래프 데이터
```http
POST /graph-data
Content-Type: application/json

{
  "query": "neural network",
  "limit": 50,
  "similarity_threshold": 0.5
}
```

### PDF 접근
```http
POST /pdf
Content-Type: application/json

{
  "doi": "10.1038/nature14539"
}
```

### 고급 검색
```http
POST /search/advanced
Content-Type: application/json

{
  "query": "attention mechanism",
  "min_citations": 100,
  "year_from": 2020,
  "year_to": 2024,
  "open_access_only": true,
  "limit": 30
}
```

## 사용 방법

### 1. 기본 검색
1. 검색창에 키워드 입력 (영문 권장)
2. 고급 옵션에서 필터 설정 (선택사항)
3. 검색 버튼 클릭
4. 왼쪽 패널에서 논문 목록 확인
5. 오른쪽 패널에서 관계 그래프 탐색

### 2. 그래프 탐색
- **노드 크기**: 인용 수에 비례
- **노드 색상**: 카테고리별 구분
- **엣지 굵기**: 유사도에 비례
- **유사도 슬라이더**: 연결 임계값 조정 (0.4~1.0)

### 3. PDF
- 논문에 `pdf_url`이 있으면 그 주소를 연다
- 없으면 원문을 다른 곳에서 찾지 않는다

## 데이터

- 벡터 차원은 384다. 모델은 `all-MiniLM-L6-v2`
- 논문 수, 응답 시간, 메모리 사용량은 이 저장소에 측정값이 없다
- HNSW 인덱스 생성문은 `init.sql`에 주석으로만 있다. 기본 기동은 그 인덱스를 만들지 않는다

## 개발 가이드

### 로컬 개발 환경
```bash
# Python 가상환경 설정
cd api
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt

# 데이터베이스 설정
docker-compose up -d postgres redis

# API 서버 실행
python main.py

# 프론트엔드는 별도 웹서버 또는 live-server 사용
```

### 새로운 논문 추가

수집 저장소에서 같은 DB로 `full_openalex_collector.py`와 `embedding_generator.py`를 실행한다. 이 API 이미지에는 수집기가 들어 있지 않다.

### 데이터베이스 스키마
```sql
-- 논문 테이블
CREATE TABLE papers (
    id SERIAL PRIMARY KEY,
    openalex_id TEXT UNIQUE,
    doi TEXT,
    title TEXT NOT NULL,
    abstract TEXT,
    authors TEXT[],
    categories TEXT[],
    concepts TEXT[],
    published_date DATE,
    publication_year INTEGER,
    journal_name TEXT,
    cited_by_count INTEGER DEFAULT 0,
    fwci REAL,
    open_access_status TEXT,
    pdf_url TEXT,
    paper_source TEXT DEFAULT 'openalex',
    full_text TEXT,
    grobid_data JSONB,
    grobid_status TEXT,
    keywords TEXT,
    embedding vector(384),
    embedding_model TEXT,
    embedding_generated_at TIMESTAMP,
    updated_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- HNSW 인덱스는 init.sql에 주석으로만 있다.
-- CREATE INDEX papers_embedding_idx ON papers
-- USING hnsw (embedding vector_cosine_ops);
```

## 문제 해결

### 자주 발생하는 문제

#### 1. API 서버 응답 없음
```bash
# 컨테이너 상태 확인
docker-compose ps

# API 로그 확인
docker-compose logs api

# 임베딩 모델 다운로드 완료 대기 (최초 실행시 1-2분)
```

#### 2. 그래프가 표시되지 않음
```bash
# 브라우저 콘솔에서 JavaScript 에러 확인
# F12 > Console 탭

# 네트워크 탭에서 API 호출 상태 확인
# F12 > Network 탭
```

#### 3. PDF 링크가 없음
- 그 논문 행의 `pdf_url`이 비어 있으면 API는 링크를 만들지 않는다
- 수집기가 OpenAlex OA 주소를 저장했는지 확인한다

#### 4. 검색 결과 없음
- 검색어를 영어로 입력
- 유사도 임계값 낮추기 (0.5 → 0.3)
- 데이터베이스 논문 수 확인

### 성능 최적화

#### 1. 검색 속도 향상
```sql
-- 추가 인덱스 생성
CREATE INDEX papers_year_idx ON papers(publication_year);
CREATE INDEX papers_citations_idx ON papers(cited_by_count);
CREATE INDEX papers_concepts_idx ON papers USING gin(concepts);
```

#### 2. 메모리 사용량 줄이기
`papers.embedding`은 `VECTOR(384)`다. `EMBEDDING_MODEL`을 바꿀 때는 수집기와 조회 서버가 같은 384차원 모델이어야 한다.

## 지원 및 문의

### 기술 문의
- 이슈 등록: GitHub Issues
- API 문서: http://localhost:8000/docs

### 기여하기
1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request

## 라이선스

이 프로젝트는 MIT 라이선스 하에 배포됩니다.

## 감사의 글

- **OpenAlex**: 오픈 학술 데이터 제공
- **SentenceTransformers**: 임베딩 모델 제공
- **Vis.js**: 그래프 시각화 라이브러리

*스키마와 실행 설명은 현재 compose, `init.sql`, 수집 저장소와 맞춘 상태다.*
