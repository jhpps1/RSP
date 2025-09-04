#!/usr/bin/env python3
"""
OpenAlex API를 사용한 논문 데이터 수집
"""

import asyncio
import asyncpg
from pgvector.asyncpg import register_vector
import requests
import time
import json
from datetime import datetime
import logging
from embedder import PaperEmbedder
from database import get_db_pool

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class OpenAlexFetcher:
    """OpenAlex API를 사용한 논문 데이터 수집"""
    
    def __init__(self):
        self.base_url = "https://api.openalex.org/works"
        self.delay = 0.1  # OpenAlex는 rate limit가 없지만 예의상 간격
    
    def fetch_papers_by_keywords(self, keywords, max_results=100, min_citations=10):
        """키워드로 논문 검색"""
        
        # 검색 쿼리 구성
        search_query = " AND ".join([f'"{keyword}"' for keyword in keywords])
        
        params = {
            'search': search_query,
            'filter': f'cited_by_count:>{min_citations},type:article,is_oa:true',
            'sort': 'cited_by_count:desc',
            'per-page': min(max_results, 200),  # OpenAlex 최대 200개
            'cursor': '*'
        }
        
        logger.info(f"Fetching papers with keywords: {keywords}")
        logger.info(f"Search query: {search_query}")
        
        papers = []
        
        try:
            while len(papers) < max_results:
                response = requests.get(self.base_url, params=params)
                response.raise_for_status()
                
                data = response.json()
                
                if not data.get('results'):
                    break
                
                for work in data['results']:
                    paper = self._parse_openalex_work(work)
                    if paper:
                        papers.append(paper)
                
                # 다음 페이지 확인
                if not data.get('meta', {}).get('next_cursor'):
                    break
                    
                params['cursor'] = data['meta']['next_cursor']
                
                if len(papers) >= max_results:
                    break
                    
                time.sleep(self.delay)
            
            logger.info(f"Found {len(papers)} papers")
            return papers[:max_results]
            
        except Exception as e:
            logger.error(f"Failed to fetch papers: {e}")
            return []
    
    def fetch_papers_by_concepts(self, concept_ids, max_results=50, min_citations=5):
        """OpenAlex concept ID로 논문 검색"""
        papers = []
        
        for concept_id in concept_ids:
            logger.info(f"Fetching papers from concept: {concept_id}")
            
            params = {
                'filter': f'concepts.id:{concept_id},cited_by_count:>{min_citations},type:article',
                'sort': 'cited_by_count:desc',
                'per-page': max_results,
            }
            
            try:
                response = requests.get(self.base_url, params=params)
                response.raise_for_status()
                
                data = response.json()
                concept_papers = []
                
                for work in data.get('results', []):
                    paper = self._parse_openalex_work(work)
                    if paper:
                        concept_papers.append(paper)
                
                papers.extend(concept_papers)
                logger.info(f"Added {len(concept_papers)} papers from {concept_id}")
                
                time.sleep(self.delay)
                
            except Exception as e:
                logger.error(f"Failed to fetch papers from {concept_id}: {e}")
                continue
        
        return papers
    
    def fetch_trending_papers(self, days=30, max_results=100):
        """최근 트렌딩 논문 검색"""
        
        # 최근 날짜 계산
        from datetime import datetime, timedelta
        recent_date = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')
        
        params = {
            'filter': f'from_publication_date:{recent_date},type:article,cited_by_count:>5',
            'sort': 'cited_by_count:desc',
            'per-page': max_results
        }
        
        logger.info(f"Fetching trending papers from last {days} days")
        
        try:
            response = requests.get(self.base_url, params=params)
            response.raise_for_status()
            
            data = response.json()
            papers = []
            
            for work in data.get('results', []):
                paper = self._parse_openalex_work(work)
                if paper:
                    papers.append(paper)
            
            logger.info(f"Found {len(papers)} trending papers")
            return papers
            
        except Exception as e:
            logger.error(f"Failed to fetch trending papers: {e}")
            return []
    
    def _parse_openalex_work(self, work):
        """OpenAlex work 객체 파싱"""
        
        try:
            # 기본 정보 추출
            openalex_id = work.get('id', '').replace('https://openalex.org/', '')
            
            # DOI 추출
            doi = work.get('doi')
            if doi and doi.startswith('https://doi.org/'):
                doi = doi.replace('https://doi.org/', '')
            
            # 제목
            title = work.get('title', '').strip()
            if not title:
                return None
            
            # 초록 (OpenAlex는 초록을 제공하지 않을 수 있음)
            abstract = ""
            if work.get('abstract_inverted_index'):
                # inverted index를 텍스트로 복원
                abstract = self._reconstruct_abstract(work['abstract_inverted_index'])
            
            # 저자들
            authors = []
            for authorship in work.get('authorships', []):
                author_name = authorship.get('author', {}).get('display_name')
                if author_name:
                    authors.append(author_name)
            
            # 개념들 (카테고리 대신)
            concepts = []
            categories = []  # OpenAlex의 concepts를 categories로 매핑
            for concept in work.get('concepts', [])[:5]:  # 상위 5개만
                concept_name = concept.get('display_name')
                if concept_name:
                    concepts.append(concept_name)
                    # 간단한 카테고리 매핑
                    if any(term in concept_name.lower() for term in ['computer', 'machine learning', 'artificial intelligence']):
                        categories.append('cs.AI')
                    elif any(term in concept_name.lower() for term in ['language', 'natural language']):
                        categories.append('cs.CL')
            
            # 발행 정보
            publication_date = work.get('publication_date')
            if publication_date:
                try:
                    publication_date = datetime.fromisoformat(publication_date).date()
                except (ValueError, TypeError):
                    publication_date = None
            publication_year = work.get('publication_year')
            
            # 저널 정보
            journal_name = ""
            if work.get('primary_location', {}).get('source'):
                journal_name = work['primary_location']['source'].get('display_name', '')
            
            # 인용 정보
            cited_by_count = work.get('cited_by_count', 0)
            
            # 영향력 지수들
            fwci = None
            if work.get('cited_by_percentile_year', {}).get('min'):
                fwci = work['cited_by_percentile_year']['min'] / 100.0
            
            # Open Access 정보
            open_access_status = work.get('open_access', {}).get('oa_status', 'closed')
            
            # PDF URL - Open Access인 경우
            pdf_url = ""
            if work.get('open_access', {}).get('oa_url'):
                pdf_url = work['open_access']['oa_url']
            elif work.get('primary_location', {}).get('pdf_url'):
                pdf_url = work['primary_location']['pdf_url']
            
            paper = {
                'openalex_id': openalex_id,
                'doi': doi,
                'title': title,
                'abstract': abstract or f"Abstract not available. This paper discusses {title.lower()}.",
                'authors': authors,
                'categories': categories,
                'concepts': concepts,
                'published_date': publication_date,
                'publication_year': publication_year,
                'journal_name': journal_name,
                'cited_by_count': cited_by_count,
                'fwci': fwci,
                'open_access_status': open_access_status,
                'pdf_url': pdf_url,
                'paper_source': 'openalex'
            }
            
            return paper
            
        except Exception as e:
            logger.warning(f"Failed to parse work: {e}")
            return None
    
    def _reconstruct_abstract(self, inverted_index):
        """OpenAlex inverted index에서 초록 복원"""
        if not inverted_index:
            return ""
        
        try:
            # 단어별 위치 정보를 평탄화
            word_positions = []
            for word, positions in inverted_index.items():
                for pos in positions:
                    word_positions.append((pos, word))
            
            # 위치순으로 정렬
            word_positions.sort(key=lambda x: x[0])
            
            # 텍스트 복원
            abstract = " ".join([word for _, word in word_positions])
            return abstract[:1000]  # 길이 제한
            
        except Exception:
            return ""

