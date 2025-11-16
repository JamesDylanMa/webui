#!/usr/bin/env python3
"""
지정된 폴더의 문서들을 벡터 DB에 임베딩하는 스크립트
"""

import os
import sys
import argparse
from pathlib import Path

# 환경 변수 설정
os.environ["DATA_DIR"] = str(Path(__file__).parent.parent / "data")
os.environ["FROM_INIT_PY"] = "true"

# 프로젝트 루트를 Python 경로에 추가
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from open_webui.retrieval.data_sources import LocalFolderSource, embed_documents_from_source
from open_webui.retrieval.vector.factory import Vector
from open_webui.config import (
    CHUNKING_STRATEGY,
    RAG_EMBEDDING_ENGINE, RAG_EMBEDDING_MODEL,
    RAG_EMBEDDING_CONTENT_PREFIX,
    VECTOR_DB
)
from open_webui.retrieval.utils import generate_embeddings
from open_webui.env import DATA_DIR


def main():
    parser = argparse.ArgumentParser(description="Embed documents from a folder")
    parser.add_argument("--folder", type=str, help="Folder path containing documents")
    parser.add_argument("--collection", type=str, default="documents", help="Collection name")
    parser.add_argument("--vector-db", type=str, default=None, help="Vector DB type (chroma, faiss, etc.)")
    parser.add_argument("--chunking-strategy", type=str, default=None, help="Chunking strategy (semantic, hybrid, lexical)")
    args = parser.parse_args()
    
    # 폴더 경로
    if args.folder:
        folder_path = Path(args.folder)
    else:
        folder_path = DATA_DIR / "documents"
    
    if not folder_path.exists():
        print(f"Folder does not exist: {folder_path}")
        return
    
    # Vector DB 타입
    vector_db_type = args.vector_db or str(VECTOR_DB) or "chroma"
    os.environ["VECTOR_DB"] = vector_db_type
    
    # 데이터 소스 생성
    print(f"Loading documents from: {folder_path}")
    source = LocalFolderSource(
        folder_path=str(folder_path),
        recursive=True
    )
    
    # Vector DB 클라이언트 생성
    print(f"Using Vector DB: {vector_db_type}")
    vector_db = Vector.get_vector(vector_db_type)
    
    # 임베딩 함수
    def embedding_function(texts):
        if isinstance(texts, str):
            texts = [texts]
        
        embedding_engine = str(RAG_EMBEDDING_ENGINE) if RAG_EMBEDDING_ENGINE else ""
        embedding_model = str(RAG_EMBEDDING_MODEL) if RAG_EMBEDDING_MODEL else "sentence-transformers/all-MiniLM-L6-v2"
        
        if embedding_engine == "":
            from sentence_transformers import SentenceTransformer
            model = SentenceTransformer(embedding_model)
            embeddings = model.encode(texts, show_progress_bar=True)
            if hasattr(embeddings, 'tolist'):
                return embeddings.tolist()
            return embeddings if isinstance(embeddings, list) else [list(emb) for emb in embeddings]
        else:
            embeddings = []
            for text in texts:
                try:
                    emb = generate_embeddings(
                        engine=embedding_engine,
                        model=embedding_model,
                        text=text,
                        prefix=RAG_EMBEDDING_CONTENT_PREFIX,
                    )
                    if isinstance(emb, dict) and 'data' in emb:
                        emb_list = emb['data'][0]['embedding'] if emb['data'] else None
                    elif isinstance(emb, list):
                        emb_list = emb[0] if len(emb) > 0 and isinstance(emb[0], list) else emb
                    else:
                        emb_list = emb
                    
                    if emb_list is None:
                        raise ValueError("Failed to generate embedding")
                    embeddings.append(emb_list)
                except Exception as e:
                    print(f"Error: {e}")
                    from sentence_transformers import SentenceTransformer
                    model = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")
                    emb = model.encode([text])[0]
                    embeddings.append(emb.tolist() if hasattr(emb, 'tolist') else list(emb))
            return embeddings
    
    # 청킹 전략
    chunking_strategy = args.chunking_strategy or str(CHUNKING_STRATEGY) or "lexical"
    
    # 청킹 파라미터
    import open_webui.config as config_module
    chunk_size = int(getattr(config_module, 'CHUNK_SIZE', 1000))
    chunk_overlap = int(getattr(config_module, 'CHUNK_OVERLAP', 100))
    
    chunking_kwargs = {
        "chunk_size": chunk_size,
        "chunk_overlap": chunk_overlap,
    }
    
    if chunking_strategy == "semantic":
        threshold = getattr(config_module, 'SEMANTIC_SIMILARITY_THRESHOLD', 0.7)
        chunking_kwargs["similarity_threshold"] = float(threshold)
    elif chunking_strategy == "hybrid":
        semantic_weight = getattr(config_module, 'HYBRID_SEMANTIC_WEIGHT', 0.6)
        lexical_weight = getattr(config_module, 'HYBRID_LEXICAL_WEIGHT', 0.4)
        chunking_kwargs["semantic_weight"] = float(semantic_weight)
        chunking_kwargs["lexical_weight"] = float(lexical_weight)
    
    # 문서 임베딩
    print("-" * 50)
    print(f"Collection: {args.collection}")
    print(f"Chunking strategy: {chunking_strategy}")
    print("-" * 50)
    
    stats = embed_documents_from_source(
        source=source,
        collection_name=args.collection,
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
    print("-" * 50)
    print("Done!")


if __name__ == "__main__":
    main()

