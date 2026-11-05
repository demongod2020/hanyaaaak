# Windows Self hosted Runner 자동 배포

저장소 경로: `C:\Users\myshin\Documents\codex make`

등록된 Runner: XANWALL, Windows x64, 이 GitHub 저장소에 연결되어 실행 중인 Runner 2.338.2.
Docker Desktop은 사용자별 설치 경로인 `%LOCALAPPDATA%\Programs\DockerDesktop`에 있으며 Linux 엔진을 사용한다. 이번 확인에서 Docker Engine 29.9.2가 응답했다. 추가 Python 설치나 GPU 모델 설치는 필요하지 않다.

## 동작

`.github/workflows/deploy.yml`은 master의 Bonchorok Docker CI가 성공적으로 끝났을 때 실행한다. 같은 저장소의 push 또는 수동 CI 실행만 허용하며 Pull Request 코드를 로컬 Runner에서 실행하지 않는다. 배포 중 취소로 서비스가 중단되지 않도록 배포 작업은 순서대로 실행한다.

CI가 검사·게시한 `사용자/bonchorok:sha-전체커밋SHA`를 가져온다. 가변 latest 대신 해당 CI의 커밋 태그를 사용하고, pull 후에는 로컬 이미지 ID로 실행하여 검사한 이미지와 서비스 이미지를 일치시킨다.

1. Docker CLI 위치와 Linux 엔진 연결 확인.
2. 기존과 같은 docker/login-action@v4 및 DOCKERHUB_USERNAME, DOCKERHUB_TOKEN Secrets로 로그인.
3. scripts/deploy-local.ps1이 이미지 pull을 수행하며 일시적인 실패는 최대 3번 재시도.
4. 임시 컨테이너를 임의의 로컬 포트로 시작하여 healthy, 기존 HTTP smoke test, 호스트에서 페이지 접속까지 검사.
5. 검사가 성공하면 기존 bonchorok-local을 멈추고 복구용 이름으로 보존한 뒤 새 컨테이너를 127.0.0.1:8000에 실행.
6. 새 서비스 검사까지 성공하면 이전 컨테이너 삭제. 실패 시 새 컨테이너를 정리하고 기존에 실행 중이던 서비스를 다시 시작하여 상태 확인.

앱 주소: http://127.0.0.1:8000/?herb=sophorae-flos

서비스 컨테이너 이름: bonchorok-local. 재시작 정책은 unless-stopped이다. Docker Desktop과 Runner가 실행 중이어야 배포가 가능하고, Docker Desktop이 실행되어야 앱에 접속할 수 있다. 컨테이너 교체 시 짧은 중단 시간이 있다.

## 인증정보와 Runner 파일

인증정보는 Runner의 임시 폴더 아래 실행별 Docker 설정에만 기록하고 배포 후 삭제한다. 기존 사용자 Docker 설정과 인증정보를 덮어쓰지 않는다. Docker endpoint는 기존 활성 context에서 확인하여 임시 설정 사용 중에도 같은 엔진에 연결한다.

actions-runner/, _work/, _diag/, .runner, .credentials 계열 파일, .service, .path는 Git에서 제외했다. Runner는 저장소 안에 설치되어 있으나 GitHub로 업로드하지 않는다. 로컬 Runner는 이 저장소에서 신뢰하는 브랜치의 배포 전용으로 사용한다.

## 확인 명령

PowerShell에서 Docker가 PATH에 없다면 현재 창에 다음 경로를 추가한다.

```powershell
$env:PATH = "$env:LOCALAPPDATA\Programs\DockerDesktop\resources\bin;$env:PATH"
docker ps --filter name=bonchorok-local
docker logs --tail 80 bonchorok-local
docker inspect --format '{{.State.Health.Status}}' bonchorok-local
Invoke-RestMethod http://127.0.0.1:8000/api/health
docker exec bonchorok-local python smoke_test.py
```

GitHub Actions에서 CI 성공 → Bonchorok Local Deploy 성공의 두 실행 기록을 확인하고 Docker 컨테이너의 healthy 상태, 601개 약재 상태 응답, 주소창이 보이는 앱 화면을 캡처한다. 토큰과 Runner 인증 파일은 캡처하지 않는다.

## 장애 대응

- Runner가 Offline이면 해당 PC에서 actions-runner/run.cmd를 실행한다. 이미 실행 중인 Runner를 중복 실행하지 않는다.
- Docker 연결 실패 시 같은 Windows 계정의 Docker Desktop을 켜고 Linux 엔진 상태를 확인한다.
- 다른 앱이 8000번을 쓰는 경우 자동으로 종료하지 않는다. 해당 앱을 확인해 직접 종료하거나 배포 포트를 변경한다.
- 동일한 컨테이너 이름이 다른 용도로 쓰이면 관리 label을 확인하고 변경을 중단한다.
- bonchorok-local-previous가 남아 있으면 이전 복구 상태를 먼저 확인하며 다음 배포가 이를 임의 삭제하지 않는다.
- 실패 원인은 Actions 단계 로그와 docker logs에서 확인한다. 수정 후 push하면 CI부터 다시 검사하며, 기존 성공 CI 실행을 Re-run할 수도 있다.

GitHub에 push하는 변경은 워크플로 두 개와 스크립트, 앱 파일이다. Runner 설치물과 실행 중 생성되는 파일은 포함하지 않는다.
