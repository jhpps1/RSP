# Paper Similarity Search System

AI/ML 논문 벡터 검색과 유사도 그래프 UI다. 논문 수집은 하지 않는다. 수집과 임베딩은 [auto_collecting_paper](https://github.com/jhpps1/auto_collecting_paper)가 같은 PostgreSQL `paperdb`에 쓰고, 이 API는 그 `papers` 테이블을 읽는다. 두 프로세스는 서로를 호출하지 않는다.

## 목차

- [기능](#기능)
- [구조](#구조)
- [기술 스택](#기술-스택)
- [실행](#실행)
- [API](#api)
- [화면에서 쓰는 법](#화면에서-쓰는-법)
- [데이터](#데이터)
- [개발](#개발)
- [문제 해결](#문제-해결)

## 기능

### 논문 검색

질의 문장을 `all-MiniLM-L6-v2`로 임베딩하고, pgvector 코사인 거리로 `papers.embedding`을 찾는다. 필터는 인용 수, 발행 연도, 저널명, Open Access 상태다. 응답 시간 측정값은 이 저장소에 없다.

### 마인드맵

왼쪽 25%는 논문 목록, 오른쪽 75%는 관계 그래프다. Vis.js force-directed 네트워크를 쓰고, 유사도 0.4 이상인 논문만 선으로 잇는다. 노드 클릭, 확대, 축소, 드래그가 된다.

### PDF

저장된 OpenAlex `open_access.oa_url`만 연다. 그 링크가 없으면 PDF를 찾지 않는다.

### 샘플 데이터

스키마와 임베딩이 없는 샘플 3건은 `init.sql`에 있다. 벡터 검색(`embedding IS NOT NULL`)에는 나오지 않는다. 검색에 쓰려면 수집 저장소가 같은 DB에 논문을 넣고 `all-MiniLM-L6-v2` 임베딩을 채워야 한다.

## 구조

```text
Web (HTML/JS/CSS)  ->  FastAPI  ->  PostgreSQL + pgvector
                         |
                       Redis (검색 결과 캐시)
```

수집 프로세스는 이 그림 밖에 있다. OpenAlex를 호출해 `paperdb`에 쓰고 끝난다.

프론트는 `web/public/`이다. `index.html`이 화면, `app.js`가 그래프와 API, `style.css`가 스타일이다.

API는 `api/`이다. `main.py`가 앱과 라우팅, `search.py`가 벡터 검색과 그래프, `embedder.py`가 질의를 384차원으로 임베딩, `database.py`가 PostgreSQL과 Redis 연결이다.

## 기술 스택

| 구분 | 기술 |
| --- | --- |
| API | FastAPI, uvicorn, asyncpg, SentenceTransformers `all-MiniLM-L6-v2` |
| 데이터 | PostgreSQL 16 (`pgvector/pgvector:pg16`), Redis 검색 결과 캐시 |
| 프론트 | Vis.js Network, Bootstrap 5, Axios, Font Awesome |
| 실행 | Docker Compose로 postgres, redis, api, web을 같이 기동 |

Redis 클라이언트는 `redis.asyncio`다. `requirements.txt`의 `aioredis`는 API 코드에서 쓰지 않는다.

## 실행

필요 조건은 Docker, Docker Compose, Git이다. 임베딩 모델을 올리려면 메모리 4GB 이상을 본다.

```bash
git clone https://github.com/jhpps1/RSP.git
cd RSP
cp .env.example .env
docker-compose up -d
docker-compose logs -f api
```

논문 행과 임베딩은 이 저장소가 만들지 않는다. `auto_collecting_paper`를 같은 `paperdb`에 연결해 수집한 뒤 `embedding_generator.py`를 실행한다. 두 저장소의 DB 이름, 계정, 임베딩 모델은 `.env.example` 기준으로 같다.

| 화면 | 주소 |
| --- | --- |
| 웹 | http://localhost:3000 |
| API 문서 | http://localhost:8000/docs |
| 헬스체크 | http://localhost:8000/health |

호스트 포트 기본값은 Postgres `5433`, Redis `6380`이다. 컨테이너 안에서는 각각 `5432`, `6379`다.

## API

검색과 그래프 요청의 기본 `similarity_threshold`는 0.5다. 그래프 간선은 요청값과 별도로 0.4를 쓴다.

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

### 그래프

```http
POST /graph-data
Content-Type: application/json

{
  "query": "neural network",
  "limit": 50,
  "similarity_threshold": 0.5
}
```

### PDF

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

## 화면에서 쓰는 법

검색창에 키워드를 넣는다. 영문이 낫다. 필요하면 필터를 걸고 검색한다. 왼쪽에서 논문 목록을 보고, 오른쪽에서 관계 그래프를 본다.

노드 크기는 인용 수, 색은 카테고리, 선 굵기는 유사도다. 유사도 슬라이더는 0.4에서 1.0까지다.

논문에 `pdf_url`이 있으면 그 주소를 연다. 없으면 원문을 다른 곳에서 찾지 않는다.

## 데이터

벡터 차원은 384다. 모델은 `all-MiniLM-L6-v2`다. 논문 수, 응답 시간, 메모리 사용량은 이 저장소에 측정값이 없다. HNSW 인덱스 생성문은 `init.sql`에 주석으로만 있다. 기본 기동은 그 인덱스를 만들지 않는다.

```sql
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
```

## 개발

API만 로컬에서 띄울 때다.

```bash
cd api
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
docker-compose up -d postgres redis
python main.py
```

Windows에서는 `venv\Scripts\activate`를 쓴다. 프론트는 별도 웹 서버나 live-server로 연다.

논문을 더 넣으려면 수집 저장소에서 같은 DB로 `full_openalex_collector.py`와 `embedding_generator.py`를 실행한다. 이 API 이미지에는 수집기가 들어 있지 않다.

## 문제 해결

API가 바로 응답하지 않으면 모델 다운로드가 끝날 때까지 기다린다. 최초 실행은 1–2분 정도 걸린다.

```bash
docker-compose ps
docker-compose logs api
```

그래프가 안 보이면 브라우저 콘솔과 네트워크 탭에서 `/graph-data` 응답을 본다.

PDF 링크가 없으면 그 행의 `pdf_url`이 비어 있는 것이다. 수집기가 OpenAlex OA 주소를 저장했는지 확인한다.

검색 결과가 없으면 검색어를 영어로 넣거나, 유사도 임계값을 0.5에서 0.3으로 낮춘다. DB에 임베딩된 논문이 있는지도 본다.

아래 인덱스는 기본 `init.sql`에 없다. 필요하면 따로 만든다.

```sql
CREATE INDEX papers_year_idx ON papers(publication_year);
CREATE INDEX papers_citations_idx ON papers(cited_by_count);
CREATE INDEX papers_concepts_idx ON papers USING gin(concepts);
```

`papers.embedding`은 `VECTOR(384)`다. `EMBEDDING_MODEL`을 바꿀 때는 수집기와 조회 서버가 같은 384차원 모델이어야 한다.

## 문의

이슈는 GitHub Issues에 남긴다. 로컬 API 문서는 http://localhost:8000/docs 다.

기여는 fork 뒤 브랜치를 만들고 pull request를 보낸다. 라이선스는 MIT다.

데이터와 라이브러리는 OpenAlex, SentenceTransformers, Vis.js를 쓴다.