async def insert_openalex_papers_with_embeddings(papers):
    """OpenAlex 논문 데이터를 DB에 저장하고 임베딩 생성"""
    
    if not papers:
        logger.error("No papers to process")
        return
    
    # 데이터베이스 연결
    db_pool = await get_db_pool()
    
    # 임베딩 모델 초기화
    logger.info("Initializing embedding model...")
    embedder = PaperEmbedder()
    
    try:
        async with db_pool.acquire() as conn:
            await register_vector(conn)
            
            logger.info(f"Processing {len(papers)} OpenAlex papers...")
            
            processed = 0
            failed = 0
            
            for i, paper in enumerate(papers, 1):
                try:
                    logger.info(f"Processing paper {i}/{len(papers)}: {paper['title'][:50]}...")
                    
                    # 중복 확인 (DOI 또는 OpenAlex ID)
                    existing = None
                    if paper.get('doi'):
                        existing = await conn.fetchval(
                            "SELECT id FROM papers WHERE doi = $1", 
                            paper['doi']
                        )
                    
                    if not existing and paper.get('openalex_id'):
                        existing = await conn.fetchval(
                            "SELECT id FROM papers WHERE openalex_id = $1", 
                            paper['openalex_id']
                        )
                    
                    if existing:
                        logger.info(f"  Paper already exists, skipping...")
                        continue
                    
                    # 논문 텍스트 준비
                    paper_text = embedder.prepare_paper_text(
                        paper['title'], 
                        paper['abstract']
                    )
                    
                    # 임베딩 생성
                    start_time = time.time()
                    embedding = await embedder.encode_async(paper_text)
                    embed_time = time.time() - start_time
                    
                    # 데이터베이스에 삽입
                    await conn.execute("""
                        INSERT INTO papers 
                        (openalex_id, doi, title, abstract, authors, categories, concepts,
                         published_date, publication_year, journal_name, cited_by_count,
                         fwci, open_access_status, pdf_url, paper_source, embedding)
                        VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15, $16)
                    """, 
                        paper['openalex_id'],
                        paper['doi'],
                        paper['title'],
                        paper['abstract'],
                        paper['authors'],
                        paper['categories'],
                        paper['concepts'],
                        paper['published_date'],
                        paper['publication_year'],
                        paper['journal_name'],
                        paper['cited_by_count'],
                        paper['fwci'],
                        paper['open_access_status'],
                        paper['pdf_url'],
                        paper['paper_source'],
                        embedding.tolist()
                    )
                    
                    processed += 1
                    logger.info(f"  ✓ Processed in {embed_time:.2f}s")
                    
                    # 진행상황 표시
                    if processed % 10 == 0:
                        logger.info(f"Progress: {processed}/{len(papers)} papers processed")
                    
                except Exception as e:
                    failed += 1
                    logger.error(f"  ✗ Failed to process paper: {e}")
                    continue
            
            logger.info(f"Processing complete: {processed} success, {failed} failed")
            
            # 최종 통계
            total_papers = await conn.fetchval("SELECT COUNT(*) FROM papers")
            openalex_papers = await conn.fetchval("SELECT COUNT(*) FROM papers WHERE paper_source = 'openalex'")
            
            logger.info(f"Database statistics:")
            logger.info(f"  Total papers: {total_papers}")
            logger.info(f"  OpenAlex papers: {openalex_papers}")
            
    except Exception as e:
        logger.error(f"Database operation failed: {e}")
        raise
    
    finally:
        await db_pool.close()

