from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime, date

class SearchRequest(BaseModel):
    """검색 요청 모델"""
    query: str = Field(..., min_length=1, max_length=1000, description="검색 쿼리")
    limit: int = Field(default=20, ge=1, le=100, description="결과 개수 제한")
    similarity_threshold: float = Field(default=0.5, ge=0.0, le=1.0, description="유사도 임계값")
    
    class Config:
        json_schema_extra = {
            "example": {
                "query": "transformer attention mechanism",
                "limit": 20,
                "similarity_threshold": 0.7
            }
        }

class Paper(BaseModel):
    """논문 모델"""
    id: int
    openalex_id: Optional[str] = None
    doi: Optional[str] = None
    title: str
    abstract: Optional[str] = None
    authors: List[str] = []
    categories: List[str] = []
    concepts: List[str] = []
    published_date: Optional[str] = None
    publication_year: Optional[int] = None
    pdf_url: Optional[str] = None
    journal_name: Optional[str] = None
    cited_by_count: Optional[int] = None
    fwci: Optional[float] = None
    citation_percentile: Optional[float] = None
    open_access_status: Optional[str] = None
    paper_source: Optional[str] = None
    similarity: Optional[float] = None
    created_at: Optional[str] = None
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat() if v else None,
            date: lambda v: v.isoformat() if v else None
        }
        json_schema_extra = {
            "example": {
                "id": 1,
                "openalex_id": "W2964118117",
                "doi": "10.1038/nature14539",
                "title": "Attention Is All You Need",
                "abstract": "The dominant sequence transduction models are based on...",
                "authors": ["Ashish Vaswani", "Noam Shazeer"],
                "categories": ["cs.CL", "cs.AI"],
                "concepts": ["Machine learning", "Deep learning", "Attention mechanism"],
                "published_date": "2017-06-12",
                "publication_year": 2017,
                "pdf_url": "https://arxiv.org/abs/1706.03762",
                "journal_name": "Neural Information Processing Systems",
                "cited_by_count": 15420,
                "fwci": 8.7,
                "citation_percentile": 99.8,
                "open_access_status": "gold",
                "paper_source": "openalex",
                "similarity": 0.92
            }
        }

class SearchResponse(BaseModel):
    """검색 응답 모델"""
    papers: List[Paper]
    total: int
    processing_time: float = Field(description="처리 시간(초)")
    query: str
    
    class Config:
        json_schema_extra = {
            "example": {
                "papers": [
                    {
                        "id": 1,
                        "title": "Attention Is All You Need",
                        "similarity": 0.92
                    }
                ],
                "total": 1,
                "processing_time": 0.23,
                "query": "transformer attention"
            }
        }

class SimilarRequest(BaseModel):
    """유사 논문 검색 요청"""
    paper_id: str = Field(..., description="기준 논문 ID (openalex_id 또는 doi)")
    limit: int = Field(default=10, ge=1, le=50, description="결과 개수")
    
    class Config:
        json_schema_extra = {
            "example": {
                "paper_id": "1706.03762",
                "limit": 10
            }
        }

class EmbeddingResponse(BaseModel):
    """임베딩 응답 모델"""
    embedding: List[float]
    dimension: int
    model: str
    processing_time: float

class SearchStats(BaseModel):
    """검색 통계 모델"""
    total_papers: int
    total_searches: int
    avg_search_time: float
    popular_queries: List[Dict[str, Any]]
    recent_searches: List[Dict[str, Any]]

class PDFRequest(BaseModel):
    """PDF 요청 모델"""
    doi: str = Field(..., description="논문의 DOI")
    
    class Config:
        json_schema_extra = {
            "example": {
                "doi": "10.1038/nature14539"
            }
        }

class PDFResponse(BaseModel):
    """PDF 응답 모델"""
    doi: str
    pdf_url: Optional[str] = None
    scihub_url: Optional[str] = None
    available: bool
    source: Optional[str] = None
    message: Optional[str] = None

class FilterRequest(BaseModel):
    """고급 필터 검색 요청"""
    query: Optional[str] = None
    paper_source: Optional[str] = Field(None, description="논문 소스 (항상 'openalex')")
    min_citations: Optional[int] = Field(None, ge=0, description="최소 인용수")
    max_citations: Optional[int] = Field(None, ge=0, description="최대 인용수")
    year_from: Optional[int] = Field(None, ge=1900, le=2030, description="시작 연도")
    year_to: Optional[int] = Field(None, ge=1900, le=2030, description="끝 연도")
    journal_name: Optional[str] = Field(None, description="저널명")
    open_access_only: Optional[bool] = Field(False, description="오픈 액세스만")
    concepts: Optional[List[str]] = Field(None, description="OpenAlex 개념 필터")
    limit: int = Field(default=20, ge=1, le=100, description="결과 개수 제한")
    similarity_threshold: float = Field(default=0.5, ge=0.0, le=1.0, description="유사도 임계값")
    
    class Config:
        json_schema_extra = {
            "example": {
                "query": "machine learning",
                "min_citations": 100,
                "year_from": 2020,
                "open_access_only": True,
                "concepts": ["Machine learning", "Deep learning"],
                "limit": 20
            }
        }