from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import asyncpg
import redis.asyncio as redis
from typing import Optional
import os
import logging

# 로컬 모듈
from models import (SearchRequest, SearchResponse, Paper, SimilarRequest, 
                   PDFRequest, PDFResponse, FilterRequest)
from database import get_db_pool, get_redis_client
from embedder import PaperEmbedder
from search import SearchService

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 글로벌 객체들
embedder = None
search_service = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    """애플리케이션 시작/종료 시 실행되는 함수"""
    global embedder, search_service
    
    # 시작 시
    logger.info("Starting Paper Search API...")
    
    # 임베딩 모델 초기화
    embedder = PaperEmbedder()
    
    # 검색 서비스 초기화
    db_pool = await get_db_pool()
    redis_client = await get_redis_client()
    search_service = SearchService(db_pool, redis_client, embedder)
    
    logger.info("API ready!")
    
    yield
    
    # 종료 시
    logger.info("Shutting down...")
    if db_pool:
        await db_pool.close()
    if redis_client:
        await redis_client.close()

# FastAPI 앱 생성
app = FastAPI(
    title="Paper Search API",
    description="논문 벡터 검색 API",
    version="1.0.0",
    lifespan=lifespan
)

# CORS 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 개발용, 프로덕션에서는 제한 필요
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def root():
    """API 상태 확인"""
    return {
        "message": "Paper Search API is running!",
        "version": "1.0.0",
        "status": "healthy"
    }

@app.get("/health")
async def health_check():
    """헬스체크 엔드포인트"""
    try:
        # DB 연결 확인
        db_pool = await get_db_pool()
        async with db_pool.acquire() as conn:
            await conn.fetchval("SELECT 1")
        
        # Redis 연결 확인
        redis_client = await get_redis_client()
        await redis_client.ping()
        
        return {"status": "healthy", "database": "ok", "cache": "ok"}
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        raise HTTPException(status_code=503, detail="Service unavailable")

@app.post("/search", response_model=SearchResponse)
async def search_papers(request: SearchRequest):
    """논문 검색 API"""
    try:
        results = await search_service.search(
            query=request.query,
            limit=request.limit,
            similarity_threshold=request.similarity_threshold
        )
        return results
    except Exception as e:
        logger.error(f"Search failed: {e}")
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")

@app.get("/papers/{paper_id}", response_model=Paper)
async def get_paper(paper_id: str):
    """논문 상세 정보"""
    try:
        paper = await search_service.get_paper_by_id(paper_id)
        if not paper:
            raise HTTPException(status_code=404, detail="Paper not found")
        return paper
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get paper failed: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get paper: {str(e)}")

@app.post("/similar", response_model=SearchResponse)
async def find_similar_papers(request: SimilarRequest):
    """유사한 논문 찾기"""
    try:
        results = await search_service.find_similar(
            paper_id=request.paper_id,
            limit=request.limit
        )
        return results
    except Exception as e:
        logger.error(f"Similar search failed: {e}")
        raise HTTPException(status_code=500, detail=f"Similar search failed: {str(e)}")

@app.get("/stats")
async def get_search_stats():
    """검색 통계"""
    try:
        stats = await search_service.get_search_stats()
        return stats
    except Exception as e:
        logger.error(f"Get stats failed: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get stats: {str(e)}")

@app.post("/pdf", response_model=PDFResponse)
async def get_pdf_url(request: PDFRequest):
    """저장된 OpenAlex OA 링크만 돌려준다."""
    try:
        if not request.doi:
            raise HTTPException(status_code=400, detail="DOI is required")

        paper = await search_service.get_paper_by_id(request.doi)
        pdf_url = paper.pdf_url if paper else None
        if pdf_url:
            return PDFResponse(
                doi=request.doi,
                pdf_url=pdf_url,
                available=True,
                source="openalex",
                message="OpenAlex OA link"
            )
        return PDFResponse(
            doi=request.doi,
            pdf_url=None,
            available=False,
            source=None,
            message="OpenAlex OA link is not stored for this paper"
        )
    except Exception as e:
        logger.error(f"PDF request failed: {e}")
        raise HTTPException(status_code=500, detail=f"PDF request failed: {str(e)}")

