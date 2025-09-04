import asyncpg
import redis.asyncio as redis
from pgvector.asyncpg import register_vector
import os
from typing import Optional
import logging

logger = logging.getLogger(__name__)

# 전역 연결 풀
db_pool: Optional[asyncpg.Pool] = None
redis_client: Optional[redis.Redis] = None

async def get_db_pool() -> asyncpg.Pool:
    """PostgreSQL 연결 풀 가져오기"""
    global db_pool
    
    if db_pool is None:
        database_url = os.getenv("DATABASE_URL", "postgresql://admin:password@postgres:5432/paperdb")
        
        try:
            db_pool = await asyncpg.create_pool(
                database_url,
                min_size=2,
                max_size=10,
                command_timeout=60
            )
            
            # pgvector 확장 등록
            async with db_pool.acquire() as conn:
                await register_vector(conn)
                # 연결 테스트
                await conn.fetchval("SELECT 1")
                
            logger.info("Database pool created successfully")
            
        except Exception as e:
            logger.error(f"Failed to create database pool: {e}")
            raise
    
    return db_pool

async def get_redis_client() -> redis.Redis:
    """Redis 클라이언트 가져오기"""
    global redis_client
    
    if redis_client is None:
        redis_url = os.getenv("REDIS_URL", "redis://redis:6379")
        
        try:
            redis_client = redis.from_url(
                redis_url,
                encoding="utf-8",
                decode_responses=True,
                socket_connect_timeout=5,
                socket_timeout=5
            )
            
            # 연결 테스트
            await redis_client.ping()
            logger.info("Redis client created successfully")
            
        except Exception as e:
            logger.error(f"Failed to create Redis client: {e}")
            raise
    
    return redis_client

