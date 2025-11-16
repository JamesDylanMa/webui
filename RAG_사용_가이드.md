# RAG 구성 및 사용 가이드

## 📋 목차
1. [문서 준비 및 임베딩](#1-문서-준비-및-임베딩)
2. [RAG 설정](#2-rag-설정)
3. [RAG 사용 방법](#3-rag-사용-방법)
4. [문제 해결](#4-문제-해결)

---

## 1. 문서 준비 및 임베딩

### 방법 1: 스크립트를 사용한 일괄 임베딩 (권장)

#### 1-1. 문서 폴더에 파일 추가

```bash
# 문서를 저장할 폴더
C:\Users\elect\webui\open-webui\backend\data\documents
```

이 폴더에 다음 형식의 문서를 추가하세요:
- PDF 파일 (`.pdf`)
- 텍스트 파일 (`.txt`, `.md`)
- Word 문서 (`.docx`)
- 기타 지원되는 형식

#### 1-2. 배치 파일 실행

```bash
# 프로젝트 루트에서 실행
EMBED_DOCUMENTS.bat
```

또는 수동으로:

```bash
# Anaconda Prompt에서
conda activate webui
cd C:\Users\elect\webui\open-webui\backend

# 환경 변수 설정
set DATA_DIR=C:\Users\elect\webui\open-webui\backend\data
set FROM_INIT_PY=true
set VECTOR_DB=chroma

# 스크립트 실행
python scripts\embed_documents.py
```

#### 1-3. 임베딩 결과 확인

스크립트 실행 후 다음과 같은 출력을 확인할 수 있습니다:

```
Found 5 files in C:\Users\elect\webui\open-webui\backend\data\documents
Loading documents from: ...
Using Vector DB: chroma
Collection: documents
Chunking strategy: lexical
Chunk size: 1000, Overlap: 100
--------------------------------------------------
Embedding Statistics:
  Total documents: 5
  Total chunks: 23
  Success: 5
  Failed: 0
--------------------------------------------------
Done! Documents are now embedded in ChromaDB.
```

### 방법 2: 웹 UI를 통한 문서 업로드

#### 2-1. 웹 UI 접속

1. 브라우저에서 `http://localhost:8080` 접속
2. 로그인 (관리자 계정)

#### 2-2. 문서 업로드

1. 좌측 메뉴에서 **"Knowledge"** 또는 **"Knowledge Base"** 클릭
2. **"Upload"** 또는 **"Add Document"** 버튼 클릭
3. 파일 선택 및 업로드
4. 업로드된 문서는 자동으로 임베딩됩니다

#### 2-3. Knowledge Base 확인

- 업로드된 문서 목록 확인
- 각 문서의 임베딩 상태 확인
- 필요시 재인덱싱 (Reindex) 수행

---

## 2. RAG 설정

### 2-1. 관리자 설정 페이지 접속

1. 웹 UI에서 좌측 메뉴 **"설정"** 클릭
2. **"문서"** (Documents) 탭 선택

### 2-2. Vector Database 선택

**Vector Database** 드롭다운에서 선택:
- **ChromaDB** (기본값, 로컬 사용)
- Qdrant
- Milvus
- Weaviate
- pgvector (PostgreSQL)
- Elasticsearch
- AWS OpenSearch
- Oracle 23ai
- S3Vector
- Faiss
- RDFox

> **참고**: Vector DB 변경 후 서버 재시작이 필요할 수 있습니다.

### 2-3. 청킹 전략 설정

**Chunking Strategy** 드롭다운에서 선택:

#### Lexical (기본값)
- 토큰/문자/문장 단위로 분할
- 빠르고 단순한 방식

#### Semantic
- 의미 기반 분할
- 유사도 임계값 설정 가능 (`SEMANTIC_SIMILARITY_THRESHOLD`: 기본 0.7)

#### Hybrid
- 의미 + 구조 기반 분할
- 가중치 조정 가능:
  - `HYBRID_SEMANTIC_WEIGHT`: 기본 0.6
  - `HYBRID_LEXICAL_WEIGHT`: 기본 0.4

### 2-4. 청킹 파라미터 설정

- **Chunk Size**: 청크 크기 (기본: 1000)
- **Chunk Overlap**: 청크 간 겹치는 부분 (기본: 100)

### 2-5. 임베딩 모델 설정

**Embedding Engine** 선택:
- **sentence-transformers** (로컬, 기본값)
- **ollama** (로컬 Ollama 서버)
- **openai** (OpenAI API)
- **azure_openai** (Azure OpenAI)

**Embedding Model** 선택:
- sentence-transformers: `all-MiniLM-L6-v2` (기본값)
- ollama: `nomic-embed-text` 등
- openai: `text-embedding-ada-002` 등

### 2-6. Hybrid Search 설정

- **Enable Hybrid Search**: BM25 + Vector 검색 활성화
- **Top K**: 검색 결과 개수 (기본: 4)
- **Top K Reranker**: 리랭킹 후 결과 개수 (기본: 4)
- **Relevance Threshold**: 관련성 임계값
- **BM25 Weight**: BM25 가중치

### 2-7. 설정 저장

모든 설정을 변경한 후 **"Save"** 버튼 클릭

---

## 3. RAG 사용 방법

### 3-1. 채팅에서 RAG 사용

1. 웹 UI에서 새 채팅 시작
2. 채팅 입력창에 질문 입력
3. RAG가 자동으로 관련 문서를 검색하여 컨텍스트로 사용

### 3-2. Knowledge Base 검색

1. **Knowledge Base** 메뉴 접속
2. 검색창에 키워드 입력
3. 관련 문서 및 청크 확인

### 3-3. API를 통한 검색

```bash
curl -X POST "http://localhost:8080/api/v1/retrieval/query/doc" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "collection_name": "documents",
    "query": "검색할 질문",
    "k": 5
  }'
```

---

## 4. 문제 해결

### 4-1. 문서가 임베딩되지 않음

**확인 사항:**
1. 문서 폴더 경로 확인: `C:\Users\elect\webui\open-webui\backend\data\documents`
2. 파일 형식이 지원되는지 확인
3. 스크립트 실행 시 에러 메시지 확인

**해결 방법:**
```bash
# 문서 폴더 확인
dir C:\Users\elect\webui\open-webui\backend\data\documents

# 스크립트 재실행
python scripts\embed_documents.py
```

### 4-2. Vector DB 연결 오류

**확인 사항:**
1. Vector DB 설정이 올바른지 확인
2. ChromaDB의 경우 데이터 폴더 권한 확인

**해결 방법:**
```bash
# ChromaDB 데이터 폴더 확인
dir C:\Users\elect\webui\open-webui\backend\data\vector_db

# 필요시 폴더 생성
mkdir C:\Users\elect\webui\open-webui\backend\data\vector_db
```

### 4-3. 임베딩 모델 로드 실패

**확인 사항:**
1. 인터넷 연결 확인 (모델 다운로드 필요)
2. 디스크 공간 확인

**해결 방법:**
```bash
# sentence-transformers 모델 수동 다운로드
python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('sentence-transformers/all-MiniLM-L6-v2')"
```

---

## 5. 고급 기능

### 5-1. AWS S3에서 문서 임베딩

```bash
# API 사용
curl -X POST "http://localhost:8080/api/v1/retrieval/embed/from-source" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "source_type": "s3",
    "collection_name": "s3_documents",
    "bucket_name": "your-bucket",
    "prefix": "documents/",
    "aws_access_key_id": "YOUR_KEY",
    "aws_secret_access_key": "YOUR_SECRET",
    "region_name": "us-east-1"
  }'
```

### 5-2. Azure Blob Storage에서 문서 임베딩

```bash
curl -X POST "http://localhost:8080/api/v1/retrieval/embed/from-source" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "source_type": "azure",
    "collection_name": "azure_documents",
    "container_name": "documents",
    "account_name": "your_account",
    "account_key": "YOUR_KEY"
  }'
```

---

## 6. 체크리스트

### 초기 설정
- [ ] 문서 폴더에 파일 추가
- [ ] 스크립트 실행하여 임베딩
- [ ] 임베딩 결과 확인

### RAG 설정
- [ ] Vector Database 선택
- [ ] 청킹 전략 선택
- [ ] 청킹 파라미터 설정
- [ ] 임베딩 모델 선택
- [ ] Hybrid Search 설정 (선택사항)
- [ ] 설정 저장

### 사용
- [ ] 채팅에서 RAG 테스트
- [ ] Knowledge Base 검색 테스트
- [ ] API 검색 테스트 (선택사항)

---

## 7. 유용한 명령어

### 문서 폴더 확인
```bash
dir C:\Users\elect\webui\open-webui\backend\data\documents
```

### ChromaDB 데이터 확인
```bash
dir C:\Users\elect\webui\open-webui\backend\data\vector_db
```

### 임베딩 스크립트 실행
```bash
cd C:\Users\elect\webui\open-webui\backend
set DATA_DIR=C:\Users\elect\webui\open-webui\backend\data
set FROM_INIT_PY=true
set VECTOR_DB=chroma
python scripts\embed_documents.py
```

---

**문제가 발생하면 서버 로그를 확인하거나 이슈를 등록하세요!**

