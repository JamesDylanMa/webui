# API 키 설정 가이드

일부 MCP 도구는 실제 데이터를 가져오기 위해 API 키가 필요합니다. API 키를 설정하면 더 정확한 정보를 받을 수 있습니다.

## 환경 변수 설정

### Windows PowerShell

```powershell
# 날씨 정보 (OpenWeatherMap)
$env:OPENWEATHER_API_KEY = "your_api_key_here"

# 뉴스 검색 (NewsAPI)
$env:NEWS_API_KEY = "your_api_key_here"
```

### 영구 설정 (Windows)

1. 시스템 환경 변수 설정:
   - Win + R → `sysdm.cpl` 입력
   - "고급" 탭 → "환경 변수" 클릭
   - "시스템 변수"에서 "새로 만들기" 클릭
   - 변수 이름: `OPENWEATHER_API_KEY`
   - 변수 값: API 키 입력

## 무료 API 키 받기

### 1. OpenWeatherMap (날씨 정보)
- 웹사이트: https://openweathermap.org/api
- 가입 후 무료 플랜 사용 가능
- 일일 60회 호출 제한 (무료)

### 2. NewsAPI (뉴스 검색)
- 웹사이트: https://newsapi.org/
- 가입 후 개발자 키 발급
- 일일 100회 호출 제한 (무료)

### 3. ExchangeRate-API (환율)
- 웹사이트: https://www.exchangerate-api.com/
- API 키 없이도 사용 가능 (무료)
- 월 1,500회 호출 제한

### 4. CoinGecko (암호화폐)
- 웹사이트: https://www.coingecko.com/en/api
- API 키 없이도 사용 가능 (무료)
- 분당 10-50회 호출 제한

## API 키 없이 사용 가능한 도구

다음 도구들은 API 키 없이도 작동합니다:
- ✅ 환율 정보 (ExchangeRate-API)
- ✅ 암호화폐 가격 (CoinGecko)
- ✅ 위키피디아 검색
- ✅ 번역 (MyMemory - 제한 있음)
- ✅ IP 조회
- ✅ 주식 가격 (Yahoo Finance)
- ✅ 시간 정보
- ✅ 계산
- ✅ 텍스트 분석
- ✅ 명언/농담/랜덤 사실

## 서버 재시작

API 키를 설정한 후에는 MCP 서버를 재시작해야 합니다:

```powershell
# 서버 중지 (Ctrl+C)
# 서버 재시작
cd C:\Users\elect\webui\mcp-server-local
.\venv\Scripts\python.exe server.py
```

