# MCP 서버 로컬 설정 가이드

## 개요

MCP (Model Context Protocol) 서버를 로컬에 설정하여 Open WebUI의 Agentic RAG 기능과 통합하는 방법을 설명합니다.

## 1. 로컬 MCP 서버 설치

### 1.1 디렉토리 생성 및 이동

```bash
cd C:\Users\elect\webui
mkdir mcp-server-local
cd mcp-server-local
```

### 1.2 가상환경 생성 및 활성화

```powershell
# 가상환경 생성
python -m venv venv

# 가상환경 활성화
venv\Scripts\activate
```

### 1.3 의존성 설치

```bash
pip install fastapi uvicorn mcp pydantic
```

또는 requirements.txt 사용:

```bash
pip install -r requirements.txt
```

## 2. MCP 서버 실행

### 2.1 HTTP 모드로 실행 (Open WebUI 통합용)

```bash
python server.py
```

서버가 `http://127.0.0.1:8001`에서 실행됩니다.

### 2.2 Windows 배치 파일로 실행

```bash
start_server.bat
```

## 3. Open WebUI에 MCP 서버 연결

### 3.1 웹 UI를 통한 설정

1. Open WebUI에 로그인 (관리자 권한 필요)
2. 설정(Settings) → Tool Servers로 이동
3. "Add Tool Server" 클릭
4. 다음 정보 입력:
   - **Name**: `Local MCP Server`
   - **URL**: `http://127.0.0.1:8001/mcp/stream`
   - **Type**: `MCP`
   - **Auth Type**: `None`
   - **Description**: `로컬 MCP 서버`

5. "Verify" 버튼을 클릭하여 연결 확인
6. "Save" 클릭

### 3.2 환경 변수로 설정

```powershell
# Windows PowerShell
$env:TOOL_SERVER_CONNECTIONS = @'
[
  {
    "url": "http://127.0.0.1:8001/mcp/stream",
    "type": "mcp",
    "auth_type": "none",
    "info": {
      "id": "local-mcp-server",
      "name": "Local MCP Server",
      "description": "로컬 MCP 서버 - 시간, 계산, 문서 검색 등 제공"
    }
  }
]
'@
```

### 3.3 설정 파일로 저장 (영구 설정)

Open WebUI의 설정 API를 사용하여 저장:

```powershell
# Open WebUI가 실행 중일 때
$headers = @{
    "Content-Type" = "application/json"
    "Authorization" = "Bearer YOUR_ADMIN_TOKEN"
}

$body = @{
    TOOL_SERVER_CONNECTIONS = @(
        @{
            url = "http://127.0.0.1:8001/mcp/stream"
            type = "mcp"
            auth_type = "none"
            info = @{
                id = "local-mcp-server"
                name = "Local MCP Server"
                description = "로컬 MCP 서버"
            }
        }
    )
} | ConvertTo-Json -Depth 10

Invoke-RestMethod -Uri "http://localhost:8080/api/v1/configs/tool_servers" -Method POST -Headers $headers -Body $body
```

## 4. Agentic RAG에서 MCP 서버 사용

### 4.1 Agentic RAG 활성화

```powershell
$env:ENABLE_AGENTIC_RAG = "true"
$env:AGENTIC_RAG_MAX_ITERATIONS = "3"
```

또는 웹 UI에서:
- 설정 → Documents → "Enable Agentic RAG" 활성화

### 4.2 사용 방법

1. 채팅에서 파일을 첨부하고 질문을 입력
2. Agentic RAG가 자동으로:
   - 쿼리를 분석
   - 필요한 경우 MCP 서버의 도구를 사용하여 추가 정보 수집
   - 문서 검색 및 답변 생성
   - 답변 검증 및 필요시 재처리

## 5. 제공되는 도구

로컬 MCP 서버는 다음 도구를 제공합니다:

### 5.1 get_current_time
현재 시간과 날짜를 반환합니다.

**예시 사용**:
- "지금 몇 시야?"
- "현재 시간 알려줘"

### 5.2 search_local_documents
로컬 문서를 검색합니다.

**예시 사용**:
- "문서에서 'RAG' 관련 내용 찾아줘"
- "벡터 데이터베이스에 대해 설명하는 문서 찾기"

### 5.3 calculate
수학 계산을 수행합니다.

**예시 사용**:
- "2 + 2 계산해줘"
- "sqrt(16) 계산"

### 5.4 get_system_info
시스템 정보를 반환합니다.

**예시 사용**:
- "시스템 정보 알려줘"
- "현재 환경 정보 확인"

### 5.5 text_analysis
텍스트를 분석합니다.

**예시 사용**:
- "이 텍스트의 단어 수 세어줘"
- "텍스트 감정 분석해줘"

## 6. 테스트

### 6.1 서버 상태 확인

```powershell
# 헬스 체크
Invoke-RestMethod -Uri "http://127.0.0.1:8001/health"

# 도구 목록 조회
Invoke-RestMethod -Uri "http://127.0.0.1:8001/tools"
```

### 6.2 Open WebUI에서 테스트

1. MCP 서버가 실행 중인지 확인
2. Open WebUI에서 채팅 시작
3. 파일 첨부 후 질문 입력
4. Agentic RAG가 MCP 도구를 사용하는지 확인

## 7. 문제 해결

### 7.1 서버가 시작되지 않음

- Python 가상환경이 활성화되어 있는지 확인
- 필요한 패키지가 설치되어 있는지 확인: `pip list | findstr mcp`

### 7.2 Open WebUI에서 연결 실패

- MCP 서버가 실행 중인지 확인: `http://127.0.0.1:8001/health`
- URL이 정확한지 확인: `http://127.0.0.1:8001/mcp/stream`
- 방화벽이 포트 8001을 차단하지 않는지 확인

### 7.3 Agentic RAG가 MCP 도구를 사용하지 않음

- Agentic RAG가 활성화되어 있는지 확인
- MCP 서버가 Tool Servers에 등록되어 있는지 확인
- 채팅에서 파일이 첨부되어 있는지 확인 (Agentic RAG는 파일이 있을 때만 작동)

## 8. 고급 설정

### 8.1 인증 추가

보안이 필요한 경우 Bearer 토큰 인증을 추가할 수 있습니다:

```python
# server.py 수정
@app.post("/mcp/stream")
async def mcp_stream(request: Request):
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Unauthorized")
    # ... 나머지 코드
```

### 8.2 커스텀 도구 추가

`server.py`의 `list_tools()` 함수에 새 도구를 추가하고, `call_tool()` 함수에 처리 로직을 추가하세요.

## 9. 참고 자료

- [MCP 공식 문서](https://modelcontextprotocol.io/)
- [Open WebUI MCP 문서](https://docs.openwebui.com/features/mcp)
- 프로젝트 GitHub: `https://github.com/JamesDylanMa/webui`

