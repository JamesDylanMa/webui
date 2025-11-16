"""
RDFox 벡터 데이터베이스 클라이언트
RDFox는 주로 Knowledge Graph용이지만, 메타데이터 기반 검색 지원
"""

import os
import logging
import requests
from typing import List, Dict, Optional, Any

from open_webui.retrieval.vector.main import VectorDBBase
from open_webui.env import SRC_LOG_LEVELS

log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS.get("RAG", "INFO"))


class RDFoxClient(VectorDBBase):
    """RDFox 벡터 DB 클라이언트 (메타데이터 기반 검색)"""
    
    def __init__(self):
        self.server_url = os.environ.get("RDFOX_SERVER_URL", "http://localhost:12110")
        self.username = os.environ.get("RDFOX_USERNAME", "admin")
        self.password = os.environ.get("RDFOX_PASSWORD", "admin")
        self.database = os.environ.get("RDFOX_DATABASE", "rag_db")
        
        self.session_token = None
        self._authenticate()
    
    def _authenticate(self):
        """RDFox 인증"""
        try:
            auth_url = f"{self.server_url}/datastores/{self.database}/content"
            response = requests.post(
                auth_url,
                auth=(self.username, self.password),
                headers={"Accept": "application/json"}
            )
            
            if response.status_code == 200:
                # 세션 토큰 추출 (RDFox API에 따라 다를 수 있음)
                self.session_token = response.headers.get("Authorization") or response.cookies.get("session")
                log.info(f"Authenticated with RDFox server: {self.server_url}")
            else:
                log.warning(f"RDFox authentication failed: {response.status_code}")
        
        except Exception as e:
            log.error(f"Error authenticating with RDFox: {e}")
    
    def _get_headers(self):
        """요청 헤더 생성"""
        headers = {"Accept": "application/json", "Content-Type": "application/json"}
        if self.session_token:
            headers["Authorization"] = f"Bearer {self.session_token}"
        return headers
    
    def has_collection(self, collection_name: str) -> bool:
        """컬렉션 존재 여부 확인"""
        # RDFox는 컬렉션 개념이 없으므로 항상 True 반환
        # 실제로는 데이터베이스에 데이터가 있는지 확인해야 함
        return True
    
    def create_collection(self, collection_name: str, metadata: Optional[Dict] = None):
        """컬렉션 생성 (RDFox에서는 데이터베이스 생성)"""
        try:
            # 데이터베이스 생성 (이미 존재하면 무시)
            url = f"{self.server_url}/datastores/{self.database}"
            response = requests.put(
                url,
                auth=(self.username, self.password),
                headers={"Accept": "application/json"}
            )
            
            if response.status_code in [200, 201, 409]:  # 409 = 이미 존재
                log.info(f"Created/verified database: {self.database}")
            else:
                log.warning(f"Failed to create database: {response.status_code}")
        
        except Exception as e:
            log.error(f"Error creating RDFox database: {e}")
    
    def delete_collection(self, collection_name: str):
        """컬렉션 삭제"""
        try:
            # SPARQL DELETE 쿼리로 모든 데이터 삭제
            delete_query = f"""
            DELETE {{
                ?s ?p ?o
            }}
            WHERE {{
                ?s ?p ?o
            }}
            """
            
            self._execute_sparql_update(delete_query)
            log.info(f"Deleted collection: {collection_name}")
        
        except Exception as e:
            log.error(f"Error deleting collection: {e}")
    
    def _execute_sparql_update(self, query: str):
        """SPARQL UPDATE 쿼리 실행"""
        try:
            url = f"{self.server_url}/datastores/{self.database}/content"
            response = requests.post(
                url,
                auth=(self.username, self.password),
                headers={
                    "Content-Type": "application/sparql-update",
                    "Accept": "application/json"
                },
                data=query
            )
            
            if response.status_code not in [200, 204]:
                log.error(f"SPARQL update failed: {response.status_code} - {response.text}")
            
            return response
        
        except Exception as e:
            log.error(f"Error executing SPARQL update: {e}")
            raise
    
    def _execute_sparql_query(self, query: str) -> Dict:
        """SPARQL SELECT 쿼리 실행"""
        try:
            url = f"{self.server_url}/datastores/{self.database}/content"
            params = {"query": query}
            response = requests.get(
                url,
                auth=(self.username, self.password),
                headers={"Accept": "application/sparql-results+json"},
                params=params
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                log.error(f"SPARQL query failed: {response.status_code} - {response.text}")
                return {"results": {"bindings": []}}
        
        except Exception as e:
            log.error(f"Error executing SPARQL query: {e}")
            return {"results": {"bindings": []}}
    
    def insert(self, collection_name: str, items: List[Dict]):
        """벡터 삽입 (RDFox에서는 RDF 트리플로 저장)"""
        try:
            # RDF 트리플 생성
            triples = []
            
            for item in items:
                item_id = item.get('id', f"doc_{len(items)}")
                text = item.get('text', '')
                metadata = item.get('metadata', {})
                
                # 기본 트리플: 문서 ID와 텍스트
                doc_uri = f"<http://example.org/doc/{item_id}>"
                triples.append(f"{doc_uri} <http://www.w3.org/1999/02/22-rdf-syntax-ns#type> <http://example.org/Document> .")
                triples.append(f'{doc_uri} <http://example.org/text> "{text.replace('"', '\\"')}" .')
                
                # 메타데이터를 트리플로 변환
                for key, value in metadata.items():
                    if isinstance(value, (str, int, float)):
                        value_str = str(value).replace('"', '\\"')
                        triples.append(f'{doc_uri} <http://example.org/{key}> "{value_str}" .')
            
            # RDF 데이터 삽입
            rdf_data = "\n".join(triples)
            url = f"{self.server_url}/datastores/{self.database}/content"
            
            response = requests.post(
                url,
                auth=(self.username, self.password),
                headers={
                    "Content-Type": "application/n-triples",
                    "Accept": "application/json"
                },
                data=rdf_data
            )
            
            if response.status_code in [200, 201, 204]:
                log.info(f"Inserted {len(items)} items into RDFox collection: {collection_name}")
            else:
                log.error(f"Failed to insert into RDFox: {response.status_code} - {response.text}")
        
        except Exception as e:
            log.error(f"Error inserting into RDFox: {e}")
            raise
    
    def search(self, collection_name: str, query_vector: List[float], limit: int = 10, **kwargs) -> Dict:
        """벡터 검색 (RDFox는 직접적인 벡터 검색을 지원하지 않으므로 메타데이터 기반 검색)"""
        # RDFox는 벡터 검색을 직접 지원하지 않으므로 빈 결과 반환
        # 실제 구현에서는 메타데이터 기반 SPARQL 쿼리를 사용해야 함
        
        log.warning("RDFox does not support direct vector search. Use metadata-based SPARQL queries instead.")
        
        return {
            "documents": [],
            "metadatas": [],
            "distances": [],
            "ids": []
        }
    
    def query(self, collection_name: str, query: str, limit: int = 10) -> Dict:
        """SPARQL 쿼리 실행 (메타데이터 기반 검색)"""
        try:
            # SPARQL 쿼리 실행
            sparql_query = f"""
            SELECT ?doc ?text ?metadata
            WHERE {{
                ?doc <http://www.w3.org/1999/02/22-rdf-syntax-ns#type> <http://example.org/Document> .
                ?doc <http://example.org/text> ?text .
                OPTIONAL {{
                    ?doc <http://example.org/metadata> ?metadata .
                }}
            }}
            LIMIT {limit}
            """
            
            results = self._execute_sparql_query(sparql_query)
            
            # 결과 변환
            documents = []
            metadatas = []
            ids = []
            
            for binding in results.get("results", {}).get("bindings", []):
                doc_uri = binding.get("doc", {}).get("value", "")
                text = binding.get("text", {}).get("value", "")
                metadata_str = binding.get("metadata", {}).get("value", "{}")
                
                doc_id = doc_uri.split("/")[-1] if "/" in doc_uri else doc_uri
                
                documents.append([text])
                metadatas.append([{"source": doc_uri}])
                ids.append([doc_id])
            
            return {
                "documents": documents,
                "metadatas": metadatas,
                "distances": [],
                "ids": ids
            }
        
        except Exception as e:
            log.error(f"Error querying RDFox: {e}")
            return {
                "documents": [],
                "metadatas": [],
                "distances": [],
                "ids": []
            }
    
    def delete(self, collection_name: str, ids: List[str]):
        """벡터 삭제"""
        try:
            for doc_id in ids:
                # SPARQL DELETE 쿼리
                delete_query = f"""
                DELETE {{
                    ?s ?p ?o
                }}
                WHERE {{
                    ?s ?p ?o .
                    FILTER (STR(?s) = "http://example.org/doc/{doc_id}")
                }}
                """
                
                self._execute_sparql_update(delete_query)
            
            log.info(f"Deleted {len(ids)} items from RDFox collection: {collection_name}")
        
        except Exception as e:
            log.error(f"Error deleting from RDFox: {e}")

