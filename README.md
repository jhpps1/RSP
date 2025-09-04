# Paper Similarity Search System

AI/ML 논문 벡터 검색 및 유사도 시각화 시스템입니다. OpenAlex API와 Sci-Hub를 연동하여 논문 데이터를 수집하고, 의미론적 검색과 그래프 기반 관계 시각화를 제공합니다.

## 🌟 주요 기능

### 1. 지능형 논문 검색
- **의미론적 검색**: SentenceTransformers 기반 벡터 유사도 검색
- **고급 필터링**: 인용 수, 발행 연도, 저널명, Open Access 상태 등
- **실시간 검색**: 빠른 응답 시간과 정확한 결과 제공

### 2. 마인드맵 시각화
- **분할 레이아웃**: 왼쪽 25% 논문 목록, 오른쪽 75% 관계 그래프
- **동적 그래프**: Vis.js 기반 force-directed 네트워크 시각화
- **유사도 연결**: 0.4 이상 유사도 기준으로 논문 간 관계 표시
- **인터랙티브**: 노드 클릭, 확대/축소, 드래그 등 다양한 상호작용

### 3. PDF 접근 시스템
- **다중 소스**: OpenAlex 직접 링크 + Sci-Hub 자동 fallback
- **스마트 라우팅**: Open Access 우선, Closed Access는 Sci-Hub 연동
- **다중 미러**: 8개 Sci-Hub 미러 도메인으로 안정성 확보

### 4. 대용량 데이터
- **1,119개 논문**: AI/ML 분야 고품질 논문 컬렉션
- **30개 카테고리**: Deep Learning, NLP, Computer Vision 등 세분화
- **실시간 확장**: OpenAlex API를 통한 지속적 데이터 업데이트

## 🏗️ 시스템 아키텍처

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
                                 │
                        ┌─────────────────┐
                        │   External APIs │
                        │   - OpenAlex    │
                        │   - Sci-Hub     │
                        └─────────────────┘
```

### 핵심 컴포넌트

#### Frontend (web/public/)
- **index.html**: 반응형 Bootstrap UI, 분할 레이아웃
- **app.js**: Vis.js 그래프, API 연동, PDF 다운로드 로직
- **style.css**: 맞춤형 스타일링, 그래프 최적화

#### Backend (api/)
- **main.py**: FastAPI 애플리케이션, CORS, 라우팅
- **search.py**: 벡터 검색, 유사도 계산, 그래프 데이터 생성
- **embedder.py**: SentenceTransformers 임베딩 생성
- **scihub_client.py**: Sci-Hub 다중 미러 클라이언트
- **openalex_fetcher.py**: OpenAlex API 데이터 수집
- **database.py**: PostgreSQL + Redis 연결 관리

## 🚀 기술 스택

### Backend
- **FastAPI**: 고성능 Python 웹 프레임워크
- **PostgreSQL 15**: 벡터 검색을 위한 pgvector 확장
- **Redis**: 검색 결과 캐싱, 세션 관리
- **SentenceTransformers**: all-MiniLM-L6-v2 임베딩 모델
- **asyncpg**: 비동기 PostgreSQL 드라이버
- **aioredis**: 비동기 Redis 클라이언트

### Frontend
- **Vis.js Network**: 고성능 그래프 시각화
- **Bootstrap 5**: 반응형 UI 프레임워크
- **Axios**: HTTP 클라이언트
- **Font Awesome**: 아이콘 세트

### External APIs
- **OpenAlex**: 학술 논문 메타데이터
- **Sci-Hub**: PDF 원문 접근 (8개 미러)

### DevOps
- **Docker Compose**: 마이크로서비스 오케스트레이션
- **Nginx**: 리버스 프록시, 정적 파일 서빙
- **uvicorn**: ASGI 서버

## 📦 설치 및 실행

### 1. 필수 요구사항
```bash
- Docker & Docker Compose
- Git
- 최소 4GB RAM (임베딩 모델 로딩용)
```

### 2. 프로젝트 클론
```bash
git clone <repository-url>
cd similarity
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

