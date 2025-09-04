#!/usr/bin/env python3
"""
Sci-Hub 클라이언트 - DOI를 통한 PDF 원문 제공
"""

import requests
import re
import logging
from typing import Optional, Dict
from urllib.parse import quote
import time

logger = logging.getLogger(__name__)

class SciHubClient:
    """Sci-Hub를 통한 논문 원문 접근 클라이언트"""
    
    def __init__(self):
        # 다양한 Sci-Hub 미러 도메인들 (2024년 기준)
        self.mirrors = [
            "https://sci-hub.se",
            "https://sci-hub.st", 
            "https://sci-hub.ru",
            "https://sci-hub.ren",
            "https://sci-hub.wf",
            "https://sci-hub.tf",
            "https://sci-hub.ee",
            "https://sci-hub.mksa.top"
        ]
        
        self.current_mirror = 0
        self.delay = 1.0  # 요청 간 대기시간
        
        # HTTP 세션 설정
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive'
        })
    
    def get_pdf_url(self, doi: str, max_retries: int = 3) -> Optional[Dict[str, str]]:
        """DOI를 통해 Sci-Hub에서 PDF URL 획득"""
        
        if not doi:
            return None
        
        # DOI 정리
        clean_doi = doi.strip()
        if clean_doi.startswith('https://doi.org/'):
            clean_doi = clean_doi.replace('https://doi.org/', '')
        
        logger.info(f"Fetching PDF URL for DOI: {clean_doi}")
        
        for attempt in range(max_retries):
            tried_mirrors = set()  # 시도한 미러 추적
            
            for mirror_attempt in range(len(self.mirrors)):
                try:
                    # 현재 미러 사용
                    mirror = self.mirrors[self.current_mirror]
                    
                    # 이미 시도한 미러는 건너뛰기
                    if mirror in tried_mirrors:
                        self._rotate_mirror()
                        continue
                        
                    tried_mirrors.add(mirror)
                    url = f"{mirror}/{quote(clean_doi)}"
                    
                    logger.debug(f"Trying mirror {mirror} (attempt {attempt + 1}/{max_retries}, mirror {mirror_attempt + 1}/{len(self.mirrors)})")
                    
                    response = self.session.get(url, timeout=15)  # 타임아웃 증가
                    
                    if response.status_code == 200:
                        pdf_info = self._extract_pdf_info(response.text, mirror)
                        if pdf_info:
                            logger.info(f"✓ PDF found for {clean_doi} via {mirror}")
                            return pdf_info
                        else:
                            logger.debug(f"PDF info not found in response from {mirror}")
                    
                    # 다양한 HTTP 에러 상태 처리
                    elif response.status_code in [403, 404, 429, 503]:
                        logger.debug(f"Mirror {mirror} returned {response.status_code}")
                        self._rotate_mirror()
                        
                    else:
                        logger.warning(f"Unexpected status code {response.status_code} from {mirror}")
                        self._rotate_mirror()
                        
                except requests.exceptions.Timeout:
                    logger.debug(f"Timeout for mirror {self.mirrors[self.current_mirror]}")
                    self._rotate_mirror()
                    
                except requests.exceptions.ConnectionError:
                    logger.debug(f"Connection error for mirror {self.mirrors[self.current_mirror]}")
                    self._rotate_mirror()
                    
                except requests.exceptions.RequestException as e:
                    logger.debug(f"Request failed for mirror {self.mirrors[self.current_mirror]}: {e}")
                    self._rotate_mirror()
                
                # 다음 미러 시도 전 잠시 대기
                if mirror_attempt < len(self.mirrors) - 1:
                    time.sleep(0.5)
                    
            # 모든 미러 시도 후 대기
            if attempt < max_retries - 1:
                time.sleep(self.delay)
        
        logger.warning(f"Failed to get PDF for DOI: {clean_doi}")
        return None
    
    def _extract_pdf_info(self, html_content: str, base_mirror: str) -> Optional[Dict[str, str]]:
        """HTML에서 PDF 정보 추출"""
        
        try:
            # Sci-Hub 페이지에서 PDF URL 패턴들 검색
            pdf_patterns = [
                r'<iframe[^>]+src=["\']([^"\']+\.pdf[^"\']*)["\']',  # iframe 내 PDF
                r'<embed[^>]+src=["\']([^"\']+\.pdf[^"\']*)["\']',   # embed 태그
                r'href=["\']([^"\']*\.pdf[^"\']*)["\']',             # 일반 링크
                r'location\.href\s*=\s*["\']([^"\']+\.pdf[^"\']*)["\']'  # JavaScript 리다이렉트
            ]
            
            for pattern in pdf_patterns:
                matches = re.findall(pattern, html_content, re.IGNORECASE)
                for match in matches:
                    pdf_url = match.strip()
                    
                    # 상대 URL을 절대 URL로 변환
                    if pdf_url.startswith('//'):
                        pdf_url = 'https:' + pdf_url
                    elif pdf_url.startswith('/'):
                        pdf_url = base_mirror + pdf_url
                    elif not pdf_url.startswith('http'):
                        continue
                    
                    # PDF URL 검증
                    if self._validate_pdf_url(pdf_url):
                        return {
                            'pdf_url': pdf_url,
                            'source': 'scihub',
                            'mirror': base_mirror
                        }
            
            # 메타데이터에서 제목 추출 (선택사항)
            title_match = re.search(r'<title>([^<]+)</title>', html_content, re.IGNORECASE)
            title = title_match.group(1).strip() if title_match else ""
            
            if "sci-hub" not in title.lower():  # 실제 논문 제목인 경우
                logger.debug(f"Found paper title: {title}")
            
            return None
            
        except Exception as e:
            logger.debug(f"Failed to extract PDF info: {e}")
            return None
    
    def _validate_pdf_url(self, url: str) -> bool:
        """PDF URL이 유효한지 간단히 검증"""
        
        try:
            # HEAD 요청으로 빠른 검증
            response = self.session.head(url, timeout=5)
            
            # Content-Type 확인
            content_type = response.headers.get('Content-Type', '').lower()
            if 'pdf' in content_type:
                return True
            
            # URL 패턴으로도 검증
            if url.endswith('.pdf') or 'pdf' in url.lower():
                return True
                
            return False
            
        except Exception:
            # 검증 실패시에도 URL이 PDF 확장자를 가지면 허용
            return url.lower().endswith('.pdf')
    
    def _rotate_mirror(self):
        """다음 미러로 변경"""
        self.current_mirror = (self.current_mirror + 1) % len(self.mirrors)
        logger.debug(f"Rotated to mirror: {self.mirrors[self.current_mirror]}")
    
    def download_pdf(self, pdf_url: str, output_path: str) -> bool:
        """PDF 파일 다운로드 (필요시 사용)"""
        
        try:
            logger.info(f"Downloading PDF from: {pdf_url}")
            
            response = self.session.get(pdf_url, timeout=30)
            response.raise_for_status()
            
            with open(output_path, 'wb') as f:
                f.write(response.content)
            
            logger.info(f"✓ PDF downloaded to: {output_path}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to download PDF: {e}")
            return False
    
    def get_multiple_pdfs(self, dois: list) -> Dict[str, Optional[Dict]]:
        """여러 DOI에 대해 일괄 PDF URL 획득"""
        
        results = {}
        
        for doi in dois:
            pdf_info = self.get_pdf_url(doi)
            results[doi] = pdf_info
            
            # 요청 간 대기
            time.sleep(self.delay)
        
        return results

