"""
청킹 전략 모듈
Semantic, Hybrid, Lexical 청킹 구현
"""

import logging
from typing import List, Dict, Optional
from enum import Enum
import numpy as np

try:
    from langchain.text_splitter import (
        RecursiveCharacterTextSplitter,
        TokenTextSplitter,
        CharacterTextSplitter,
        SentenceTransformersTokenTextSplitter
    )
    LANGCHAIN_AVAILABLE = True
except ImportError:
    LANGCHAIN_AVAILABLE = False

try:
    from sentence_transformers import SentenceTransformer
    SENTENCE_TRANSFORMERS_AVAILABLE = True
except ImportError:
    SENTENCE_TRANSFORMERS_AVAILABLE = False

from open_webui.env import SRC_LOG_LEVELS

log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS.get("RAG", "INFO"))


class ChunkingStrategy(str, Enum):
    """청킹 전략"""
    SEMANTIC = "semantic"
    HYBRID = "hybrid"
    LEXICAL = "lexical"


class ChunkingResult:
    """청킹 결과"""
    def __init__(self, chunks: List[str], metadatas: List[Dict]):
        self.chunks = chunks
        self.metadatas = metadatas


class SemanticChunker:
    """Semantic 청킹: 의미 기반 분할"""
    
    def __init__(
        self,
        chunk_size: int = 1000,
        chunk_overlap: int = 200,
        similarity_threshold: float = 0.7,
        embedding_model: Optional[str] = None
    ):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.similarity_threshold = similarity_threshold
        
        # 임베딩 모델 로드
        if embedding_model is None:
            embedding_model = "sentence-transformers/all-MiniLM-L6-v2"
        
        self.embedding_model_name = embedding_model
        
        if SENTENCE_TRANSFORMERS_AVAILABLE:
            try:
                self.embedding_model = SentenceTransformer(embedding_model)
                log.info(f"Loaded embedding model: {embedding_model}")
            except Exception as e:
                log.warning(f"Failed to load embedding model {embedding_model}: {e}")
                self.embedding_model = None
        else:
            self.embedding_model = None
            log.warning("sentence-transformers not available, falling back to lexical chunking")
    
    def chunk(self, text: str, metadata: Optional[Dict] = None) -> ChunkingResult:
        """
        텍스트를 의미 기반으로 청킹
        
        Args:
            text: 청킹할 텍스트
            metadata: 원본 메타데이터
            
        Returns:
            ChunkingResult: 청킹된 텍스트와 메타데이터
        """
        if self.embedding_model is None:
            # 폴백: lexical 청킹 사용
            lexical_chunker = LexicalChunker(
                chunk_size=self.chunk_size,
                chunk_overlap=self.chunk_overlap
            )
            return lexical_chunker.chunk(text, metadata)
        
        # 문장 단위로 분할
        sentences = self._split_into_sentences(text)
        
        if len(sentences) == 0:
            return ChunkingResult(chunks=[], metadatas=[])
        
        # 문장 임베딩 생성
        try:
            sentence_embeddings = self.embedding_model.encode(sentences, show_progress_bar=False)
        except Exception as e:
            log.error(f"Error generating embeddings: {e}")
            # 폴백: lexical 청킹 사용
            lexical_chunker = LexicalChunker(
                chunk_size=self.chunk_size,
                chunk_overlap=self.chunk_overlap
            )
            return lexical_chunker.chunk(text, metadata)
        
        # 유사도 기반으로 청킹
        chunks = []
        metadatas = []
        current_chunk = []
        current_chunk_embeddings = []
        
        for idx, (sentence, embedding) in enumerate(zip(sentences, sentence_embeddings)):
            if len(current_chunk) == 0:
                # 첫 문장 추가
                current_chunk.append(sentence)
                current_chunk_embeddings.append(embedding)
            else:
                # 현재 청크의 평균 임베딩 계산
                avg_embedding = np.mean(current_chunk_embeddings, axis=0)
                
                # 새 문장과의 유사도 계산
                similarity = np.dot(avg_embedding, embedding) / (
                    np.linalg.norm(avg_embedding) * np.linalg.norm(embedding)
                )
                
                # 유사도가 임계값 이상이고 청크 크기가 제한 내이면 추가
                if similarity >= self.similarity_threshold and len(" ".join(current_chunk)) + len(sentence) < self.chunk_size:
                    current_chunk.append(sentence)
                    current_chunk_embeddings.append(embedding)
                else:
                    # 현재 청크 저장
                    chunk_text = " ".join(current_chunk)
                    if chunk_text.strip():
                        chunks.append(chunk_text)
                        chunk_metadata = (metadata or {}).copy()
                        chunk_metadata.update({
                            "chunk_type": "semantic",
                            "chunk_idx": len(chunks) - 1,
                            "sentence_count": len(current_chunk)
                        })
                        metadatas.append(chunk_metadata)
                    
                    # 새 청크 시작 (오버랩 포함)
                    if self.chunk_overlap > 0 and len(current_chunk) > 0:
                        # 마지막 몇 문장을 오버랩으로 유지
                        overlap_sentences = current_chunk[-min(len(current_chunk), 2):]
                        overlap_embeddings = current_chunk_embeddings[-min(len(current_chunk_embeddings), 2):]
                        current_chunk = overlap_sentences + [sentence]
                        current_chunk_embeddings = overlap_embeddings + [embedding]
                    else:
                        current_chunk = [sentence]
                        current_chunk_embeddings = [embedding]
        
        # 마지막 청크 저장
        if current_chunk:
            chunk_text = " ".join(current_chunk)
            if chunk_text.strip():
                chunks.append(chunk_text)
                chunk_metadata = (metadata or {}).copy()
                chunk_metadata.update({
                    "chunk_type": "semantic",
                    "chunk_idx": len(chunks) - 1,
                    "sentence_count": len(current_chunk)
                })
                metadatas.append(chunk_metadata)
        
        return ChunkingResult(chunks=chunks, metadatas=metadatas)
    
    def _split_into_sentences(self, text: str) -> List[str]:
        """텍스트를 문장 단위로 분할"""
        import re
        # 간단한 문장 분할 (개선 가능)
        sentences = re.split(r'[.!?]\s+', text)
        return [s.strip() for s in sentences if s.strip()]


