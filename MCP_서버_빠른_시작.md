# MCP 서버 빠른 시작 가이드

## ✅ 현재 상태

MCP 서버가 `http://127.0.0.1:8001`에서 실행 중입니다!

## 📋 제공되는 도구

1. **get_current_time** - 현재 시간 반환
2. **search_local_documents** - 로컬 문서 검색
3. **calculate** - 수학 계산
4. **get_system_info** - 시스템 정보
5. **text_analysis** - 텍스트 분석

## 🔧 Open WebUI에 연결하기

### 방법 1: 웹 UI를 통한 설정 (권장)

1. Open WebUI에 로그인 (관리자 권한 필요)
2. **설정(Settings)** → **Tool Servers**로 이동
3. **"Add Tool Server"** 클릭
4. 다음 정보 입력:
   ```
   Name: Local MCP Server
   URL: http://127.0.0.1:8001/mcp/stream
   Type: MCP
   Auth Type: None
   Description: 로컬 MCP 서버
   ```
5. **"Verify"** 버튼 클릭하여 연결 확인
6. **"Save"** 클릭

### 방법 2: PowerShell 스크립트 사용

```powershell
cd C:\Users\elect\webui\mcp-server-local
.\setup_openwebui.ps1
```

스크립트 실행 시 관리자 토큰을 입력하라는 메시지가 나타납니다.
토큰은 브라우저에서 Open WebUI에 로그인한 후, 개발자 도구(F12) → Application → Cookies에서 'token' 값을 복사하면 됩니다.

### 방법 3: 환경 변수로 설정

```powershell
$env:TOOL_SERVER_CONNECTIONS = @'
[
  {
    "url": "http://127.0.0.1:8001/mcp/stream",
    "type": "mcp",
    "auth_type": "none",
    "info": {
      "id": "local-mcp-server",
      "name": "Local MCP Server",
      "description": "로컬 MCP 서버"
    }
  }
]
'@
```

## 🚀 Agentic RAG 활성화

### 환경 변수로 활성화

```powershell
$env:ENABLE_AGENTIC_RAG = "true"
$env:AGENTIC_RAG_MAX_ITERATIONS = "3"
```

### 웹 UI에서 활성화

1. **설정** → **Documents**로 이동
2. **"Enable Agentic RAG"** 옵션 활성화
3. **"Max Iterations"** 설정 (기본값: 3)

## 🧪 테스트

### 1. 서버 상태 확인

```powershell
# 헬스 체크
Invoke-RestMethod -Uri "http://127.0.0.1:8001/health"

# 도구 목록 조회
Invoke-RestMethod -Uri "http://127.0.0.1:8001/tools"
```

### 2. Open WebUI에서 테스트

1. 채팅 시작
2. 파일 첨부 (PDF, TXT 등)
3. 질문 입력 (예: "현재 시간 알려줘", "2+2 계산해줘")
4. Agentic RAG가 MCP 도구를 사용하는지 확인

## 📝 서버 관리

### 서버 시작

```powershell
cd C:\Users\elect\webui\mcp-server-local
.\venv\Scripts\activate
python server.py
```

또는 배치 파일 사용:

```powershell
.\start_server.bat
```

### 서버 중지

서버가 실행 중인 터미널에서 `Ctrl+C`를 누르세요.

## 🔍 문제 해결

### 서버가 시작되지 않음

1. 가상환경이 활성화되어 있는지 확인
2. 의존성이 설치되어 있는지 확인: `pip list | findstr fastapi`

### Open WebUI에서 연결 실패

1. MCP 서버가 실행 중인지 확인: `http://127.0.0.1:8001/health`
2. URL이 정확한지 확인: `http://127.0.0.1:8001/mcp/stream`
3. 방화벽이 포트 8001을 차단하지 않는지 확인

### Agentic RAG가 MCP 도구를 사용하지 않음

1. Agentic RAG가 활성화되어 있는지 확인
2. MCP 서버가 Tool Servers에 등록되어 있는지 확인
3. 채팅에서 파일이 첨부되어 있는지 확인 (Agentic RAG는 파일이 있을 때만 작동)

## 📚 추가 정보

- 상세 가이드: `MCP_서버_설정_가이드.md`
- 서버 코드: `mcp-server-local/server.py`
- README: `mcp-server-local/README.md`