# 유틸리티 함수들
def create_scihub_url(doi: str) -> str:
    """DOI로부터 Sci-Hub URL 생성"""
    if not doi:
        return ""
    
    clean_doi = doi.strip()
    if clean_doi.startswith('https://doi.org/'):
        clean_doi = clean_doi.replace('https://doi.org/', '')
    
    # 가장 안정적인 도메인 사용
    return f"https://sci-hub.se/{quote(clean_doi)}"

def extract_doi_from_url(url: str) -> Optional[str]:
    """URL에서 DOI 추출"""
    
    patterns = [
        r'doi\.org/(.+)$',
        r'/([10]\.\d{4,}[^\s]+)$'  # DOI 패턴
    ]
    
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    
    return None

# 테스트 함수
async def test_scihub_client():
    """Sci-Hub 클라이언트 테스트"""
    
    client = SciHubClient()
    
    # 테스트 DOI들 (유명한 논문들)
    test_dois = [
        "10.1038/nature14539",  # Deep learning paper
        "10.1126/science.aaa8415",  # AlphaGo paper
        "10.1038/nature16961"   # AlphaGo Nature paper
    ]
    
    logger.info("=== Testing Sci-Hub Client ===")
    
    for doi in test_dois:
        logger.info(f"\nTesting DOI: {doi}")
        pdf_info = client.get_pdf_url(doi)
        
        if pdf_info:
            logger.info(f"✓ Success: {pdf_info['pdf_url']}")
        else:
            logger.info("✗ Failed to get PDF")
    
    logger.info("=== Test Complete ===")

if __name__ == "__main__":
    import asyncio
    logging.basicConfig(level=logging.INFO)
    asyncio.run(test_scihub_client())