@app.post("/search/advanced", response_model=SearchResponse)
async def advanced_search(request: FilterRequest):
    """고급 필터 검색"""
    try:
        # 필터 딕셔너리 구성 (모든 논문이 OpenAlex이므로 paper_source 필터는 제거)
        filters = {}
        if request.min_citations is not None:
            filters['min_citations'] = request.min_citations
        if request.max_citations is not None:
            filters['max_citations'] = request.max_citations
        if request.year_from:
            filters['year_from'] = request.year_from
        if request.year_to:
            filters['year_to'] = request.year_to
        if request.journal_name:
            filters['journal_name'] = request.journal_name
        if request.open_access_only:
            filters['open_access_only'] = request.open_access_only
        if request.concepts:
            filters['concepts'] = request.concepts
        
        # 검색 실행
        if request.query:
            # 텍스트 쿼리가 있는 경우 임베딩 기반 검색
            results = await search_service.search_with_filters(
                query=request.query,
                filters=filters,
                limit=request.limit,
                similarity_threshold=request.similarity_threshold
            )
        else:
            # 텍스트 쿼리가 없는 경우 필터만으로 검색
            results = await search_service.filter_only_search(
                filters=filters,
                limit=request.limit
            )
        
        return results
        
    except Exception as e:
        logger.error(f"Advanced search failed: {e}")
        raise HTTPException(status_code=500, detail=f"Advanced search failed: {str(e)}")

@app.get("/papers/{paper_id}/pdf")
async def get_paper_pdf(paper_id: str):
    """논문 PDF URL 제공 (DOI 기반)"""
    try:
        # 논문 정보 조회
        paper = await search_service.get_paper_by_id(paper_id)
        if not paper:
            raise HTTPException(status_code=404, detail="Paper not found")
        
        # Open Access인 경우 OpenAlex 직접 링크 우선 사용
        if paper.pdf_url and paper.open_access_status in ['gold', 'green', 'hybrid', 'bronze']:
            return {
                "pdf_url": paper.pdf_url,
                "source": "openalex_direct",
                "available": True
            }
        
        # DOI 확인
        doi = paper.doi
        if not doi:
            # DOI가 없는 경우
            if paper.pdf_url:
                return {
                    "pdf_url": paper.pdf_url,
                    "source": "openalex_direct",
                    "available": True
                }
            else:
                raise HTTPException(status_code=404, detail="DOI not available for this paper")
        
        raise HTTPException(status_code=404, detail="OpenAlex OA link is not stored for this paper")
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get paper PDF failed: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get PDF: {str(e)}")

@app.post("/graph-data")
async def get_graph_data(request: SearchRequest):
    """논문 그래프 시각화를 위한 노드-엣지 데이터"""
    try:
        # 먼저 검색 수행
        search_results = await search_service.search(
            query=request.query,
            limit=request.limit,
            similarity_threshold=request.similarity_threshold
        )
        
        if not search_results.papers:
            return {
                "nodes": [],
                "edges": [],
                "total": 0,
                "processing_time": search_results.processing_time
            }
        
        # 그래프 데이터 생성
        graph_data = await search_service.generate_graph_data(
            papers=search_results.papers,
            similarity_threshold=0.4  # 그래프용 임계값 (더 관대하게)
        )
        
        return {
            "nodes": graph_data["nodes"],
            "edges": graph_data["edges"],
            "total": len(graph_data["nodes"]),
            "processing_time": search_results.processing_time + graph_data["processing_time"]
        }
        
    except Exception as e:
        logger.error(f"Graph data generation failed: {e}")
        raise HTTPException(status_code=500, detail=f"Graph data generation failed: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)