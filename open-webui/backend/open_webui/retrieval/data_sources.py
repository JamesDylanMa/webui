"""
데이터 소스 모듈
로컬 폴더, AWS S3, Azure Blob Storage에서 문서 로드
"""

import os
import logging
import mimetypes
from pathlib import Path
from typing import List, Dict, Optional, Iterator
from abc import ABC, abstractmethod

try:
    import boto3
    from botocore.exceptions import ClientError
    BOTO3_AVAILABLE = True
except ImportError:
    BOTO3_AVAILABLE = False

try:
    from azure.storage.blob import BlobServiceClient
    AZURE_AVAILABLE = True
except ImportError:
    AZURE_AVAILABLE = False

from langchain_core.documents import Document
from open_webui.retrieval.loaders.main import Loader
from open_webui.env import SRC_LOG_LEVELS

log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS.get("RAG", "INFO"))


class DataSourceBase(ABC):
    """데이터 소스 기본 클래스"""
    
    @abstractmethod
    def load_documents(self) -> Iterator[Document]:
        """문서 로드"""
        pass


class LocalFolderSource(DataSourceBase):
    """로컬 폴더에서 문서 로드"""
    
    def __init__(self, folder_path: str, recursive: bool = True):
        self.folder_path = Path(folder_path)
        self.recursive = recursive
        self.loader = Loader()
    
    def load_documents(self) -> Iterator[Document]:
        """폴더에서 문서 로드"""
        if not self.folder_path.exists():
            log.warning(f"Folder does not exist: {self.folder_path}")
            return
        
        if self.recursive:
            pattern = "**/*"
        else:
            pattern = "*"
        
        for file_path in self.folder_path.glob(pattern):
            if file_path.is_file():
                try:
                    # 파일 확장자 확인
                    ext = file_path.suffix.lower()
                    if ext not in ['.pdf', '.txt', '.md', '.docx', '.doc', '.html', '.htm']:
                        continue
                    
                    # MIME 타입 추정
                    content_type, _ = mimetypes.guess_type(str(file_path))
                    if content_type is None:
                        content_type = 'application/octet-stream'
                    
                    # 파일 읽기
                    with open(file_path, 'rb') as f:
                        file_content = f.read()
                    
                    # Loader를 사용하여 문서 로드
                    filename = file_path.name
                    file_path_str = str(file_path)
                    
                    docs = self.loader.load(
                        filename=filename,
                        file_content_type=content_type,
                        file_path=file_path_str
                    )
                    
                    for doc in docs:
                        # 메타데이터 추가
                        doc.metadata.update({
                            "source": str(file_path),
                            "file_name": filename,
                            "file_path": file_path_str
                        })
                        yield doc
                
                except Exception as e:
                    log.error(f"Error loading file {file_path}: {e}")
                    continue


class S3Source(DataSourceBase):
    """AWS S3에서 문서 로드"""
    
    def __init__(
        self,
        bucket_name: str,
        prefix: str = "",
        aws_access_key_id: Optional[str] = None,
        aws_secret_access_key: Optional[str] = None,
        region_name: str = "us-east-1"
    ):
        if not BOTO3_AVAILABLE:
            raise ImportError("boto3 is required for S3Source")
        
        self.bucket_name = bucket_name
        self.prefix = prefix
        self.region_name = region_name
        
        # S3 클라이언트 생성
        if aws_access_key_id and aws_secret_access_key:
            self.s3_client = boto3.client(
                's3',
                aws_access_key_id=aws_access_key_id,
                aws_secret_access_key=aws_secret_access_key,
                region_name=region_name
            )
        else:
            # 환경 변수 또는 IAM 역할 사용
            self.s3_client = boto3.client('s3', region_name=region_name)
        
        self.loader = Loader()
    
    def load_documents(self) -> Iterator[Document]:
        """S3에서 문서 로드"""
        try:
            # S3 객체 목록 가져오기
            paginator = self.s3_client.get_paginator('list_objects_v2')
            pages = paginator.paginate(Bucket=self.bucket_name, Prefix=self.prefix)
            
            for page in pages:
                if 'Contents' not in page:
                    continue
                
                for obj in page['Contents']:
                    key = obj['Key']
                    
                    # 파일 확장자 확인
                    if not any(key.lower().endswith(ext) for ext in ['.pdf', '.txt', '.md', '.docx', '.doc', '.html', '.htm']):
                        continue
                    
                    try:
                        # 파일 다운로드
                        response = self.s3_client.get_object(Bucket=self.bucket_name, Key=key)
                        file_content = response['Body'].read()
                        
                        # MIME 타입 추정
                        content_type = response.get('ContentType', 'application/octet-stream')
                        
                        # Loader를 사용하여 문서 로드
                        filename = os.path.basename(key)
                        docs = self.loader.load(
                            filename=filename,
                            file_content_type=content_type,
                            file_path=f"s3://{self.bucket_name}/{key}"
                        )
                        
                        for doc in docs:
                            doc.metadata.update({
                                "source": f"s3://{self.bucket_name}/{key}",
                                "file_name": filename,
                                "s3_bucket": self.bucket_name,
                                "s3_key": key
                            })
                            yield doc
                    
                    except Exception as e:
                        log.error(f"Error loading S3 object {key}: {e}")
                        continue
        
        except ClientError as e:
            log.error(f"Error accessing S3: {e}")
            raise


