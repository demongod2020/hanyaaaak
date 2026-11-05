# 본초록 GitHub Actions와 Docker Hub 자동 배포

## 구현 내용

프로젝트 경로: `C:\Users\myshin\Documents\codex make`

원격 저장소: https://github.com/demongod2020/hanyaaaak

워크플로: `.github/workflows/ci.yml` (Bonchorok Docker CI)

1. master 또는 main 브랜치에 push하면 Ubuntu 24.04에서 소스를 받는다.
2. Dockerfile로 Python 3.12 이미지를 빌드한다. requirements.txt의 기존 고정 버전을 설치하고 pip check로 의존성을 확인한다.
3. 빌드 도중 일반 사용자 권한으로 FastAPI를 import하여 601개 약재 로딩, ID 중복, 괴화 항목, 주요 화면 파일을 검사한다. 실패하면 이미지 빌드가 중단된다.
4. 실제 컨테이너를 실행하고 healthy 상태를 기다린다. smoke_test.py로 데이터, 화면 파일, API 문서와 비공개 파일 차단을 검사하고 호스트 공개 포트로도 요청한다.
5. 검사에 성공한 동일한 이미지를 Docker Hub에 올린다. 재빌드한 다른 이미지를 업로드하지 않는다.
6. 성공·실패와 관계없이 컨테이너 로그를 남기고 테스트 컨테이너를 제거한다.

본초록은 AI 추론 앱이 아니다. 모델 파일, 모델 다운로드, GPU, 얼굴 분석 라이브러리는 필요하지 않다. 원래 요청의 모델 로딩 검증은 이 프로젝트에 맞게 **약재 JSON과 FastAPI 앱 로딩 검증**으로 적용했다. 기존 검색, 상세 화면, 이미지와 북마크 코드는 바꾸지 않았다. HTTP 자동 검사가 브라우저 상호작용 전체를 검증하는 것은 아니므로 화면 확인도 별도로 한다.

Pull Request에서는 빌드와 검사만 실행하고 로그인이나 업로드는 하지 않는다. Actions의 Run workflow로 수동 실행할 수도 있으며 master/main에서 실행한 경우에만 게시한다. 이미지는 linux/amd64 대상으로 빌드한다.

## GitHub Secrets 등록

Docker Hub에서 본인 namespace 아래 `bonchorok` 저장소를 생성한다. Docker Hub Personal Access Token에는 해당 저장소에 push할 수 있는 Read/Write 권한이 필요하다.

GitHub 저장소 → Settings → Secrets and variables → Actions → **Secrets** → New repository secret에서 다음 두 개를 등록한다. 두 값 모두 Secrets에 등록하도록 구현했다.

| 이름 | 값 |
| --- | --- |
| DOCKERHUB_USERNAME | Docker Hub 사용자 이름. GitHub 사용자 이름이나 이메일이라고 가정하지 않는다. |
| DOCKERHUB_TOKEN | Docker Hub에서 발급한 액세스 토큰 |

설정 주소: https://github.com/demongod2020/hanyaaaak/settings/secrets/actions

토큰을 코드, Dockerfile, 명령 인수 또는 캡처에 넣지 않는다. 워크플로가 Secrets를 로그인 액션에 전달한다. 값이 없으면 검사는 수행한 뒤 게시 설정 단계에서 명확한 오류로 종료한다. 원격 Secrets의 등록 상태는 이번 로컬 작업에서 확인하지 않았다.

## GitHub에 반영하기

파일은 로컬에 작성했으며 이 작업에서 commit/push하지 않았다. 새로 추가한 서버 파일도 아직 Git 추적 대상이 아니므로 워크플로 파일만 올려서는 빌드되지 않는다. 다음 파일들이 같은 Git 커밋에 포함되어야 한다.

- Dockerfile, .dockerignore, .github/workflows/ci.yml
- main.py, requirements.txt, smoke_test.py
- 기존 dist/ 전체
- HW3/README.md, HW3/CI_SETUP.md

