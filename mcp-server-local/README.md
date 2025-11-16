# 로컬 MCP 서버

Open WebUI의 Agentic RAG와 통합할 수 있는 로컬 MCP (Model Context Protocol) 서버입니다.

## 설치

1. Python 가상환경 생성 및 활성화:
```bash
python -m venv venv
# Windows
venv\Scripts\activate
# Linux/Mac
source venv/bin/activate
```

2. 의존성 설치:
```bash
pip install -r requirements.txt
```

## 실행

### HTTP 모드 (Open WebUI 통합용)

```bash
python server.py
```

서버가 `http://127.0.0.1:8001`에서 실행됩니다.

### stdio 모드 (로컬 테스트용)

```bash
python server.py stdio
```

## 제공되는 도구

1. **get_current_time**: 현재 시간과 날짜 반환
2. **search_local_documents**: 로컬 문서 검색
3. **calculate**: 수학 계산 수행
4. **get_system_info**: 시스템 정보 반환
5. **text_analysis**: 텍스트 분석 (단어 수, 문자 수, 감정 분석)

## Open WebUI 설정

Open WebUI의 관리자 설정에서 다음 정보로 MCP 서버를 추가하세요:

- **URL**: `http://127.0.0.1:8001/mcp/stream`
- **Type**: `mcp`
- **Auth Type**: `none` (인증 없음)

또는 환경 변수로 설정:

```bash
# Windows PowerShell
$env:TOOL_SERVER_CONNECTIONS = '[{"url": "http://127.0.0.1:8001/mcp/stream", "type": "mcp", "auth_type": "none", "info": {"id": "local-mcp", "name": "Local MCP Server", "description": "로컬 MCP 서버"}}]'
```

## 테스트

서버가 실행 중일 때:

```bash
# 헬스 체크
curl http://127.0.0.1:8001/health

# 도구 목록 조회
curl http://127.0.0.1:8001/tools
```

## 참고사항

- 이 서버는 예제 구현입니다. 실제 프로덕션 환경에서는 보안 강화가 필요합니다.
- MCP의 streamable HTTP 프로토콜은 완전히 구현되지 않았을 수 있습니다. 실제 사용 시 MCP SDK의 최신 버전을 확인하세요.

