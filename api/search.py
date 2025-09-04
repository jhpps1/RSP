import asyncpg
import redis.asyncio as redis
from typing import List, Optional, Dict, Any
import time
import logging
import json
import hashlib
from models import SearchResponse, Paper, SearchStats
from database import DatabaseManager
from embedder import PaperEmbedder

logger = logging.getLogger(__name__)

class SearchService:
    """검색 서비스 클래스"""
    
    def __init__(self, db_pool: asyncpg.Pool, redis_client: redis.Redis, embedder: PaperEmbedder):
        self.db = DatabaseManager(db_pool)
        self.redis = redis_client
        self.embedder = embedder
        self.cache_ttl = 3600  # 1시간 캐시
    
    def _get_cache_key(self, query: str, limit: int, threshold: float) -> str:
        """캐시 키 생성"""
        key_data = f"search:{query}:{limit}:{threshold}"
        return hashlib.md5(key_data.encode()).hexdigest()
    
    async def search(self, query: str, limit: int = 20, similarity_threshold: float = 0.5) -> SearchResponse:
        """논문 검색"""
        start_time = time.time()
        
        try:
            # 캐시 확인
            cache_key = self._get_cache_key(query, limit, similarity_threshold)
            cached_result = await self.redis.get(cache_key)
            
            if cached_result:
                logger.info(f"Cache hit for query: {query}")
                result_data = json.loads(cached_result)
                result_data["processing_time"] = time.time() - start_time
                return SearchResponse(**result_data)
            
            # 쿼리 임베딩 생성
            logger.info(f"Searching for: {query}")
            query_embedding = await self.embedder.encode_async(query)
            
            # 벡터 검색
            search_results = await self.db.search_papers(
                embedding=query_embedding.tolist(),
                limit=limit,
                threshold=similarity_threshold
            )
            
            # Paper 객체로 변환
            papers = []
            for result in search_results:
                paper = Paper(
                    id=result["id"],
                    openalex_id=result.get("openalex_id"),
                    doi=result.get("doi"),
                    title=result["title"],
                    abstract=result["abstract"],
                    authors=result["authors"] or [],
                    categories=result["categories"] or [],
                    concepts=result.get("concepts") or [],
                    published_date=result["published_date"].isoformat() if result["published_date"] else None,
                    publication_year=result.get("publication_year"),
                    pdf_url=result["pdf_url"],
                    journal_name=result.get("journal_name"),
                    cited_by_count=result.get("cited_by_count"),
                    fwci=result.get("fwci"),
                    citation_percentile=result.get("citation_percentile"),
                    open_access_status=result.get("open_access_status"),
                    paper_source=result.get("paper_source"),
                    similarity=round(result["similarity"], 4),
                    created_at=result["created_at"].isoformat() if result["created_at"] else None
                )
                papers.append(paper)
            
            processing_time = time.time() - start_time
            
            # 응답 생성
            response = SearchResponse(
                papers=papers,
                total=len(papers),
                processing_time=round(processing_time, 4),
                query=query
            )
            
            # 캐시 저장 (처리 시간 제외한 데이터)
            cache_data = response.dict()
            cache_data.pop("processing_time", None)
            await self.redis.setex(cache_key, self.cache_ttl, json.dumps(cache_data))
            
            # 검색 통계 저장
            await self.db.save_search_stats(
                query=query,
                results_count=len(papers),
                search_time_ms=int(processing_time * 1000)
            )
            
            logger.info(f"Search completed: {len(papers)} results in {processing_time:.3f}s")
            return response
            
        except Exception as e:
            logger.error(f"Search failed: {e}")
            raise
    
    async def get_paper_by_id(self, paper_id: str) -> Optional[Paper]:
        """논문 상세 정보 조회"""
        try:
            # 캐시 확인
            cache_key = f"paper:{paper_id}"
            cached_result = await self.redis.get(cache_key)
            
            if cached_result:
                logger.debug(f"Cache hit for paper: {paper_id}")
                return Paper(**json.loads(cached_result))
            
            # DB에서 조회
            result = await self.db.get_paper_by_id(paper_id)
            
            if not result:
                return None
            
            paper = Paper(
                id=result["id"],
                openalex_id=result.get("openalex_id"),
                doi=result.get("doi"),
                title=result["title"],
                abstract=result["abstract"],
                authors=result["authors"] or [],
                categories=result["categories"] or [],
                concepts=result.get("concepts") or [],
                published_date=result["published_date"].isoformat() if result["published_date"] else None,
                publication_year=result.get("publication_year"),
                pdf_url=result["pdf_url"],
                journal_name=result.get("journal_name"),
                cited_by_count=result.get("cited_by_count"),
                fwci=result.get("fwci"),
                citation_percentile=result.get("citation_percentile"),
                open_access_status=result.get("open_access_status"),
                paper_source=result.get("paper_source"),
                created_at=result["created_at"].isoformat() if result["created_at"] else None
            )
            
            # 캐시 저장
            await self.redis.setex(cache_key, self.cache_ttl, paper.json())
            
            return paper
            
        except Exception as e:
            logger.error(f"Failed to get paper {paper_id}: {e}")
            raise
    
    async def find_similar(self, paper_id: str, limit: int = 10) -> SearchResponse:
        """유사한 논문 찾기"""
        start_time = time.time()
        
        try:
            # 캐시 확인
            cache_key = f"similar:{paper_id}:{limit}"
            cached_result = await self.redis.get(cache_key)
            
            if cached_result:
                logger.info(f"Cache hit for similar papers: {paper_id}")
                result_data = json.loads(cached_result)
                result_data["processing_time"] = time.time() - start_time
                return SearchResponse(**result_data)
            
            # 유사한 논문 검색
            search_results = await self.db.get_similar_papers(paper_id, limit)
            
            # Paper 객체로 변환
            papers = []
            for result in search_results:
                paper = Paper(
                    id=result["id"],
                    openalex_id=result.get("openalex_id"),
                    doi=result.get("doi"),
                    title=result["title"],
                    abstract=result["abstract"],
                    authors=result["authors"] or [],
                    categories=result["categories"] or [],
                    concepts=result.get("concepts") or [],
                    published_date=result["published_date"].isoformat() if result["published_date"] else None,
                    publication_year=result.get("publication_year"),
                    pdf_url=result["pdf_url"],
                    journal_name=result.get("journal_name"),
                    cited_by_count=result.get("cited_by_count"),
                    fwci=result.get("fwci"),
                    citation_percentile=result.get("citation_percentile"),
                    open_access_status=result.get("open_access_status"),
                    paper_source=result.get("paper_source"),
                    similarity=round(result["similarity"], 4),
                    created_at=result["created_at"].isoformat() if result["created_at"] else None
                )
                papers.append(paper)
            
            processing_time = time.time() - start_time
            
            # 응답 생성
            response = SearchResponse(
                papers=papers,
                total=len(papers),
                processing_time=round(processing_time, 4),
                query=f"similar to {paper_id}"
            )
            
            # 캐시 저장
            cache_data = response.dict()
            cache_data.pop("processing_time", None)
            await self.redis.setex(cache_key, self.cache_ttl, json.dumps(cache_data))
            
            logger.info(f"Similar search completed: {len(papers)} results in {processing_time:.3f}s")
            return response
            
        except Exception as e:
            logger.error(f"Similar search failed for {paper_id}: {e}")
            raise
    
    async def get_search_stats(self) -> Dict[str, Any]:
        """검색 통계 조회"""
        try:
            # 캐시 확인
            cache_key = "stats:search"
            cached_result = await self.redis.get(cache_key)
            
            if cached_result:
                return json.loads(cached_result)
            
            # DB에서 통계 조회
            stats = await self.db.get_search_stats()
            
            # 모델 정보 추가
            model_info = self.embedder.get_model_info()
            stats["model_info"] = model_info
            
            # 캐시 저장 (5분)
            await self.redis.setex(cache_key, 300, json.dumps(stats))
            
            return stats
            
        except Exception as e:
            logger.error(f"Failed to get search stats: {e}")
            raise
    
    async def search_with_filters(self, query: str = None, filters: dict = None, 
                                limit: int = 20, similarity_threshold: float = 0.5) -> SearchResponse:
        """필터와 함께 검색"""
        start_time = time.time()
        
        try:
            # 쿼리가 있는 경우 임베딩 생성
            query_embedding = None
            if query:
                logger.info(f"Advanced searching for: {query} with filters: {filters}")
                query_embedding = await self.embedder.encode_async(query)
            else:
                logger.info(f"Filter-only search with filters: {filters}")
            
            # 필터 기반 검색
            search_results = await self.db.search_papers_with_filters(
                embedding=query_embedding.tolist() if query_embedding is not None else None,
                filters=filters,
                limit=limit,
                threshold=similarity_threshold
            )
            
            # 결과 변환
            papers = []
            for row in search_results:
                paper_data = dict(row)
                
                # 날짜 처리
                if paper_data.get('published_date'):
                    paper_data['published_date'] = paper_data['published_date'].isoformat()
                if paper_data.get('created_at'):
                    paper_data['created_at'] = paper_data['created_at'].isoformat()
                
                # 빈 배열 처리
                for field in ['authors', 'categories', 'concepts']:
                    if not paper_data.get(field):
                        paper_data[field] = []
                
                papers.append(Paper(**paper_data))
            
            processing_time = time.time() - start_time
            
            # 검색 통계 저장
            await self.db.save_search_stats(
                query=query or "filter_search",
                results_count=len(papers),
                search_time_ms=int(processing_time * 1000)
            )
            
            return SearchResponse(
                papers=papers,
                total=len(papers),
                processing_time=processing_time,
                query=query or "advanced_filter"
            )
            
        except Exception as e:
            logger.error(f"Advanced search failed: {e}")
            raise
    
    async def filter_only_search(self, filters: dict, limit: int = 20) -> SearchResponse:
        """필터만으로 검색 (임베딩 없이)"""
        return await self.search_with_filters(
            query=None,
            filters=filters,
            limit=limit,
            similarity_threshold=0.0  # 임베딩 없을 때는 threshold 무시
        )
    
    async def generate_graph_data(self, papers: List[Paper], similarity_threshold: float = 0.4) -> Dict[str, Any]:
        """논문들 간의 유사도를 계산하여 그래프 데이터 생성"""
        start_time = time.time()
        
        try:
            nodes = []
            edges = []
            
            # 논문 임베딩 수집
            paper_embeddings = {}
            for paper in papers:
                # 데이터베이스에서 해당 논문의 임베딩 가져오기
                db_paper = await self.db.get_paper_by_id(paper.openalex_id or paper.doi)
                if db_paper and 'embedding' in db_paper:
                    paper_embeddings[paper.id] = db_paper['embedding']
            
            # 노드 생성 (논문들)
            for paper in papers:
                # 카테고리 기반 색상 결정
                color = self._get_category_color(paper.categories)
                
                # 노드 크기는 인용수 기반 (로그 스케일)
                import math
                citations = paper.cited_by_count or 0
                size = max(10, min(50, 10 + math.log10(citations + 1) * 8))
                
                node = {
                    "id": paper.id,
                    "label": paper.title[:40] + ("..." if len(paper.title) > 40 else ""),
                    "title": f"<b>{paper.title}</b><br>" +
                            f"저자: {', '.join(paper.authors[:2]) + ('...' if len(paper.authors) > 2 else '')}<br>" +
                            f"인용수: {citations}<br>" +
                            f"연도: {paper.publication_year or 'N/A'}",
                    "size": size,
                    "color": {
                        "background": color,
                        "border": "#2B7CE9",
                        "highlight": {
                            "background": "#D2E5FF",
                            "border": "#2B7CE9"
                        }
                    },
                    "font": {"size": 12, "color": "#343434"},
                    "paper_data": {
                        "openalex_id": paper.openalex_id,
                        "doi": paper.doi,
                        "title": paper.title,
                        "authors": paper.authors,
                        "cited_by_count": citations,
                        "publication_year": paper.publication_year,
                        "categories": paper.categories,
                        "similarity": paper.similarity
                    }
                }
                nodes.append(node)
            
            # 엣지 생성 (논문 간 유사도)
            paper_list = list(papers)
            for i in range(len(paper_list)):
                for j in range(i + 1, len(paper_list)):
                    paper1, paper2 = paper_list[i], paper_list[j]
                    
                    # 두 논문의 임베딩이 모두 있는 경우에만 계산
                    if paper1.id in paper_embeddings and paper2.id in paper_embeddings:
                        embedding1 = paper_embeddings[paper1.id]
                        embedding2 = paper_embeddings[paper2.id]
                        
                        # 코사인 유사도 계산
                        similarity = self._calculate_cosine_similarity(embedding1, embedding2)
                        
                        if similarity >= similarity_threshold:
                            # 엣지 두께는 유사도에 비례
                            width = max(1, int((similarity - similarity_threshold) / (1.0 - similarity_threshold) * 5))
                            
                            edge = {
                                "from": paper1.id,
                                "to": paper2.id,
                                "value": similarity,
                                "title": f"유사도: {similarity:.3f}",
                                "width": width,
                                "color": {
                                    "color": self._get_similarity_color(similarity),
                                    "opacity": 0.6
                                }
                            }
                            edges.append(edge)
            
            processing_time = time.time() - start_time
            
            logger.info(f"Graph data generated: {len(nodes)} nodes, {len(edges)} edges in {processing_time:.3f}s")
            
            return {
                "nodes": nodes,
                "edges": edges,
                "processing_time": processing_time
            }
            
        except Exception as e:
            logger.error(f"Failed to generate graph data: {e}")
            raise
    
    def _calculate_cosine_similarity(self, embedding1, embedding2):
        """두 임베딩 간의 코사인 유사도 계산"""
        import numpy as np
        
        # numpy 배열로 변환
        if isinstance(embedding1, list):
            embedding1 = np.array(embedding1)
        if isinstance(embedding2, list):
            embedding2 = np.array(embedding2)
        
        # 코사인 유사도 계산
        dot_product = np.dot(embedding1, embedding2)
        norm1 = np.linalg.norm(embedding1)
        norm2 = np.linalg.norm(embedding2)
        
        if norm1 == 0 or norm2 == 0:
            return 0.0
        
        similarity = dot_product / (norm1 * norm2)
        return float(similarity)
    
    def _get_category_color(self, categories):
        """카테고리 기반 노드 색상 결정"""
        if not categories:
            return "#97C2FC"
        
        color_map = {
            "cs.AI": "#FF6B6B",      # AI - 빨간색
            "cs.CL": "#4ECDC4",      # 자연어처리 - 청록색  
            "cs.CV": "#45B7D1",      # 컴퓨터비전 - 파란색
            "cs.LG": "#96CEB4",      # 기계학습 - 초록색
            "cs.NE": "#FFEAA7",      # 신경망 - 노란색
            "stat.ML": "#DDA0DD",    # 통계ML - 보라색
        }
        
        # 첫 번째 카테고리 기준으로 색상 결정
        for category in categories:
            if category in color_map:
                return color_map[category]
        
        return "#97C2FC"  # 기본 색상
    
    def _get_similarity_color(self, similarity):
        """유사도 기반 엣지 색상 결정"""
        if similarity >= 0.8:
            return "#FF4757"  # 높은 유사도 - 빨간색
        elif similarity >= 0.6:
            return "#FFA502"  # 중간 유사도 - 주황색
        else:
            return "#57606F"  # 낮은 유사도 - 회색