기존 원격 저장소에 로컬에 없는 변경이 있을 수 있으므로 먼저 fetch와 차이 확인을 한다. 충돌이 있으면 원격 변경을 보존해 통합하며 force push하지 않는다. tmp, .venv, 인증정보, 과제 보고서 전체를 무작정 `git add .`로 올리지 않는다.

```powershell
git fetch origin
git log --oneline --left-right master...origin/master
git status --short
```

원격 변경 통합을 마친 뒤 필요한 파일을 선택해 커밋하고 push한다.

```powershell
git add Dockerfile .dockerignore .github/workflows/ci.yml main.py requirements.txt smoke_test.py dist HW3/README.md HW3/CI_SETUP.md
git diff --cached --stat
git commit -m "Add tested Docker Hub publishing workflow for Bonchorok"
git push -u origin master
```

## 성공 확인과 제출 증빙

1. GitHub의 Actions → Bonchorok Docker CI에서 해당 커밋 실행을 연다.
2. Build 단계에서 `PASS: FastAPI import, 601 unique herbs and runtime assets`를 확인한다.
3. HTTP 검사 단계에서 `PASS`와 601개 약재 상태 응답을 확인한다.
4. Publish 단계가 성공했는지, push digest와 원격 inspect 결과가 있는지 확인한다.
5. Docker Hub의 bonchorok Tags에서 `hw3`, `latest`, `sha-전체커밋SHA`를 확인한다. hw3/latest는 새 push마다 갱신되고 SHA 태그로 코드 버전을 구분할 수 있다.
6. 다른 컴퓨터에서 아래 명령으로 실행하고 화면을 확인한다. YOUR_DOCKERHUB_USERNAME은 실제 이름으로 바꾼다.

```powershell
docker pull YOUR_DOCKERHUB_USERNAME/bonchorok:hw3
docker run -d --name bonchorok-hw3 -p 127.0.0.1:8000:8000 YOUR_DOCKERHUB_USERNAME/bonchorok:hw3
docker exec bonchorok-hw3 python smoke_test.py
```

브라우저 주소: http://127.0.0.1:8000

캡처할 화면: 워크플로 코드, Secrets **이름만 보이는** 목록, Actions 전체 성공 화면, 데이터 로딩/HTTP 검사 로그, Docker Hub 태그와 digest, pull 후 실행한 앱 주소창과 화면. Docker Hub 게시 자체가 인터넷 웹서버 운영을 의미하지는 않는다.

## 검증 범위와 제한

2026년 11월 6일 검증 결과:

- actionlint v1.7.12로 워크플로 문법과 GitHub Actions 표현식 검사 통과. 공식 릴리스 체크섬 확인 후 실행했으며 별도 ShellCheck/Pyflakes 검사는 실행하지 않았다.
- Dockerfile에 추가한 FastAPI import, 약재 601개 로딩, 고유 ID, 괴화 항목과 화면 파일 검사 코드를 호스트에서 실행해 통과했다.
- 동일한 Uvicorn 진입점을 임시 포트 18000으로 실행해 기존 HTTP smoke test를 통과했다. 검사 후 임시 서버는 종료했다.
- 기존 Linux Python 3.12용 의존성 다운로드 및 의존성 해결 검증 통과.

이 컴퓨터에서는 Docker와 GitHub CLI 실행 파일을 찾지 못했다. **실제 Docker 빌드, Actions 원격 실행과 Docker Hub 게시 완료는 아직 확인하지 못했다.** 호스트 검사는 컨테이너 검증을 대체하지 않는다. 원격 실행 성공 여부는 파일 push와 Secrets 등록 후 Actions에서 확인해야 한다.

약재 수를 의도적으로 바꾸면 Dockerfile과 smoke_test.py의 601개 기준을 함께 갱신한다. Python 의존성을 추가·변경할 때는 requirements.txt를 업데이트하고 빌드부터 다시 검증한다.

공식 참고: https://docs.docker.com/build/ci/github-actions/ 및 https://docs.docker.com/build/ci/github-actions/test-before-push/