class HybridChunker:
    """Hybrid 청킹: 의미 + 구조 기반 분할"""
    
    def __init__(
        self,
        chunk_size: int = 800,
        chunk_overlap: int = 150,
        semantic_weight: float = 0.6,
        lexical_weight: float = 0.4,
        embedding_model: Optional[str] = None
    ):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.semantic_weight = semantic_weight
        self.lexical_weight = lexical_weight
        self.semantic_chunker = SemanticChunker(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            embedding_model=embedding_model
        )
        self.lexical_chunker = LexicalChunker(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap
        )
    
    def chunk(self, text: str, metadata: Optional[Dict] = None) -> ChunkingResult:
        """
        Hybrid 청킹: Semantic과 Lexical 결과를 결합
        
        Args:
            text: 청킹할 텍스트
            metadata: 원본 메타데이터
            
        Returns:
            ChunkingResult: 청킹된 텍스트와 메타데이터
        """
        # Semantic 청킹
        semantic_result = self.semantic_chunker.chunk(text, metadata)
        
        # Lexical 청킹
        lexical_result = self.lexical_chunker.chunk(text, metadata)
        
        # 결과 병합 (가중치 적용)
        # 간단한 구현: semantic 결과를 우선하고, lexical 결과로 보완
        chunks = []
        metadatas = []
        
        # Semantic 청크 사용
        for idx, (chunk, meta) in enumerate(zip(semantic_result.chunks, semantic_result.metadatas)):
            chunks.append(chunk)
            meta = meta.copy()
            meta.update({
                "chunk_type": "hybrid",
                "chunk_idx": idx,
                "strategy": "semantic"
            })
            metadatas.append(meta)
        
        # Lexical 청크로 보완 (중복 제거)
        lexical_chunks_set = set(semantic_result.chunks)
        for idx, (chunk, meta) in enumerate(zip(lexical_result.chunks, lexical_result.metadatas)):
            if chunk not in lexical_chunks_set:
                chunks.append(chunk)
                meta = meta.copy()
                meta.update({
                    "chunk_type": "hybrid",
                    "chunk_idx": len(chunks) - 1,
                    "strategy": "lexical"
                })
                metadatas.append(meta)
                lexical_chunks_set.add(chunk)
        
        return ChunkingResult(chunks=chunks, metadatas=metadatas)