class DatabaseManager:
    """데이터베이스 작업 관리자"""
    
    def __init__(self, db_pool: asyncpg.Pool):
        self.db_pool = db_pool
    
    async def get_papers_count(self) -> int:
        """전체 논문 수 조회"""
        async with self.db_pool.acquire() as conn:
            return await conn.fetchval("SELECT COUNT(*) FROM papers")
    
    async def get_paper_by_id(self, paper_id: str) -> Optional[dict]:
        """ID로 논문 조회 (openalex_id 또는 doi)"""
        async with self.db_pool.acquire() as conn:
            await register_vector(conn)
            
            result = await conn.fetchrow("""
                SELECT id, openalex_id, doi, title, abstract, authors, 
                       categories, concepts, published_date, publication_year,
                       pdf_url, journal_name, cited_by_count, fwci, 
                       citation_percentile, open_access_status, paper_source, created_at
                FROM papers 
                WHERE openalex_id = $1 OR doi = $1
            """, paper_id)
            
            return dict(result) if result else None
    
    async def search_papers_with_filters(self, embedding: list = None, filters: dict = None, 
                                       limit: int = 20, threshold: float = 0.5) -> list:
        """필터와 함께 논문 검색"""
        async with self.db_pool.acquire() as conn:
            await register_vector(conn)
            
            # 기본 쿼리
            base_query = """
                SELECT id, openalex_id, doi, title, abstract, authors, 
                       categories, concepts, published_date, publication_year,
                       pdf_url, journal_name, cited_by_count, fwci, 
                       citation_percentile, open_access_status, paper_source, created_at
            """
            
            where_clauses = []
            params = []
            param_count = 0
            
            # 임베딩 기반 검색
            if embedding:
                base_query += ", 1 - (embedding <=> $1) as similarity"
                where_clauses.append("embedding IS NOT NULL")
                where_clauses.append(f"1 - (embedding <=> $1) > ${param_count + 2}")
                params.extend([embedding, threshold])
                param_count += 2
            
            base_query += " FROM papers"
            
            # 필터 적용
            if filters:
                if filters.get('paper_source'):
                    param_count += 1
                    where_clauses.append(f"paper_source = ${param_count}")
                    params.append(filters['paper_source'])
                
                if filters.get('min_citations') is not None:
                    param_count += 1
                    where_clauses.append(f"cited_by_count >= ${param_count}")
                    params.append(filters['min_citations'])
                
                if filters.get('max_citations') is not None:
                    param_count += 1
                    where_clauses.append(f"cited_by_count <= ${param_count}")
                    params.append(filters['max_citations'])
                
                if filters.get('year_from'):
                    param_count += 1
                    where_clauses.append(f"publication_year >= ${param_count}")
                    params.append(filters['year_from'])
                
                if filters.get('year_to'):
                    param_count += 1
                    where_clauses.append(f"publication_year <= ${param_count}")
                    params.append(filters['year_to'])
                
                if filters.get('journal_name'):
                    param_count += 1
                    where_clauses.append(f"journal_name ILIKE ${param_count}")
                    params.append(f"%{filters['journal_name']}%")
                
                if filters.get('open_access_only'):
                    where_clauses.append("open_access_status IN ('gold', 'green', 'hybrid')")
                
                if filters.get('concepts'):
                    param_count += 1
                    where_clauses.append(f"concepts && ${param_count}")
                    params.append(filters['concepts'])
            
            # WHERE 절 구성
            if where_clauses:
                base_query += " WHERE " + " AND ".join(where_clauses)
            
            # 정렬 및 제한
            if embedding:
                base_query += " ORDER BY embedding <=> $1"
            else:
                base_query += " ORDER BY cited_by_count DESC NULLS LAST, publication_year DESC NULLS LAST"
            
            base_query += f" LIMIT {limit}"
            
            results = await conn.fetch(base_query, *params)
            return [dict(row) for row in results]
    
    async def get_paper_by_doi(self, doi: str) -> Optional[dict]:
        """DOI로 논문 조회"""
        async with self.db_pool.acquire() as conn:
            result = await conn.fetchrow("""
                SELECT id, openalex_id, doi, title, abstract, authors, 
                       categories, concepts, published_date, publication_year,
                       pdf_url, journal_name, cited_by_count, fwci, 
                       citation_percentile, open_access_status, paper_source, created_at
                FROM papers 
                WHERE doi = $1
            """, doi)
    
    async def search_papers(self, embedding: list, limit: int = 20, threshold: float = 0.5) -> list:
        """벡터 검색"""
        async with self.db_pool.acquire() as conn:
            await register_vector(conn)
            
            results = await conn.fetch("""
                SELECT id, openalex_id, doi, title, abstract, authors, 
                       categories, concepts, published_date, publication_year,
                       pdf_url, journal_name, cited_by_count, fwci, 
                       citation_percentile, open_access_status, paper_source, created_at,
                       1 - (embedding <=> $1) as similarity
                FROM papers
                WHERE embedding IS NOT NULL
                  AND 1 - (embedding <=> $1) > $2
                ORDER BY embedding <=> $1
                LIMIT $3
            """, embedding, threshold, limit)
            
            return [dict(row) for row in results]
    
    async def get_similar_papers(self, paper_id: str, limit: int = 10) -> list:
        """유사한 논문 검색"""
        async with self.db_pool.acquire() as conn:
            await register_vector(conn)
            
            # 먼저 기준 논문의 임베딩과 ID 가져오기
            paper_info = await conn.fetchrow("""
                SELECT id, embedding FROM papers 
                WHERE openalex_id = $1 OR doi = $1
            """, paper_id)
            
            if not paper_info or paper_info['embedding'] is None:
                return []
            
            # 유사한 논문 검색 (자기 자신 제외)
            results = await conn.fetch("""
                SELECT id, openalex_id, doi, title, abstract, authors, 
                       categories, concepts, published_date, publication_year,
                       pdf_url, journal_name, cited_by_count, fwci, 
                       citation_percentile, open_access_status, paper_source, created_at,
                       1 - (embedding <=> $1) as similarity
                FROM papers
                WHERE id != $2 AND embedding IS NOT NULL
                ORDER BY embedding <=> $1
                LIMIT $3
            """, paper_info['embedding'], paper_info['id'], limit)
            
            return [dict(row) for row in results]
    
    async def save_search_stats(self, query: str, results_count: int, search_time_ms: int):
        """검색 통계 저장"""
        async with self.db_pool.acquire() as conn:
            await conn.execute("""
                INSERT INTO search_stats (query, results_count, search_time_ms)
                VALUES ($1, $2, $3)
            """, query, results_count, search_time_ms)
    
    async def get_search_stats(self) -> dict:
        """검색 통계 조회"""
        try:
            async with self.db_pool.acquire() as conn:
                # 전체 통계 - 명시적 타입 변환
                try:
                    total_searches = await conn.fetchval("SELECT COUNT(*)::int FROM search_stats")
                    total_searches = int(total_searches) if total_searches else 0
                except Exception:
                    total_searches = 0
                
                try:
                    avg_time = await conn.fetchval("SELECT COALESCE(AVG(search_time_ms), 0)::float FROM search_stats")
                    avg_time = float(avg_time) if avg_time else 0.0
                except Exception:
                    avg_time = 0.0
                
                try:
                    total_papers = await conn.fetchval("SELECT COUNT(*)::int FROM papers WHERE embedding IS NOT NULL")
                    total_papers = int(total_papers) if total_papers else 0
                except Exception:
                    total_papers = 0
                
                # 인기 검색어 - 안전한 처리
                popular_list = []
                try:
                    popular_queries = await conn.fetch("""
                        SELECT 
                            query, 
                            COUNT(*)::int as count, 
                            COALESCE(AVG(search_time_ms), 0)::float as avg_time
                        FROM search_stats
                        WHERE created_at > NOW() - INTERVAL '7 days'
                        GROUP BY query
                        ORDER BY count DESC
                        LIMIT 10
                    """)
                    
                    for row in popular_queries:
                        popular_list.append({
                            "query": str(row["query"]) if row["query"] else "",
                            "count": int(row["count"]) if row["count"] else 0,
                            "avg_time": float(row["avg_time"]) if row["avg_time"] else 0.0
                        })
                except Exception as e:
                    logger.warning(f"Failed to get popular queries: {e}")
                
                # 최근 검색 - 안전한 처리
                recent_list = []
                try:
                    recent_searches = await conn.fetch("""
                        SELECT 
                            query, 
                            results_count::int, 
                            search_time_ms::int, 
                            created_at
                        FROM search_stats
                        ORDER BY created_at DESC
                        LIMIT 20
                    """)
                    
                    for row in recent_searches:
                        recent_list.append({
                            "query": str(row["query"]) if row["query"] else "",
                            "results_count": int(row["results_count"]) if row["results_count"] else 0,
                            "search_time_ms": int(row["search_time_ms"]) if row["search_time_ms"] else 0,
                            "created_at": row["created_at"].isoformat() if row["created_at"] else None
                        })
                except Exception as e:
                    logger.warning(f"Failed to get recent searches: {e}")
                
                return {
                    "total_papers": total_papers,
                    "total_searches": total_searches,
                    "avg_search_time": avg_time,
                    "popular_queries": popular_list,
                    "recent_searches": recent_list
                }
                
        except Exception as e:
            logger.error(f"Failed to get search stats: {e}")
            # 오류 발생 시 기본값 반환
            return {
                "total_papers": 0,
                "total_searches": 0,
                "avg_search_time": 0.0,
                "popular_queries": [],
                "recent_searches": []
            }