# 초기 데이터 로딩 (선택사항)
docker-compose exec api python openalex_fetcher.py
```

### 5. 서비스 확인
- **웹 인터페이스**: http://localhost
- **API 문서**: http://localhost:8000/docs
- **헬스체크**: http://localhost:8000/health

## 📚 API 문서

### 논문 검색
```http
POST /search
Content-Type: application/json

{
  "query": "deep learning transformer",
  "limit": 20,
  "similarity_threshold": 0.7
}
```

### 그래프 데이터
```http
POST /graph-data
Content-Type: application/json

{
  "query": "neural network",
  "limit": 50,
  "similarity_threshold": 0.6
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

## 💡 사용 방법

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

### 3. PDF 다운로드
- **Open Access**: 직접 다운로드
- **Closed Access**: Sci-Hub 자동 검색
- **실패시**: Sci-Hub 웹사이트 연결

## 📊 성능 지표

### 데이터 규모
- **총 논문 수**: 1,119개
- **카테고리**: 30개 AI/ML 분야
- **평균 인용 수**: 85회
- **벡터 차원**: 384차원

### 응답 성능
- **검색 응답**: 평균 200ms
- **그래프 생성**: 평균 500ms
- **PDF 검색**: 평균 2-5초 (Sci-Hub 의존)
- **임베딩 생성**: 논문당 50ms

### 시스템 리소스
- **RAM 사용량**: 약 2GB (임베딩 모델 포함)
- **디스크 사용량**: 약 500MB (논문 메타데이터)
- **네트워크**: OpenAlex + Sci-Hub API 호출

## 🛠️ 개발 가이드

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
```bash
# OpenAlex에서 특정 키워드 논문 수집
docker-compose exec api python -c "
from openalex_fetcher import OpenAlexFetcher
fetcher = OpenAlexFetcher()
papers = fetcher.fetch_papers_by_keywords(['quantum computing'], max_results=50)
print(f'Found {len(papers)} papers')
"
```

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
    embedding vector(384),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 벡터 검색 인덱스
CREATE INDEX papers_embedding_idx ON papers 
USING ivfflat (embedding vector_cosine_ops);
```


## 🔧 문제 해결

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

#### 3. PDF 다운로드 실패
- Sci-Hub 미러 상태 확인 (일부 미러는 일시적 차단 가능)
- DOI 형식 확인
- 네트워크 연결 상태 확인

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
```python
# api/embedder.py에서 모델 크기 조정
model_name = "all-MiniLM-L6-v2"  # 현재 (80MB)
# model_name = "all-distilroberta-v1"  # 대안 (290MB, 더 정확)
```

## 🚀 향후 계획

### 단기 목표 (1-2개월)
- [ ] 실시간 검색 자동완성
- [ ] 논문 즐겨찾기 기능
- [ ] 검색 기록 저장
- [ ] 모바일 최적화

### 중기 목표 (3-6개월)
- [ ] 다국어 지원 (한국어 논문 포함)
- [ ] 인용 관계 그래프
- [ ] 논문 요약 AI
- [ ] 사용자 계정 시스템

### 장기 목표 (6-12개월)
- [ ] arXiv 실시간 동기화
- [ ] 협업 논문 추천
- [ ] 연구 트렌드 분석
- [ ] 논문 품질 평가 AI

## 📞 지원 및 문의

### 기술 문의
- 이슈 등록: GitHub Issues
- 개발 문서: `/docs` 디렉토리
- API 문서: http://localhost:8000/docs

### 기여하기
1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request

## 📄 라이선스

이 프로젝트는 MIT 라이선스 하에 배포됩니다.

## 🙏 감사의 글

- **OpenAlex**: 오픈 학술 데이터 제공
- **Sci-Hub**: 학술 논문 접근성 향상
- **SentenceTransformers**: 임베딩 모델 제공
- **Vis.js**: 그래프 시각화 라이브러리

---

*마지막 업데이트: 2025-09-04*