class LexicalChunker:
    """Lexical 청킹: 토큰/문자/문장 단위 분할"""
    
    def __init__(
        self,
        chunk_size: int = 500,
        chunk_overlap: int = 50,
        chunk_by: str = "token"  # "token", "character", "sentence"
    ):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.chunk_by = chunk_by
    
    def chunk(self, text: str, metadata: Optional[Dict] = None) -> ChunkingResult:
        """
        Lexical 청킹
        
        Args:
            text: 청킹할 텍스트
            metadata: 원본 메타데이터
            
        Returns:
            ChunkingResult: 청킹된 텍스트와 메타데이터
        """
        if not LANGCHAIN_AVAILABLE:
            # 폴백: 간단한 문자 기반 분할
            return self._simple_chunk(text, metadata)
        
        try:
            if self.chunk_by == "token":
                splitter = TokenTextSplitter(
                    chunk_size=self.chunk_size,
                    chunk_overlap=self.chunk_overlap
                )
            elif self.chunk_by == "character":
                splitter = CharacterTextSplitter(
                    chunk_size=self.chunk_size,
                    chunk_overlap=self.chunk_overlap,
                    separator="\n\n"
                )
            else:  # sentence
                splitter = RecursiveCharacterTextSplitter(
                    chunk_size=self.chunk_size,
                    chunk_overlap=self.chunk_overlap,
                    separators=["\n\n", "\n", ". ", " ", ""]
                )
            
            chunks = splitter.split_text(text)
            
            metadatas = []
            for idx, chunk in enumerate(chunks):
                chunk_metadata = (metadata or {}).copy()
                chunk_metadata.update({
                    "chunk_type": "lexical",
                    "chunk_idx": idx,
                    "chunk_by": self.chunk_by
                })
                metadatas.append(chunk_metadata)
            
            return ChunkingResult(chunks=chunks, metadatas=metadatas)
        
        except Exception as e:
            log.error(f"Error in lexical chunking: {e}")
            return self._simple_chunk(text, metadata)
    
    def _simple_chunk(self, text: str, metadata: Optional[Dict] = None) -> ChunkingResult:
        """간단한 문자 기반 청킹 (폴백)"""
        chunks = []
        metadatas = []
        
        words = text.split()
        current_chunk = []
        current_length = 0
        
        for word in words:
            word_length = len(word) + 1  # +1 for space
            
            if current_length + word_length > self.chunk_size and current_chunk:
                chunks.append(" ".join(current_chunk))
                chunk_metadata = (metadata or {}).copy()
                chunk_metadata.update({
                    "chunk_type": "lexical",
                    "chunk_idx": len(chunks) - 1,
                    "chunk_by": "character"
                })
                metadatas.append(chunk_metadata)
                
                # 오버랩 처리
                if self.chunk_overlap > 0:
                    overlap_words = current_chunk[-min(len(current_chunk), self.chunk_overlap // 10):]
                    current_chunk = overlap_words + [word]
                    current_length = sum(len(w) + 1 for w in current_chunk)
                else:
                    current_chunk = [word]
                    current_length = word_length
            else:
                current_chunk.append(word)
                current_length += word_length
        
        # 마지막 청크
        if current_chunk:
            chunks.append(" ".join(current_chunk))
            chunk_metadata = (metadata or {}).copy()
            chunk_metadata.update({
                "chunk_type": "lexical",
                "chunk_idx": len(chunks) - 1,
                "chunk_by": "character"
            })
            metadatas.append(chunk_metadata)
        
        return ChunkingResult(chunks=chunks, metadatas=metadatas)


class ChunkingStrategyFactory:
    """청킹 전략 팩토리"""
    
    @staticmethod
    def create_chunker(
        strategy: str,
        chunk_size: int = 1000,
        chunk_overlap: int = 200,
        **kwargs
    ):
        """
        청킹 전략에 따른 청커 생성
        
        Args:
            strategy: "semantic", "hybrid", "lexical"
            chunk_size: 청크 크기
            chunk_overlap: 오버랩 크기
            **kwargs: 전략별 추가 파라미터
            
        Returns:
            Chunker 인스턴스
        """
        strategy_enum = ChunkingStrategy(strategy.lower())
        
        if strategy_enum == ChunkingStrategy.SEMANTIC:
            return SemanticChunker(
                chunk_size=chunk_size,
                chunk_overlap=chunk_overlap,
                similarity_threshold=kwargs.get("similarity_threshold", 0.7),
                embedding_model=kwargs.get("embedding_model")
            )
        elif strategy_enum == ChunkingStrategy.HYBRID:
            return HybridChunker(
                chunk_size=chunk_size,
                chunk_overlap=chunk_overlap,
                semantic_weight=kwargs.get("semantic_weight", 0.6),
                lexical_weight=kwargs.get("lexical_weight", 0.4),
                embedding_model=kwargs.get("embedding_model")
            )
        elif strategy_enum == ChunkingStrategy.LEXICAL:
            return LexicalChunker(
                chunk_size=chunk_size,
                chunk_overlap=chunk_overlap,
                chunk_by=kwargs.get("chunk_by", "token")
            )
        else:
            raise ValueError(f"Unknown chunking strategy: {strategy}")