async def main():
    """메인 실행 함수"""
    
    logger.info("=== OpenAlex Paper Fetcher ===")
    
    # OpenAlex 클라이언트 초기화
    fetcher = OpenAlexFetcher()
    
    # 다양한 방법으로 논문 수집
    all_papers = []
    
    # 1. 인기 AI/ML 키워드로 검색 (1200개 목표)
    popular_keywords = [
        ['artificial intelligence', 'machine learning'],
        ['deep learning', 'neural network'],
        ['computer vision', 'image recognition'],
        ['natural language processing', 'NLP'],
        ['reinforcement learning', 'RL'],
        ['generative adversarial network', 'GAN'],
        ['transformer', 'attention'],
        ['BERT', 'language model'],
        ['graph neural network', 'GNN'],
        ['convolutional neural network', 'CNN'],
        ['recurrent neural network', 'RNN'],
        ['transfer learning'],
        ['few-shot learning'],
        ['meta learning'],
        ['federated learning'],
        # 추가 키워드들
        ['autoencoder', 'unsupervised learning'],
        ['support vector machine', 'SVM'],
        ['random forest', 'ensemble learning'],
        ['clustering', 'k-means'],
        ['dimensionality reduction', 'PCA'],
        ['recommendation system', 'collaborative filtering'],
        ['time series', 'forecasting'],
        ['anomaly detection', 'outlier detection'],
        ['speech recognition', 'ASR'],
        ['object detection', 'YOLO'],
        ['semantic segmentation', 'U-Net'],
        ['generative model', 'VAE'],
        ['adversarial training', 'robustness'],
        ['multi-task learning', 'MTL'],
        ['continual learning', 'lifelong learning']
    ]
    
    target_per_keyword = 50  # 키워드당 50개씩 (총 1500개 목표)
    
    for keywords in popular_keywords:
        papers = fetcher.fetch_papers_by_keywords(keywords, max_results=target_per_keyword, min_citations=5)  # 인용 수 기준 낮춤
        all_papers.extend(papers)
        logger.info(f"Collected {len(papers)} papers for keywords: {keywords}")
        time.sleep(fetcher.delay)
    
    # 2. 추가 트렌딩 논문 수집 (최근 180일)
    trending_papers = fetcher.fetch_trending_papers(days=180, max_results=50)
    all_papers.extend(trending_papers)
    logger.info(f"Added {len(trending_papers)} trending papers")
    
    # 중복 제거 (OpenAlex ID 기준)
    unique_papers = {}
    for paper in all_papers:
        key = paper.get('openalex_id') or paper.get('doi') or paper.get('title')
        if key:
            unique_papers[key] = paper
    
    final_papers = list(unique_papers.values())
    logger.info(f"Total unique OpenAlex papers collected: {len(final_papers)}")
    
    # 데이터베이스에 저장 및 임베딩 생성
    await insert_openalex_papers_with_embeddings(final_papers)
    
    logger.info("=== OpenAlex Process Complete ===")

if __name__ == "__main__":
    asyncio.run(main())