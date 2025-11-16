# MCP 서버 개발자/관리자 매뉴얼

## 목차
1. [개요](#개요)
2. [시스템 요구사항](#시스템-요구사항)
3. [설치 및 설정](#설치-및-설정)
4. [서버 실행](#서버-실행)
5. [도구 개발](#도구-개발)
6. [API 통합](#api-통합)
7. [문제 해결](#문제-해결)
8. [모니터링 및 로깅](#모니터링-및-로깅)

## 개요

이 MCP (Model Context Protocol) 서버는 Open WebUI의 Agentic RAG 기능과 통합하여 다양한 외부 정보를 탐색하고 처리할 수 있는 도구들을 제공합니다.

### 주요 기능
- 17개의 다양한 도구 제공
- HTTP 기반 RESTful API
- MCP 프로토콜 지원
- 외부 API 통합 (날씨, 뉴스, 환율 등)
- 확장 가능한 아키텍처

## 시스템 요구사항

### 필수 요구사항
- Python 3.8 이상
- pip (Python 패키지 관리자)
- 인터넷 연결 (외부 API 사용 시)

### 권장 사양
- Python 3.10 이상
- 최소 512MB RAM
- 100MB 이상 디스크 공간

## 설치 및 설정

### 1. 저장소 클론

```bash
git clone https://github.com/JamesDylanMa/webui.git
cd webui/mcp-server-local
```

### 2. 가상환경 생성 및 활성화

#### Windows
```powershell
python -m venv venv
venv\Scripts\activate
```

#### Linux/Mac
```bash
python3 -m venv venv
source venv/bin/activate
```

### 3. 의존성 설치

```bash
pip install -r requirements.txt
```

필요한 패키지:
- `fastapi>=0.104.0` - 웹 프레임워크
- `uvicorn>=0.24.0` - ASGI 서버
- `pydantic>=2.0.0` - 데이터 검증
- `requests>=2.31.0` - HTTP 클라이언트
- `pytz>=2023.3` - 시간대 처리

### 4. 환경 변수 설정 (선택사항)

#### Windows PowerShell
```powershell
# 날씨 API 키
$env:OPENWEATHER_API_KEY = "your_api_key_here"

# 뉴스 API 키
$env:NEWS_API_KEY = "your_api_key_here"
```

#### Linux/Mac
```bash
export OPENWEATHER_API_KEY="your_api_key_here"
export NEWS_API_KEY="your_api_key_here"
```

#### 영구 설정 (Windows)
1. 시스템 속성 → 고급 → 환경 변수
2. 시스템 변수에서 "새로 만들기"
3. 변수 이름과 값 입력

#### 영구 설정 (Linux/Mac)
`~/.bashrc` 또는 `~/.zshrc`에 추가:
```bash
export OPENWEATHER_API_KEY="your_api_key_here"
export NEWS_API_KEY="your_api_key_here"
```

## 서버 실행

### 개발 모드 실행

#### Windows
```powershell
cd mcp-server-local
.\venv\Scripts\python.exe server.py
```

또는 배치 파일 사용:
```powershell
.\start_server.bat
```

#### Linux/Mac
```bash
cd mcp-server-local
source venv/bin/activate
python server.py
```

### 프로덕션 모드 실행

#### Windows
```powershell
$env:PORT = "8001"
.\venv\Scripts\uvicorn.exe server:app --host 0.0.0.0 --port 8001 --workers 4
```

#### Linux/Mac
```bash
uvicorn server:app --host 0.0.0.0 --port 8001 --workers 4
```

### 서비스로 실행 (Linux)

#### systemd 서비스 파일 생성

`/etc/systemd/system/mcp-server.service`:
```ini
[Unit]
Description=MCP Server
After=network.target

[Service]
Type=simple
User=your_user
WorkingDirectory=/path/to/webui/mcp-server-local
Environment="PATH=/path/to/venv/bin"
ExecStart=/path/to/venv/bin/python server.py
Restart=always

[Install]
WantedBy=multi-user.target
```

서비스 시작:
```bash
sudo systemctl daemon-reload
sudo systemctl enable mcp-server
sudo systemctl start mcp-server
sudo systemctl status mcp-server
```

### Docker로 실행

#### Dockerfile 생성

```dockerfile
FROM python:3.10-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY server.py .

EXPOSE 8001

CMD ["python", "server.py"]
```

#### Docker 실행

```bash
docker build -t mcp-server .
docker run -d -p 8001:8001 \
  -e OPENWEATHER_API_KEY=your_key \
  -e NEWS_API_KEY=your_key \
  --name mcp-server mcp-server
```

## 도구 개발

### 새 도구 추가하기

#### 1. 도구 정의 추가

`server.py`의 `get_tools_list()` 함수에 도구 정의 추가:

```python
{
    "name": "your_tool_name",
    "description": "도구 설명",
    "parameters": {
        "type": "object",
        "properties": {
            "param1": {
                "type": "string",
                "description": "파라미터 설명"
            }
        },
        "required": ["param1"]
    }
}
```

#### 2. 실행 로직 추가

`execute_tool()` 함수에 처리 로직 추가:

```python
elif name == "your_tool_name":
    param1 = arguments.get("param1", "")
    
    # 도구 로직 구현
    result = {
        "result": "결과 데이터"
    }
    
    return result
```

#### 3. 테스트

```bash
# 도구 목록 확인
curl http://127.0.0.1:8001/tools

# 도구 호출 테스트
curl -X POST http://127.0.0.1:8001/tools/call \
  -H "Content-Type: application/json" \
  -d '{"name": "your_tool_name", "arguments": {"param1": "value"}}'
```

### 도구 개발 가이드라인

1. **에러 처리**: 모든 도구는 try-except로 감싸서 에러 처리
2. **로깅**: 중요한 작업은 logger로 기록
3. **타임아웃**: 외부 API 호출 시 timeout 설정 (기본 5초)
4. **기본값**: API 실패 시 예제 데이터 반환
5. **문서화**: 도구 설명과 파라미터를 명확히 작성

## API 통합

### 지원하는 외부 API

#### 무료 API (API 키 불필요)
- **ExchangeRate-API**: 환율 정보
- **CoinGecko**: 암호화폐 가격
- **Wikipedia REST API**: 위키피디아 검색
- **MyMemory Translation**: 번역 (제한 있음)
- **ip-api.com**: IP 위치 조회
- **Yahoo Finance**: 주식 가격

#### 유료/제한적 API (API 키 필요)
- **OpenWeatherMap**: 날씨 정보
  - 무료 플랜: 일일 60회 호출
  - 가입: https://openweathermap.org/api
  
- **NewsAPI**: 뉴스 검색
  - 무료 플랜: 일일 100회 호출
  - 가입: https://newsapi.org/

### API 키 발급 방법

#### OpenWeatherMap
1. https://openweathermap.org/api 접속
2. "Sign Up" 클릭하여 계정 생성
3. API Keys 메뉴에서 키 복사
4. 환경 변수에 설정: `OPENWEATHER_API_KEY`

#### NewsAPI
1. https://newsapi.org/ 접속
2. "Get API Key" 클릭하여 계정 생성
3. 대시보드에서 API 키 복사
4. 환경 변수에 설정: `NEWS_API_KEY`

## 문제 해결

### 일반적인 문제

#### 1. 서버가 시작되지 않음

**증상**: 포트가 이미 사용 중이거나 모듈을 찾을 수 없음

**해결책**:
```bash
# 포트 확인
netstat -ano | findstr :8001  # Windows
lsof -i :8001                 # Linux/Mac

# 다른 포트 사용
python server.py  # 기본 포트 8001
# 또는 코드에서 포트 변경
```

#### 2. API 호출 실패

**증상**: 외부 API에서 데이터를 가져오지 못함

**해결책**:
- 인터넷 연결 확인
- API 키가 올바르게 설정되었는지 확인
- API 사용량 제한 확인
- 방화벽 설정 확인

#### 3. MCP 프로토콜 오류

**증상**: Open WebUI에서 MCP 서버에 연결할 수 없음

**해결책**:
- 서버가 실행 중인지 확인: `curl http://127.0.0.1:8001/health`
- URL이 정확한지 확인: `http://127.0.0.1:8001/mcp/stream`
- CORS 설정 확인
- 로그 확인

### 디버깅

#### 로그 레벨 변경

`server.py`에서 로그 레벨 조정:
```python
logging.basicConfig(level=logging.DEBUG)  # 상세 로그
logging.basicConfig(level=logging.INFO)   # 일반 로그
logging.basicConfig(level=logging.WARNING) # 경고만
```

#### 요청/응답 로깅

FastAPI 미들웨어 추가:
```python
@app.middleware("http")
async def log_requests(request: Request, call_next):
    logger.info(f"Request: {request.method} {request.url}")
    response = await call_next(request)
    logger.info(f"Response: {response.status_code}")
    return response
```

## 모니터링 및 로깅

### 헬스 체크

```bash
curl http://127.0.0.1:8001/health
```

응답:
```json
{
  "status": "healthy",
  "server": "local-mcp-server"
}
```

### 도구 목록 확인

```bash
curl http://127.0.0.1:8001/tools
```

### 로그 파일 설정

#### Windows
```powershell
python server.py > mcp-server.log 2>&1
```

#### Linux/Mac
```bash
python server.py > mcp-server.log 2>&1 &
```

또는 systemd journal 사용:
```bash
sudo journalctl -u mcp-server -f
```

### 성능 모니터링

#### 요청 수 모니터링
```python
from collections import defaultdict
request_count = defaultdict(int)

@app.middleware("http")
async def count_requests(request: Request, call_next):
    request_count[request.url.path] += 1
    return await call_next(request)

@app.get("/stats")
async def get_stats():
    return dict(request_count)
```

## 보안 고려사항

### 1. API 키 보안
- API 키를 코드에 하드코딩하지 않음
- 환경 변수 사용
- Git에 API 키 커밋하지 않음

### 2. CORS 설정
프로덕션 환경에서는 특정 도메인만 허용:
```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://your-domain.com"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

### 3. Rate Limiting
외부 API 호출 제한:
```python
from slowapi import Limiter
limiter = Limiter(key_func=get_remote_address)

@app.post("/tools/call")
@limiter.limit("10/minute")
async def call_tool_http(request: Request):
    # ...
```

### 4. 입력 검증
Pydantic 모델 사용:
```python
from pydantic import BaseModel, validator

class ToolCallRequest(BaseModel):
    name: str
    arguments: dict
    
    @validator('name')
    def validate_name(cls, v):
        if v not in allowed_tools:
            raise ValueError('Invalid tool name')
        return v
```

## 배포 체크리스트

- [ ] 모든 의존성 설치 확인
- [ ] 환경 변수 설정 확인
- [ ] API 키 설정 확인
- [ ] 서버 시작 테스트
- [ ] 헬스 체크 테스트
- [ ] 도구 호출 테스트
- [ ] 로그 설정 확인
- [ ] 방화벽 설정 확인
- [ ] 백업 계획 수립
- [ ] 모니터링 설정

## 추가 리소스

- [FastAPI 문서](https://fastapi.tiangolo.com/)
- [MCP 프로토콜 사양](https://modelcontextprotocol.io/)
- [Open WebUI 문서](https://docs.openwebui.com/)
- 프로젝트 GitHub: https://github.com/JamesDylanMa/webui

## 지원 및 문의

문제가 발생하거나 질문이 있으면:
1. GitHub Issues에 등록
2. 로그 파일 확인
3. 문서 재검토

