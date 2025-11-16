#!/usr/bin/env python3
"""
다양한 소스에서 문서를 임베딩하는 예제 스크립트
"""

import os
import sys
from pathlib import Path

os.environ["DATA_DIR"] = str(Path(__file__).parent.parent / "data")
os.environ["FROM_INIT_PY"] = "true"
os.environ["VECTOR_DB"] = "chroma"

backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from open_webui.retrieval.data_sources import (
    LocalFolderSource,
    S3Source,
    AzureBlobSource,
    embed_documents_from_source
)
from open_webui.retrieval.vector.factory import Vector
from open_webui.config import RAG_EMBEDDING_ENGINE, RAG_EMBEDDING_MODEL
from open_webui.env import DATA_DIR


def example_local_folder():
    """로컬 폴더 예제"""
    print("Example: Local Folder")
    source = LocalFolderSource(
        folder_path=str(DATA_DIR / "documents"),
        recursive=True
    )
    vector_db = Vector.get_vector("chroma")
    
    def embedding_function(texts):
        from sentence_transformers import SentenceTransformer
        model = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")
        embeddings = model.encode(texts, show_progress_bar=True)
        return embeddings.tolist() if hasattr(embeddings, 'tolist') else embeddings
    
    stats = embed_documents_from_source(
        source=source,
        collection_name="local_documents",
        vector_db_client=vector_db,
        embedding_function=embedding_function,
        chunking_strategy="lexical"
    )
    print(f"Embedded {stats['total_chunks']} chunks from {stats['total_documents']} documents")


def example_s3():
    """AWS S3 예제"""
    print("Example: AWS S3")
    # 실제 사용 시 환경 변수나 인자로 전달
    # source = S3Source(
    #     bucket_name="your-bucket",
    #     prefix="documents/",
    #     aws_access_key_id=os.environ.get("AWS_ACCESS_KEY_ID"),
    #     aws_secret_access_key=os.environ.get("AWS_SECRET_ACCESS_KEY"),
    #     region_name="us-east-1"
    # )
    print("S3 example - configure credentials and uncomment code")


def example_azure():
    """Azure Blob Storage 예제"""
    print("Example: Azure Blob Storage")
    # 실제 사용 시 환경 변수나 인자로 전달
    # source = AzureBlobSource(
    #     container_name="documents",
    #     account_name=os.environ.get("AZURE_STORAGE_ACCOUNT_NAME"),
    #     account_key=os.environ.get("AZURE_STORAGE_ACCOUNT_KEY")
    # )
    print("Azure example - configure credentials and uncomment code")


if __name__ == "__main__":
    print("=" * 50)
    print("Document Embedding from Various Sources")
    print("=" * 50)
    
    # 로컬 폴더 예제만 실행 (S3, Azure는 설정 필요)
    example_local_folder()
    
    print("\nFor S3 and Azure examples, configure credentials and uncomment the code.")

