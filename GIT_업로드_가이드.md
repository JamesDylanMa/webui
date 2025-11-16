# Git 업로드 가이드

## 현재 상태

✅ Git 저장소 초기화 완료
✅ 파일 추가 완료
✅ 초기 커밋 완료

## 다음 단계: 원격 저장소에 업로드

### 1. GitHub에 새 저장소 생성

1. GitHub (https://github.com) 접속
2. 우측 상단 "+" 버튼 클릭 → "New repository"
3. 저장소 이름 입력 (예: `rag-webui-extension`)
4. 설명 입력 (선택사항)
5. Public 또는 Private 선택
6. **"Initialize this repository with a README" 체크 해제** (이미 README가 있음)
7. "Create repository" 클릭

### 2. 원격 저장소 추가

```bash
cd C:\Users\elect\webui

# GitHub 저장소 URL 사용 (예시)
git remote add origin https://github.com/YOUR_USERNAME/rag-webui-extension.git

# 또는 SSH 사용
git remote add origin git@github.com:YOUR_USERNAME/rag-webui-extension.git
```

### 3. 코드 푸시

```bash
# 기본 브랜치를 main으로 설정
git branch -M main

# 원격 저장소에 푸시
git push -u origin main
```

### 4. 인증

GitHub에 푸시할 때 인증이 필요할 수 있습니다:

**Personal Access Token 사용 (권장)**
1. GitHub → Settings → Developer settings → Personal access tokens → Tokens (classic)
2. "Generate new token" 클릭
3. 권한 선택 (repo 권한 필요)
4. 토큰 생성 후 복사
5. 푸시 시 비밀번호 대신 토큰 사용

**또는 GitHub CLI 사용**
```bash
gh auth login
git push -u origin main
```

## 대안: GitLab 사용

### 1. GitLab에 새 프로젝트 생성

1. GitLab (https://gitlab.com) 접속
2. "New project" 클릭
3. "Create blank project" 선택
4. 프로젝트 이름 입력
5. Visibility 선택
6. "Create project" 클릭

### 2. 원격 저장소 추가 및 푸시

```bash
git remote add origin https://gitlab.com/YOUR_USERNAME/rag-webui-extension.git
git branch -M main
git push -u origin main
```

## 현재 커밋된 파일

- ✅ 핵심 구현 파일 (chunking_strategies.py, data_sources.py 등)
- ✅ Vector DB 클라이언트 (faiss.py, rdfox.py)
- ✅ 임베딩 스크립트
- ✅ 설정 파일 업데이트
- ✅ 프론트엔드 UI 업데이트
- ✅ 가이드 문서
- ✅ README.md
- ✅ .gitignore

## 주의사항

1. **민감한 정보 제외**: `.env` 파일, API 키 등은 업로드하지 마세요
2. **대용량 파일**: 빌드 파일, node_modules 등은 .gitignore에 포함되어 있습니다
3. **데이터베이스**: `*.db` 파일은 제외됩니다

## 문제 해결

### 인증 오류
```bash
# GitHub Personal Access Token 설정
git config --global credential.helper store
# 푸시 시 토큰 입력
```

### 원격 저장소 변경
```bash
# 기존 원격 저장소 제거
git remote remove origin

# 새 원격 저장소 추가
git remote add origin <새_URL>
```

### 브랜치 이름 변경
```bash
# 현재 브랜치를 main으로 변경
git branch -M main
```

## 완료 확인

푸시가 성공하면 GitHub/GitLab에서 파일들을 확인할 수 있습니다!

