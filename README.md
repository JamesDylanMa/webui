# RAG 기반 LLM 서비스 - Open WebUI 확장

Open WebUI를 기반으로 한 고급 RAG(Retrieval Augmented Generation) 시스템입니다.

## 주요 기능

### 1. 다양한 Vector Database 지원
- **ChromaDB** (기본값, 로컬)
- **Qdrant**
- **Milvus**
- **Weaviate**
- **pgvector** (PostgreSQL)
- **Elasticsearch**
- **AWS OpenSearch**
- **Oracle 23ai**
- **S3Vector**
- **Faiss**
- **RDFox**

### 2. 청킹 전략
- **Lexical Chunking**: 토큰/문자/문장 단위 분할
- **Semantic Chunking**: 의미 기반 분할
- **Hybrid Chunking**: 의미 + 구조 기반 분할

### 3. 데이터 소스 지원
- 로컬 폴더
- AWS S3
- Azure Blob Storage

### 4. LLM 통합
- **Ollama** (로컬)
- **AWS Bedrock** (클라우드)

### 5. 고급 검색 기능
- Hybrid Search (BM25 + Vector)
- Learning to Rank
- Chain of Thought (COT)

## 빠른 시작

### 1. 환경 설정

```bash
# Anaconda 환경 활성화
conda activate webui

# 환경 변수 설정
set DATA_DIR=C:\Users\elect\webui\open-webui\backend\data
set FROM_INIT_PY=true
set VECTOR_DB=chroma
```

### 2. 문서 임베딩

```bash
# 배치 파일 실행
EMBED_DOCUMENTS.bat

# 또는 수동 실행
cd open-webui\backend
python scripts\embed_documents.py
```

### 3. 서버 실행

```bash
cd open-webui\backend
python -m uvicorn open_webui.main:app --host 0.0.0.0 --port 8080
```

### 4. 웹 UI 접속

브라우저에서 `http://localhost:8080` 접속

## 프로젝트 구조

```
webui/
├── open-webui/              # Open WebUI 메인 프로젝트
│   ├── backend/            # 백엔드
│   │   ├── open_webui/
│   │   │   ├── retrieval/  # RAG 관련 모듈
│   │   │   │   ├── chunking_strategies.py
│   │   │   │   ├── data_sources.py
│   │   │   │   └── vector/
│   │   │   │       └── dbs/
│   │   │   │           ├── faiss.py
│   │   │   │           └── rdfox.py
│   │   │   └── routers/
│   │   │       └── retrieval.py
│   │   └── scripts/        # 유틸리티 스크립트
│   │       ├── embed_documents.py
│   │       ├── embed_data_folder.py
│   │       └── embed_from_sources.py
│   └── src/                # 프론트엔드
├── data/                   # 데이터 폴더
│   └── documents/          # 임베딩할 문서들
├── RAG_사용_가이드.md      # 사용 가이드
├── 빠른_시작_가이드.md     # 빠른 시작 가이드
└── EMBED_DOCUMENTS.bat     # 문서 임베딩 배치 파일
```

## 주요 파일 설명

### 백엔드 모듈

- `chunking_strategies.py`: 청킹 전략 구현 (Semantic, Hybrid, Lexical)
- `data_sources.py`: 데이터 소스 클래스 (LocalFolderSource, S3Source, AzureBlobSource)
- `vector/dbs/faiss.py`: Faiss 벡터 DB 클라이언트
- `vector/dbs/rdfox.py`: RDFox 벡터 DB 클라이언트
- `routers/retrieval.py`: RAG API 엔드포인트

### 스크립트

- `embed_documents.py`: documents 폴더의 문서를 임베딩
- `embed_data_folder.py`: 지정된 폴더의 문서를 임베딩
- `embed_from_sources.py`: 다양한 소스에서 문서 임베딩 예제

## 설정

### 환경 변수

```bash
# Vector Database
VECTOR_DB=chroma  # chroma, qdrant, milvus, weaviate, pgvector, elasticsearch, opensearch, oracle23ai, s3vector, faiss, rdfox

# 청킹 전략
CHUNKING_STRATEGY=lexical  # lexical, semantic, hybrid
SEMANTIC_SIMILARITY_THRESHOLD=0.7
HYBRID_SEMANTIC_WEIGHT=0.6
HYBRID_LEXICAL_WEIGHT=0.4

# 임베딩 모델
RAG_EMBEDDING_ENGINE=sentence-transformers  # sentence-transformers, ollama, openai, azure_openai
RAG_EMBEDDING_MODEL=sentence-transformers/all-MiniLM-L6-v2

# 데이터 디렉토리
DATA_DIR=C:\Users\elect\webui\open-webui\backend\data
```

## 문서

- [RAG 사용 가이드](RAG_사용_가이드.md) - 상세한 사용 가이드
- [빠른 시작 가이드](빠른_시작_가이드.md) - 빠른 시작 가이드

## 라이선스

Open WebUI의 라이선스를 따릅니다.

## 기여

이슈 및 풀 리퀘스트를 환영합니다!