class AzureBlobSource(DataSourceBase):
    """Azure Blob Storage에서 문서 로드"""
    
    def __init__(
        self,
        container_name: str,
        account_name: Optional[str] = None,
        account_key: Optional[str] = None,
        connection_string: Optional[str] = None,
        prefix: str = ""
    ):
        if not AZURE_AVAILABLE:
            raise ImportError("azure-storage-blob is required for AzureBlobSource")
        
        self.container_name = container_name
        self.prefix = prefix
        
        # BlobServiceClient 생성
        if connection_string:
            self.blob_service_client = BlobServiceClient.from_connection_string(connection_string)
        elif account_name and account_key:
            account_url = f"https://{account_name}.blob.core.windows.net"
            self.blob_service_client = BlobServiceClient(
                account_url=account_url,
                credential=account_key
            )
        else:
            # 환경 변수 사용
            account_name = os.environ.get("AZURE_STORAGE_ACCOUNT_NAME")
            account_key = os.environ.get("AZURE_STORAGE_ACCOUNT_KEY")
            if not account_name or not account_key:
                raise ValueError("Azure credentials must be provided")
            account_url = f"https://{account_name}.blob.core.windows.net"
            self.blob_service_client = BlobServiceClient(
                account_url=account_url,
                credential=account_key
            )
        
        self.loader = Loader()
    
    def load_documents(self) -> Iterator[Document]:
        """Azure Blob Storage에서 문서 로드"""
        try:
            container_client = self.blob_service_client.get_container_client(self.container_name)
            
            # Blob 목록 가져오기
            blobs = container_client.list_blobs(name_starts_with=self.prefix)
            
            for blob in blobs:
                blob_name = blob.name
                
                # 파일 확장자 확인
                if not any(blob_name.lower().endswith(ext) for ext in ['.pdf', '.txt', '.md', '.docx', '.doc', '.html', '.htm']):
                    continue
                
                try:
                    # Blob 다운로드
                    blob_client = container_client.get_blob_client(blob_name)
                    file_content = blob_client.download_blob().readall()
                    
                    # MIME 타입 추정
                    content_type = blob.content_settings.content_type or 'application/octet-stream'
                    
                    # Loader를 사용하여 문서 로드
                    filename = os.path.basename(blob_name)
                    docs = self.loader.load(
                        filename=filename,
                        file_content_type=content_type,
                        file_path=f"azure://{self.container_name}/{blob_name}"
                    )
                    
                    for doc in docs:
                        doc.metadata.update({
                            "source": f"azure://{self.container_name}/{blob_name}",
                            "file_name": filename,
                            "container_name": self.container_name,
                            "blob_name": blob_name
                        })
                        yield doc
                
                except Exception as e:
                    log.error(f"Error loading Azure blob {blob_name}: {e}")
                    continue
        
        except Exception as e:
            log.error(f"Error accessing Azure Blob Storage: {e}")
            raise


def embed_documents_from_source(
    source: DataSourceBase,
    collection_name: str,
    vector_db_client,
    embedding_function,
    chunking_strategy: str = "lexical",
    **chunking_kwargs
) -> Dict:
    """
    데이터 소스에서 문서를 로드하고 임베딩하여 벡터 DB에 저장
    
    Args:
        source: 데이터 소스 인스턴스
        collection_name: 컬렉션 이름
        vector_db_client: 벡터 DB 클라이언트
        embedding_function: 임베딩 함수
        chunking_strategy: 청킹 전략 ("semantic", "hybrid", "lexical")
        **chunking_kwargs: 청킹 파라미터
        
    Returns:
        통계 딕셔너리
    """
    from open_webui.retrieval.chunking_strategies import ChunkingStrategyFactory
    
    stats = {
        "total_documents": 0,
        "total_chunks": 0,
        "success": 0,
        "failed": 0,
        "errors": []
    }
    
    try:
        # 청커 생성
        chunker = ChunkingStrategyFactory.create_chunker(
            strategy=chunking_strategy,
            **chunking_kwargs
        )
        
        # 문서 로드 및 처리
        all_chunks = []
        all_metadatas = []
        
        for doc in source.load_documents():
            stats["total_documents"] += 1
            
            try:
                # 청킹
                chunking_result = chunker.chunk(doc.page_content, doc.metadata)
                
                # 청크와 메타데이터 수집
                for chunk, metadata in zip(chunking_result.chunks, chunking_result.metadatas):
                    all_chunks.append(chunk)
                    all_metadatas.append(metadata)
                    stats["total_chunks"] += 1
                
                stats["success"] += 1
            
            except Exception as e:
                log.error(f"Error processing document: {e}")
                stats["failed"] += 1
                stats["errors"].append(f"Document processing error: {str(e)}")
                continue
        
        # 배치로 임베딩 생성
        if all_chunks:
            log.info(f"Generating embeddings for {len(all_chunks)} chunks...")
            embeddings = embedding_function(all_chunks)
            
            # 벡터 아이템 생성
            vector_items = []
            for idx, (chunk, metadata, embedding) in enumerate(zip(all_chunks, all_metadatas, embeddings)):
                vector_items.append({
                    "id": f"{collection_name}_{stats['total_documents']}_{idx}_{metadata.get('content_hash', '')}",
                    "text": chunk,
                    "vector": embedding,
                    "metadata": metadata
                })
            
            # 벡터 DB에 삽입
            log.info(f"Inserting {len(vector_items)} vectors into collection '{collection_name}'...")
            vector_db_client.insert(collection_name=collection_name, items=vector_items)
            
            log.info(f"Successfully embedded {stats['total_chunks']} chunks from {stats['total_documents']} documents")
        else:
            log.warning("No chunks to embed")
        
    except Exception as e:
        log.error(f"Error embedding documents: {e}")
        stats["errors"].append(str(e))
        raise
    
    return stats

