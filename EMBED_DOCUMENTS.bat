@echo off
REM documents 폴더의 문서들을 ChromaDB에 임베딩

echo ========================================
echo 문서 임베딩 (ChromaDB)
echo ========================================

REM 환경 변수 설정
set DATA_DIR=C:\Users\elect\webui\open-webui\backend\data
set FROM_INIT_PY=true
set VECTOR_DB=chroma

REM webui Python 경로
set WEBUI_PYTHON=C:\Users\elect\.conda\envs\webui\python.exe

REM 백엔드 디렉토리로 이동
cd /d "%~dp0open-webui\backend"

echo Python: %WEBUI_PYTHON%
echo Data Dir: %DATA_DIR%
echo Vector DB: %VECTOR_DB%
echo Documents: %DATA_DIR%\documents
echo.

REM 문서 임베딩 실행
"%WEBUI_PYTHON%" scripts\embed_documents.py

pause

