# MCP 서버 관리자 매뉴얼

## 목차
1. [빠른 시작](#빠른-시작)
2. [서버 관리](#서버-관리)
3. [Open WebUI 연동](#open-webui-연동)
4. [모니터링](#모니터링)
5. [백업 및 복구](#백업-및-복구)
6. [성능 최적화](#성능-최적화)
7. [문제 해결](#문제-해결)

## 빠른 시작

### 최소 설치 (5분)

```powershell
# 1. 저장소 클론
git clone https://github.com/JamesDylanMa/webui.git
cd webui/mcp-server-local

# 2. 가상환경 생성 및 활성화
python -m venv venv
venv\Scripts\activate

# 3. 의존성 설치
pip install -r requirements.txt

# 4. 서버 실행
python server.py
```

서버가 `http://127.0.0.1:8001`에서 실행됩니다.

### Open WebUI 연동

1. Open WebUI 관리자로 로그인
2. 설정 → Tool Servers → "Add Tool Server"
3. 다음 정보 입력:
   - **Name**: `Local MCP Server`
   - **URL**: `http://127.0.0.1:8001/mcp/stream`
   - **Type**: `MCP`
   - **Auth Type**: `None`
4. "Verify" 클릭하여 연결 확인
5. "Save" 클릭

## 서버 관리

### 서버 시작

#### Windows
```powershell
cd C:\Users\elect\webui\mcp-server-local
.\venv\Scripts\activate
python server.py
```

또는 배치 파일:
```powershell
.\start_server.bat
```

#### Linux/Mac
```bash
cd /path/to/mcp-server-local
source venv/bin/activate
python server.py
```

### 서버 중지

- **개발 모드**: 터미널에서 `Ctrl+C`
- **백그라운드 실행**: 프로세스 ID 확인 후 종료
  ```bash
  # Windows
  taskkill /PID <pid> /F
  
  # Linux/Mac
  kill <pid>
  ```

### 서버 재시작

1. 서버 중지
2. 코드 업데이트 확인
3. 서버 시작

### 자동 시작 설정

#### Windows (작업 스케줄러)

1. 작업 스케줄러 열기
2. "기본 작업 만들기"
3. 트리거: "컴퓨터 시작 시"
4. 작업: "프로그램 시작"
5. 프로그램: `C:\Users\elect\webui\mcp-server-local\venv\Scripts\python.exe`
6. 인수 추가: `server.py`
7. 시작 위치: `C:\Users\elect\webui\mcp-server-local`

#### Linux (systemd)

`/etc/systemd/system/mcp-server.service` 파일 생성:
```ini
[Unit]
Description=MCP Server
After=network.target

[Service]
Type=simple
User=your_user
WorkingDirectory=/path/to/mcp-server-local
Environment="PATH=/path/to/venv/bin"
ExecStart=/path/to/venv/bin/python server.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

서비스 활성화:
```bash
sudo systemctl daemon-reload
sudo systemctl enable mcp-server
sudo systemctl start mcp-server
```

## Open WebUI 연동

### 기본 연동

1. **MCP 서버 실행 확인**
   ```bash
   curl http://127.0.0.1:8001/health
   ```

2. **Open WebUI 설정**
   - 관리자 계정으로 로그인
   - 설정 → Tool Servers
   - "Add Tool Server" 클릭
   - MCP 서버 정보 입력

### 고급 설정

#### 인증 추가

서버에 인증을 추가하려면 `server.py` 수정:

```python
from fastapi import Header, HTTPException

API_KEY = "your_secret_key"

@app.post("/mcp/stream")
async def mcp_stream(
    request: Request,
    authorization: str = Header(None)
):
    if authorization != f"Bearer {API_KEY}":
        raise HTTPException(status_code=401, detail="Unauthorized")
    # ...
```

Open WebUI에서:
- **Auth Type**: `Bearer`
- **Key**: `your_secret_key`

#### 여러 서버 인스턴스

여러 포트에서 실행:
```bash
# 서버 1
PORT=8001 python server.py

# 서버 2
PORT=8002 python server.py
```

각각 다른 Open WebUI에 연결 가능.

### Agentic RAG 활성화

1. **환경 변수 설정**
   ```powershell
   $env:ENABLE_AGENTIC_RAG = "true"
   $env:AGENTIC_RAG_MAX_ITERATIONS = "3"
   ```

2. **웹 UI에서 활성화**
   - 설정 → Documents
   - "Enable Agentic RAG" 활성화
   - "Max Iterations" 설정

3. **테스트**
   - 채팅에서 파일 첨부
   - 질문 입력 (예: "서울 날씨 알려줘")
   - Agentic RAG가 MCP 도구 사용 확인

## 모니터링

### 헬스 체크

정기적으로 헬스 체크:
```bash
# Windows
curl http://127.0.0.1:8001/health

# PowerShell
Invoke-RestMethod -Uri "http://127.0.0.1:8001/health"
```

### 로그 확인

#### 실시간 로그
```bash
# Windows
Get-Content mcp-server.log -Wait

# Linux/Mac
tail -f mcp-server.log
```

#### 로그 레벨 변경
`server.py`에서:
```python
logging.basicConfig(level=logging.DEBUG)  # 상세 로그
```

### 성능 모니터링

#### 요청 통계
```bash
curl http://127.0.0.1:8001/stats
```

#### 리소스 사용량
```bash
# Windows
tasklist | findstr python

# Linux/Mac
ps aux | grep python
top -p $(pgrep -f "python server.py")
```

### 알림 설정

#### 서버 다운 알림

간단한 스크립트 (`check_server.ps1`):
```powershell
$response = Invoke-WebRequest -Uri "http://127.0.0.1:8001/health" -ErrorAction SilentlyContinue
if ($response.StatusCode -ne 200) {
    Write-Host "MCP Server is down!" -ForegroundColor Red
    # 알림 전송 (이메일, 슬랙 등)
}
```

작업 스케줄러에 등록하여 주기적으로 실행.

## 백업 및 복구

### 백업 항목

1. **코드 파일**
   ```bash
   # Git 저장소 사용 권장
   git add .
   git commit -m "Backup"
   git push
   ```

2. **설정 파일**
   - `server.py`
   - `requirements.txt`
   - 환경 변수 설정

3. **로그 파일**
   ```bash
   # 로그 백업
   cp mcp-server.log backups/mcp-server-$(date +%Y%m%d).log
   ```

### 복구 절차

1. **코드 복구**
   ```bash
   git clone https://github.com/JamesDylanMa/webui.git
   cd webui/mcp-server-local
   ```

2. **환경 재구성**
   ```bash
   python -m venv venv
   venv\Scripts\activate
   pip install -r requirements.txt
   ```

3. **서버 시작**
   ```bash
   python server.py
   ```

## 성능 최적화

### 1. 워커 프로세스 증가

```bash
uvicorn server:app --host 0.0.0.0 --port 8001 --workers 4
```

### 2. 캐싱 추가

자주 사용되는 데이터 캐싱:
```python
from functools import lru_cache
import time

cache = {}
CACHE_TTL = 300  # 5분

def get_cached_data(key, fetch_func):
    if key in cache:
        data, timestamp = cache[key]
        if time.time() - timestamp < CACHE_TTL:
            return data
    
    data = fetch_func()
    cache[key] = (data, time.time())
    return data
```

### 3. 연결 풀링

requests 세션 사용:
```python
import requests
session = requests.Session()

# 도구에서 사용
response = session.get(url, params=params, timeout=5)
```

### 4. 비동기 처리

외부 API 호출을 비동기로:
```python
import asyncio
import aiohttp

async def fetch_data_async(url):
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            return await response.json()
```

## 문제 해결

### 일반적인 문제

#### 1. 서버가 시작되지 않음

**증상**: 포트 충돌 또는 모듈 없음

**해결**:
```bash
# 포트 확인 및 해제
netstat -ano | findstr :8001
taskkill /PID <pid> /F

# 의존성 재설치
pip install -r requirements.txt --force-reinstall
```

#### 2. API 호출 실패

**증상**: 외부 API에서 데이터를 가져오지 못함

**해결**:
- API 키 확인: `echo $env:OPENWEATHER_API_KEY`
- 네트워크 연결 확인
- API 사용량 제한 확인
- 로그에서 에러 메시지 확인

#### 3. Open WebUI 연결 실패

**증상**: Tool Server에 연결할 수 없음

**해결**:
1. 서버 실행 확인: `curl http://127.0.0.1:8001/health`
2. URL 확인: `http://127.0.0.1:8001/mcp/stream`
3. CORS 설정 확인
4. 방화벽 확인

#### 4. 메모리 사용량 증가

**증상**: 서버가 점점 느려짐

**해결**:
- 캐시 크기 제한
- 주기적 서버 재시작
- 워커 프로세스 수 조정

### 로그 분석

#### 에러 로그 확인
```bash
# Windows
Select-String -Path mcp-server.log -Pattern "ERROR"

# Linux/Mac
grep ERROR mcp-server.log
```

#### 요청 패턴 분석
```bash
# 가장 많이 사용되는 도구 확인
grep "Tool called" mcp-server.log | awk '{print $NF}' | sort | uniq -c | sort -rn
```

## 유지보수

### 정기 작업

#### 일일
- [ ] 서버 상태 확인
- [ ] 로그 확인
- [ ] 에러 확인

#### 주간
- [ ] 로그 파일 정리
- [ ] 성능 메트릭 확인
- [ ] API 사용량 확인

#### 월간
- [ ] 의존성 업데이트 확인
- [ ] 보안 업데이트 확인
- [ ] 백업 확인
- [ ] 성능 최적화 검토

### 업데이트 절차

1. **백업**
   ```bash
   git add .
   git commit -m "Backup before update"
   git push
   ```

2. **코드 업데이트**
   ```bash
   git pull origin master
   ```

3. **의존성 업데이트**
   ```bash
   pip install -r requirements.txt --upgrade
   ```

4. **테스트**
   ```bash
   python server.py
   curl http://127.0.0.1:8001/health
   ```

5. **재시작**
   - 서버 중지
   - 서버 시작

## 체크리스트

### 초기 설정
- [ ] Python 설치 확인
- [ ] 가상환경 생성
- [ ] 의존성 설치
- [ ] 서버 시작 테스트
- [ ] 헬스 체크 테스트
- [ ] Open WebUI 연동

### 운영 준비
- [ ] API 키 설정
- [ ] 자동 시작 설정
- [ ] 로그 설정
- [ ] 모니터링 설정
- [ ] 백업 계획 수립
- [ ] 알림 설정

### 정기 점검
- [ ] 서버 상태 확인
- [ ] 로그 확인
- [ ] 성능 확인
- [ ] 보안 업데이트 확인
- [ ] 백업 확인

## 추가 리소스

- 개발자 매뉴얼: `MCP_서버_개발자_매뉴얼.md`
- 빠른 시작: `MCP_서버_빠른_시작.md`
- 도구 목록: `mcp-server-local/도구_목록.md`
- API 키 가이드: `mcp-server-local/API_KEYS.md`

