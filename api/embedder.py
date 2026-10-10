import os
import torch
from sentence_transformers import SentenceTransformer
import numpy as np
from typing import List, Union
import logging
import time
import asyncio
from concurrent.futures import ThreadPoolExecutor

logger = logging.getLogger(__name__)

class PaperEmbedder:
    """논문 임베딩 생성 클래스"""
    
    def __init__(self, model_name: str = None):
        if not model_name:
            model_name = os.getenv("EMBEDDING_MODEL", "all-MiniLM-L6-v2")
        """
        임베딩 모델 초기화
        
        Args:
            model_name: 사용할 모델명 (기본: all-MiniLM-L6-v2, 384차원)
        """
        self.model_name = model_name
        self.model = None
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.thread_pool = ThreadPoolExecutor(max_workers=2)
        
        logger.info(f"Initializing embedder with model: {model_name}")
        logger.info(f"Device: {self.device}")
        
        self._load_model()
    
    def _load_model(self):
        """모델 로드"""
        try:
            start_time = time.time()
            
            self.model = SentenceTransformer(self.model_name)
            self.model.to(self.device)
            
            # 메모리 최적화 (RTX 3050용)
            if self.device == "cuda":
                torch.cuda.empty_cache()
            
            load_time = time.time() - start_time
            logger.info(f"Model loaded successfully in {load_time:.2f} seconds")
            
            # 테스트 인코딩
            test_text = "This is a test sentence."
            test_embedding = self.model.encode([test_text])
            logger.info(f"Model test successful, embedding dimension: {len(test_embedding[0])}")
            
        except Exception as e:
            logger.error(f"Failed to load model: {e}")
            raise
    
    def encode_text(self, text: str) -> np.ndarray:
        """단일 텍스트 임베딩 생성"""
        if not text or not text.strip():
            raise ValueError("Empty text provided")
        
        try:
            start_time = time.time()
            
            # GPU 메모리 정리
            if self.device == "cuda":
                torch.cuda.empty_cache()
            
            embedding = self.model.encode(
                text,
                convert_to_numpy=True,
                normalize_embeddings=True,  # 코사인 유사도 최적화
                device=self.device
            )
            
            processing_time = time.time() - start_time
            logger.debug(f"Text encoded in {processing_time:.3f} seconds")
            
            return embedding
            
        except Exception as e:
            logger.error(f"Failed to encode text: {e}")
            raise
    
    def encode_batch(self, texts: List[str], batch_size: int = 8) -> np.ndarray:
        """배치 텍스트 임베딩 생성"""
        if not texts:
            raise ValueError("Empty text list provided")
        
        # 빈 텍스트 필터링
        valid_texts = [text.strip() for text in texts if text and text.strip()]
        if not valid_texts:
            raise ValueError("No valid texts provided")
        
        try:
            start_time = time.time()
            
            # GPU 메모리 정리
            if self.device == "cuda":
                torch.cuda.empty_cache()
            
            embeddings = self.model.encode(
                valid_texts,
                batch_size=batch_size,
                convert_to_numpy=True,
                normalize_embeddings=True,
                device=self.device,
                show_progress_bar=len(valid_texts) > 10
            )
            
            processing_time = time.time() - start_time
            logger.info(f"Batch of {len(valid_texts)} texts encoded in {processing_time:.2f} seconds")
            
            return embeddings
            
        except Exception as e:
            logger.error(f"Failed to encode batch: {e}")
            raise
    
    async def encode_async(self, text: str) -> np.ndarray:
        """비동기 텍스트 임베딩 생성"""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            self.thread_pool, 
            self.encode_text, 
            text
        )
    
    async def encode_batch_async(self, texts: List[str], batch_size: int = 8) -> np.ndarray:
        """비동기 배치 임베딩 생성"""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            self.thread_pool, 
            self.encode_batch, 
            texts, 
            batch_size
        )
    
    def prepare_paper_text(self, title: str, abstract: str = None) -> str:
        """논문 텍스트 전처리"""
        # 제목과 초록 결합
        text_parts = []
        
        if title and title.strip():
            text_parts.append(title.strip())
        
        if abstract and abstract.strip():
            # 초록이 너무 길면 자르기 (모델 최대 길이 고려)
            abstract_clean = abstract.strip()
            if len(abstract_clean) > 500:  # 대략 500자로 제한
                abstract_clean = abstract_clean[:500] + "..."
            text_parts.append(abstract_clean)
        
        if not text_parts:
            raise ValueError("No valid title or abstract provided")
        
        return " [SEP] ".join(text_parts)
    
    def get_model_info(self) -> dict:
        """모델 정보 반환"""
        return {
            "model_name": self.model_name,
            "device": self.device,
            "embedding_dimension": self.model.get_sentence_embedding_dimension(),
            "max_sequence_length": self.model.max_seq_length
        }

# 전역 임베더 인스턴스
embedder_instance: PaperEmbedder = None

def get_embedder() -> PaperEmbedder:
    """전역 임베더 인스턴스 가져오기"""
    global embedder_instance
    if embedder_instance is None:
        embedder_instance = PaperEmbedder()
    return embedder_instance