#!/usr/bin/env python3
"""
documents 폴더의 문서들을 ChromaDB에 임베딩하는 스크립트
"""

import os
import sys
from pathlib import Path

# 환경 변수 설정
os.environ["DATA_DIR"] = str(Path(__file__).parent.parent / "data")
os.environ["FROM_INIT_PY"] = "true"
os.environ["VECTOR_DB"] = "chroma"

# 프로젝트 루트를 Python 경로에 추가
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from open_webui.retrieval.data_sources import LocalFolderSource, embed_documents_from_source
from open_webui.retrieval.vector.factory import Vector
from open_webui.config import (
    RAG_EMBEDDING_ENGINE, RAG_EMBEDDING_MODEL,
    RAG_EMBEDDING_CONTENT_PREFIX
)
# CHUNKING_STRATEGY는 환경 변수에서 직접 가져오기 (config.py에 정의되어 있지만 import 문제 방지)
import os
CHUNKING_STRATEGY = os.environ.get("CHUNKING_STRATEGY", "lexical")
# PersistentConfig 객체에서 실제 값을 가져오기 위해 app state를 사용하거나 직접 값 가져오기
try:
    # config 모듈에서 직접 값 가져오기 시도
    import open_webui.config as config_module
    CHUNK_SIZE = int(getattr(config_module, 'CHUNK_SIZE', 1000))
    CHUNK_OVERLAP = int(getattr(config_module, 'CHUNK_OVERLAP', 100))
except:
    # 기본값 사용
    CHUNK_SIZE = 1000
    CHUNK_OVERLAP = 100
from open_webui.retrieval.utils import generate_embeddings
from open_webui.env import DATA_DIR


def main():
    # 문서 폴더 경로
    documents_path = DATA_DIR / "documents"
    
    if not documents_path.exists():
        print(f"Creating documents directory: {documents_path}")
        documents_path.mkdir(parents=True, exist_ok=True)
        print(f"Please add documents to {documents_path} and run again.")
        return
    
    # 파일 확인
    files = list(documents_path.glob("*"))
    if not files:
        print(f"No documents found in {documents_path}")
        print("Please add documents (PDF, TXT, DOCX, etc.) to this folder.")
        return
    
    print(f"Found {len(files)} files in {documents_path}")
    
    # 데이터 소스 생성
    print(f"Loading documents from: {documents_path}")
    source = LocalFolderSource(
        folder_path=str(documents_path),
        recursive=True
    )
    
    # Vector DB 클라이언트 생성 (ChromaDB)
    print("Using Vector DB: chroma")
    vector_db = Vector.get_vector("chroma")
    
    # 임베딩 함수 생성
    def embedding_function(texts):
        """텍스트 리스트를 임베딩으로 변환"""
        if isinstance(texts, str):
            texts = [texts]
        
        # 기본 임베딩 엔진 사용 (sentence-transformers)
        embedding_engine = str(RAG_EMBEDDING_ENGINE) if RAG_EMBEDDING_ENGINE else ""
        embedding_model = str(RAG_EMBEDDING_MODEL) if RAG_EMBEDDING_MODEL else "sentence-transformers/all-MiniLM-L6-v2"
        
        if embedding_engine == "":
            # 로컬 임베딩 모델 사용
            from sentence_transformers import SentenceTransformer
            print(f"Loading embedding model: {embedding_model}")
            model = SentenceTransformer(embedding_model)
            embeddings = model.encode(texts, show_progress_bar=True)
            # numpy array를 list로 변환
            if hasattr(embeddings, 'tolist'):
                return embeddings.tolist()
            elif isinstance(embeddings, list):
                return embeddings
            else:
                return [list(emb) for emb in embeddings] if len(texts) > 1 else list(embeddings)
        else:
            # API 기반 임베딩 (Ollama, OpenAI 등) - 동기 함수로 변환 필요
            print(f"Using API embedding engine: {embedding_engine}")
            embeddings = []
            for text in texts:
                try:
                    emb = generate_embeddings(
                        engine=embedding_engine,
                        model=embedding_model,
                        text=text,
                        prefix=RAG_EMBEDDING_CONTENT_PREFIX,
                    )
                    # 응답 형식에 따라 처리
                    if isinstance(emb, dict) and 'data' in emb:
                        # OpenAI 형식 응답
                        emb_list = emb['data'][0]['embedding'] if emb['data'] else None
                    elif isinstance(emb, list):
                        emb_list = emb[0] if len(emb) > 0 and isinstance(emb[0], list) else emb
                    else:
                        emb_list = emb
                    
                    if emb_list is None:
                        raise ValueError(f"Failed to generate embedding for text: {text[:50]}...")
                    
                    embeddings.append(emb_list)
                except Exception as e:
                    print(f"Error generating embedding: {e}")
                    # 기본 모델로 폴백
                    from sentence_transformers import SentenceTransformer
                    model = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")
                    emb = model.encode([text])[0]
                    embeddings.append(emb.tolist() if hasattr(emb, 'tolist') else list(emb))
            
            return embeddings
    
    # 청킹 파라미터 (PersistentConfig에서 실제 값 추출)
    chunk_size = int(CHUNK_SIZE) if hasattr(CHUNK_SIZE, '__int__') or isinstance(CHUNK_SIZE, (int, float)) else 1000
    chunk_overlap = int(CHUNK_OVERLAP) if hasattr(CHUNK_OVERLAP, '__int__') or isinstance(CHUNK_OVERLAP, (int, float)) else 100
    
    chunking_kwargs = {
        "chunk_size": chunk_size,
        "chunk_overlap": chunk_overlap,
    }
    
    chunking_strategy = str(CHUNKING_STRATEGY) if CHUNKING_STRATEGY else "lexical"
    
    if chunking_strategy == "semantic":
        threshold = float(os.environ.get("SEMANTIC_SIMILARITY_THRESHOLD", "0.7"))
        chunking_kwargs["similarity_threshold"] = threshold
    elif chunking_strategy == "hybrid":
        semantic_weight = float(os.environ.get("HYBRID_SEMANTIC_WEIGHT", "0.6"))
        lexical_weight = float(os.environ.get("HYBRID_LEXICAL_WEIGHT", "0.4"))
        chunking_kwargs["semantic_weight"] = semantic_weight
        chunking_kwargs["lexical_weight"] = lexical_weight
    
    # 컬렉션 이름
    collection_name = "documents"
    
    # 문서 임베딩
    print("-" * 50)
    print(f"Collection: {collection_name}")
    print(f"Chunking strategy: {chunking_strategy}")
    print(f"Chunk size: {chunk_size}, Overlap: {chunk_overlap}")
    print("-" * 50)
    
    stats = embed_documents_from_source(
        source=source,
        collection_name=collection_name,
        vector_db_client=vector_db,
        embedding_function=embedding_function,
        chunking_strategy=chunking_strategy,
        **chunking_kwargs
    )
    
    # 결과 출력
    print("-" * 50)
    print("Embedding Statistics:")
    print(f"  Total documents: {stats['total_documents']}")
    print(f"  Total chunks: {stats['total_chunks']}")
    print(f"  Success: {stats['success']}")
    print(f"  Failed: {stats['failed']}")
    if stats['errors']:
        print(f"  Errors: {len(stats['errors'])}")
        for error in stats['errors'][:5]:
            print(f"    - {error}")
    print("-" * 50)
    print("Done! Documents are now embedded in ChromaDB.")


if __name__ == "__main__":
    main()

