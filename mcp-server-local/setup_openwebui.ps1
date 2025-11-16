# Open WebUI에 MCP 서버를 설정하는 PowerShell 스크립트

Write-Host "Open WebUI에 MCP 서버 설정 중..." -ForegroundColor Green

# Open WebUI API 엔드포인트
$webuiUrl = "http://localhost:8080"
$mcpServerUrl = "http://127.0.0.1:8001/mcp/stream"

Write-Host "`n1. MCP 서버가 실행 중인지 확인..." -ForegroundColor Yellow
try {
    $healthCheck = Invoke-RestMethod -Uri "http://127.0.0.1:8001/health" -ErrorAction Stop
    Write-Host "✓ MCP 서버가 정상적으로 실행 중입니다." -ForegroundColor Green
    Write-Host "  서버 정보: $($healthCheck | ConvertTo-Json)" -ForegroundColor Gray
} catch {
    Write-Host "✗ MCP 서버에 연결할 수 없습니다. 서버가 실행 중인지 확인하세요." -ForegroundColor Red
    Write-Host "  실행 명령: cd mcp-server-local; .\venv\Scripts\python.exe server.py" -ForegroundColor Yellow
    exit 1
}

Write-Host "`n2. Open WebUI에 MCP 서버 추가..." -ForegroundColor Yellow
Write-Host "   관리자 토큰이 필요합니다. 브라우저에서 Open WebUI에 로그인한 후," -ForegroundColor Cyan
Write-Host "   개발자 도구(F12) → Application → Cookies에서 'token' 값을 복사하세요." -ForegroundColor Cyan
Write-Host ""

$token = Read-Host "관리자 토큰을 입력하세요"

if ([string]::IsNullOrWhiteSpace($token)) {
    Write-Host "토큰이 입력되지 않았습니다. 웹 UI를 통해 수동으로 설정하세요." -ForegroundColor Yellow
    Write-Host ""
    Write-Host "수동 설정 방법:" -ForegroundColor Cyan
    Write-Host "1. Open WebUI에 로그인 (관리자 권한)" -ForegroundColor White
    Write-Host "2. 설정(Settings) → Tool Servers로 이동" -ForegroundColor White
    Write-Host "3. 'Add Tool Server' 클릭" -ForegroundColor White
    Write-Host "4. 다음 정보 입력:" -ForegroundColor White
    Write-Host "   - Name: Local MCP Server" -ForegroundColor Gray
    Write-Host "   - URL: $mcpServerUrl" -ForegroundColor Gray
    Write-Host "   - Type: MCP" -ForegroundColor Gray
    Write-Host "   - Auth Type: None" -ForegroundColor Gray
    Write-Host "5. 'Verify' 버튼으로 연결 확인" -ForegroundColor White
    Write-Host "6. 'Save' 클릭" -ForegroundColor White
    exit 0
}

$headers = @{
    "Content-Type" = "application/json"
    "Authorization" = "Bearer $token"
}

# 기존 설정 가져오기
try {
    Write-Host "기존 Tool Server 설정 조회 중..." -ForegroundColor Gray
    $existingConfig = Invoke-RestMethod -Uri "$webuiUrl/api/v1/configs/tool_servers" -Method GET -Headers $headers -ErrorAction Stop
    
    $connections = $existingConfig.TOOL_SERVER_CONNECTIONS
    Write-Host "기존 설정: $($connections.Count)개의 서버가 등록되어 있습니다." -ForegroundColor Gray
} catch {
    Write-Host "기존 설정을 가져올 수 없습니다. 새로 생성합니다." -ForegroundColor Yellow
    $connections = @()
}

# MCP 서버가 이미 등록되어 있는지 확인
$mcpExists = $connections | Where-Object { 
    $_.type -eq "mcp" -and $_.url -eq $mcpServerUrl 
}

if ($mcpExists) {
    Write-Host "✓ MCP 서버가 이미 등록되어 있습니다." -ForegroundColor Green
    Write-Host "  서버 ID: $($mcpExists.info.id)" -ForegroundColor Gray
} else {
    # 새 MCP 서버 추가
    $newServer = @{
        url = $mcpServerUrl
        type = "mcp"
        auth_type = "none"
        info = @{
            id = "local-mcp-server"
            name = "Local MCP Server"
            description = "로컬 MCP 서버 - 시간, 계산, 문서 검색 등 제공"
        }
    }
    
    $connections += $newServer
    
    $body = @{
        TOOL_SERVER_CONNECTIONS = $connections
    } | ConvertTo-Json -Depth 10
    
    try {
        Write-Host "MCP 서버 추가 중..." -ForegroundColor Yellow
        $result = Invoke-RestMethod -Uri "$webuiUrl/api/v1/configs/tool_servers" -Method POST -Headers $headers -Body $body -ErrorAction Stop
        Write-Host "✓ MCP 서버가 성공적으로 추가되었습니다!" -ForegroundColor Green
    } catch {
        Write-Host "✗ MCP 서버 추가 실패: $($_.Exception.Message)" -ForegroundColor Red
        Write-Host "  응답: $($_.Exception.Response)" -ForegroundColor Gray
        exit 1
    }
}

Write-Host "`n3. Agentic RAG 활성화 확인..." -ForegroundColor Yellow
Write-Host "   Agentic RAG를 활성화하려면:" -ForegroundColor Cyan
Write-Host "   1. 환경 변수 설정:" -ForegroundColor White
Write-Host "      `$env:ENABLE_AGENTIC_RAG = 'true'" -ForegroundColor Gray
Write-Host "   2. 또는 웹 UI에서:" -ForegroundColor White
Write-Host "      설정 → Documents → 'Enable Agentic RAG' 활성화" -ForegroundColor Gray

Write-Host "`n✓ 설정 완료!" -ForegroundColor Green
Write-Host ""
Write-Host "다음 단계:" -ForegroundColor Cyan
Write-Host "1. MCP 서버가 실행 중인지 확인: http://127.0.0.1:8001/health" -ForegroundColor White
Write-Host "2. Open WebUI에서 채팅 시작" -ForegroundColor White
Write-Host "3. 파일을 첨부하고 질문 입력" -ForegroundColor White
Write-Host "4. Agentic RAG가 MCP 도구를 사용하는지 확인" -ForegroundColor White

