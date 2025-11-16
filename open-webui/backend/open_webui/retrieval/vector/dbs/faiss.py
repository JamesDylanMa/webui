"""
Faiss 벡터 데이터베이스 클라이언트
"""

import os
import logging
import pickle
import numpy as np
from pathlib import Path
from typing import List, Dict, Optional, Any
import uuid

try:
    import faiss
    FAISS_AVAILABLE = True
except ImportError:
    FAISS_AVAILABLE = False

from open_webui.retrieval.vector.main import VectorDBBase
from open_webui.env import DATA_DIR, SRC_LOG_LEVELS

log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS.get("RAG", "INFO"))


class FaissClient(VectorDBBase):
    """Faiss 벡터 DB 클라이언트"""
    
    def __init__(self):
        if not FAISS_AVAILABLE:
            raise ImportError("faiss-cpu or faiss-gpu is required for FaissClient")
        
        self.index_path = Path(DATA_DIR) / "faiss_index"
        self.index_path.mkdir(parents=True, exist_ok=True)
        
        # 인덱스 타입 (기본: IVF_FLAT)
        self.index_type = os.environ.get("FAISS_INDEX_TYPE", "IVF_FLAT")
        
        # 컬렉션별 인덱스와 문서 저장소
        self.indices: Dict[str, Any] = {}
        self.doc_stores: Dict[str, Dict[str, Dict]] = {}  # {collection: {id: {text, metadata, vector}}}
        self.dimension = None
    
    def _create_index(self, dimension: int, collection_name: str):
        """Faiss 인덱스 생성"""
        if self.index_type == "HNSW":
            # HNSW 인덱스 (고속 검색)
            index = faiss.IndexHNSWFlat(dimension, 32)
            index.hnsw.efConstruction = 200
            index.hnsw.efSearch = 50
        elif self.index_type == "IVF_FLAT":
            # IVF_FLAT 인덱스 (균형잡힌 성능)
            nlist = 100  # 클러스터 수
            quantizer = faiss.IndexFlatL2(dimension)
            index = faiss.IndexIVFFlat(quantizer, dimension, nlist)
            index.nprobe = 10  # 검색 시 탐색할 클러스터 수
        else:  # FLAT
            # FLAT 인덱스 (정확한 검색, 느림)
            index = faiss.IndexFlatL2(dimension)
        
        return index
    
    def _load_index(self, collection_name: str):
        """인덱스 로드"""
        index_file = self.index_path / f"{collection_name}.index"
        doc_store_file = self.index_path / f"{collection_name}.pkl"
        
        if index_file.exists() and doc_store_file.exists():
            try:
                # 인덱스 로드
                index = faiss.read_index(str(index_file))
                self.indices[collection_name] = index
                
                # 문서 저장소 로드
                with open(doc_store_file, 'rb') as f:
                    self.doc_stores[collection_name] = pickle.load(f)
                
                # 차원 설정
                if collection_name in self.doc_stores and self.doc_stores[collection_name]:
                    sample_id = next(iter(self.doc_stores[collection_name].values()))
                    if 'vector' in sample_id:
                        self.dimension = len(sample_id['vector'])
                
                log.info(f"Loaded index for collection: {collection_name}")
                return True
            except Exception as e:
                log.error(f"Error loading index for {collection_name}: {e}")
                return False
        
        return False
    
    def _save_index(self, collection_name: str):
        """인덱스 저장"""
        if collection_name not in self.indices:
            return
        
        index_file = self.index_path / f"{collection_name}.index"
        doc_store_file = self.index_path / f"{collection_name}.pkl"
        
        try:
            # 인덱스 저장
            faiss.write_index(self.indices[collection_name], str(index_file))
            
            # 문서 저장소 저장
            with open(doc_store_file, 'wb') as f:
                pickle.dump(self.doc_stores.get(collection_name, {}), f)
            
            log.info(f"Saved index for collection: {collection_name}")
        except Exception as e:
            log.error(f"Error saving index for {collection_name}: {e}")
    
    def has_collection(self, collection_name: str) -> bool:
        """컬렉션 존재 여부 확인"""
        if collection_name in self.indices:
            return True
        
        # 파일 시스템에서 확인
        index_file = self.index_path / f"{collection_name}.index"
        return index_file.exists()
    
    def create_collection(self, collection_name: str, metadata: Optional[Dict] = None):
        """컬렉션 생성"""
        if not self.has_collection(collection_name):
            # 인덱스는 벡터 삽입 시 생성됨
            self.doc_stores[collection_name] = {}
            log.info(f"Created collection: {collection_name}")
        else:
            self._load_index(collection_name)
    
    def delete_collection(self, collection_name: str):
        """컬렉션 삭제"""
        if collection_name in self.indices:
            del self.indices[collection_name]
        
        if collection_name in self.doc_stores:
            del self.doc_stores[collection_name]
        
        # 파일 삭제
        index_file = self.index_path / f"{collection_name}.index"
        doc_store_file = self.index_path / f"{collection_name}.pkl"
        
        if index_file.exists():
            index_file.unlink()
        if doc_store_file.exists():
            doc_store_file.unlink()
        
        log.info(f"Deleted collection: {collection_name}")
    
    def insert(self, collection_name: str, items: List[Dict]):
        """벡터 삽입"""
        if not items:
            return
        
        # 컬렉션 초기화
        if collection_name not in self.doc_stores:
            self.doc_stores[collection_name] = {}
        
        # 기존 인덱스 로드 또는 생성
        if collection_name not in self.indices:
            if not self._load_index(collection_name):
                # 첫 벡터의 차원으로 인덱스 생성
                if items[0].get('vector'):
                    self.dimension = len(items[0]['vector'])
                    self.indices[collection_name] = self._create_index(self.dimension, collection_name)
                else:
                    raise ValueError("Vector dimension cannot be determined")
        
        # 벡터와 메타데이터 추출
        vectors = []
        for item in items:
            vector = item.get('vector')
            if vector is None:
                continue
            
            vectors.append(vector)
            
            # 문서 저장소에 저장
            item_id = item.get('id', str(uuid.uuid4()))
            self.doc_stores[collection_name][item_id] = {
                'text': item.get('text', ''),
                'metadata': item.get('metadata', {}),
                'vector': vector
            }
        
        if not vectors:
            return
        
        # NumPy 배열로 변환
        vectors_np = np.array(vectors, dtype=np.float32)
        
        # 인덱스가 훈련되지 않았다면 훈련
        if hasattr(self.indices[collection_name], 'is_trained') and not self.indices[collection_name].is_trained:
            if len(vectors_np) >= 100:  # 최소 훈련 샘플 수
                self.indices[collection_name].train(vectors_np)
            else:
                # 샘플이 적으면 FLAT 인덱스로 변경
                log.warning(f"Not enough samples for training, using FLAT index for {collection_name}")
                self.indices[collection_name] = faiss.IndexFlatL2(self.dimension)
        
        # 벡터 추가
        self.indices[collection_name].add(vectors_np)
        
        # 인덱스 저장
        self._save_index(collection_name)
        
        log.info(f"Inserted {len(vectors)} vectors into collection: {collection_name}")
    
    def search(self, collection_name: str, query_vector: List[float], limit: int = 10, **kwargs) -> Dict:
        """벡터 검색"""
        if not self.has_collection(collection_name):
            return {"documents": [], "metadatas": [], "distances": [], "ids": []}
        
        # 인덱스 로드
        if collection_name not in self.indices:
            if not self._load_index(collection_name):
                return {"documents": [], "metadatas": [], "distances": [], "ids": []}
        
        # 쿼리 벡터를 NumPy 배열로 변환
        query_np = np.array([query_vector], dtype=np.float32)
        
        # 검색
        k = min(limit, self.indices[collection_name].ntotal) if self.indices[collection_name].ntotal > 0 else limit
        distances, indices = self.indices[collection_name].search(query_np, k)
        
        # 결과 구성
        documents = []
        metadatas = []
        ids = []
        distances_list = []
        
        doc_store = self.doc_stores.get(collection_name, {})
        doc_list = list(doc_store.items())
        
        for idx, dist in zip(indices[0], distances[0]):
            if idx < len(doc_list):
                doc_id, doc_data = doc_list[idx]
                documents.append([doc_data.get('text', '')])
                metadatas.append([doc_data.get('metadata', {})])
                ids.append([doc_id])
                distances_list.append([float(dist)])
        
        return {
            "documents": documents,
            "metadatas": metadatas,
            "distances": distances_list,
            "ids": ids
        }
    
    def delete(self, collection_name: str, ids: List[str]):
        """벡터 삭제"""
        if collection_name not in self.doc_stores:
            return
        
        # 문서 저장소에서 삭제
        for doc_id in ids:
            if doc_id in self.doc_stores[collection_name]:
                del self.doc_stores[collection_name][doc_id]
        
        # 인덱스 재구성 (Faiss는 삭제를 직접 지원하지 않음)
        if collection_name in self.indices:
            # 모든 벡터를 다시 삽입
            doc_store = self.doc_stores[collection_name]
            if doc_store:
                vectors = [doc['vector'] for doc in doc_store.values()]
                vectors_np = np.array(vectors, dtype=np.float32)
                
                # 새 인덱스 생성
                self.indices[collection_name] = self._create_index(self.dimension, collection_name)
                if hasattr(self.indices[collection_name], 'is_trained') and not self.indices[collection_name].is_trained:
                    if len(vectors_np) >= 100:
                        self.indices[collection_name].train(vectors_np)
                    else:
                        self.indices[collection_name] = faiss.IndexFlatL2(self.dimension)
                
                self.indices[collection_name].add(vectors_np)
                self._save_index(collection_name)
        
        log.info(f"Deleted {len(ids)} vectors from collection: {collection_name}")

