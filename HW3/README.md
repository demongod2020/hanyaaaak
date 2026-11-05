# HW3 본초록 Docker 이미지 제작과 Docker Hub 배포

## 1. 프로젝트 분석과 작업 범위

| 항목 | 확인 내용 |
| --- | --- |
| 서버 언어와 프레임워크 | Python, FastAPI, Uvicorn |
| 프런트엔드 | `dist/`의 HTML, CSS, JavaScript |
| 데이터 | `dist/herbs.json`의 601개 항목, 별도 DB 서버 불필요 |
| 서버 진입점 | 루트 `main.py`의 `app` 객체 (`main:app`) |
| 기존 로컬 실행 | `python main.py`, `127.0.0.1:8000` |
| Docker 실행 | `python -m uvicorn main:app --host 0.0.0.0 --port 8000` |
| 이미지 기반 | 공식 `python:3.12-slim-bookworm`, Linux 컨테이너 |
| 설치 의존성 | 기존 `requirements.txt`의 고정 버전 사용 |

Dockerfile과 .dockerignore는 **프로젝트 루트**에 추가했다. 이 안내서는 `HW3/README.md`이다. 기존 `main.py`, 화면, 데이터, HW2 사본은 변경하지 않았다. Docker 빌드 대상은 루트의 최신 소스이며 `HW/` 사본이 아니다.

컨테이너 내부에서 127.0.0.1로만 실행하면 호스트의 포트 전달 요청을 받지 못한다. 따라서 기존 코드는 그대로 두고 Docker 시작 명령으로 0.0.0.0을 지정했다. 호스트에는 `127.0.0.1:8000:8000`으로 연결해 내 컴퓨터에서 접근하도록 한다. `EXPOSE`만으로 호스트 포트가 열리는 것은 아니다.

의존성을 먼저 복사해 설치하고 소스를 나중에 복사하므로 화면만 바꾼 재빌드에서 의존성 캐시를 재사용할 수 있다. 일반 사용자 UID 10001로 실행하며, 상태 검사는 Python 표준 라이브러리를 사용해 curl 등 추가 도구가 필요 없다. `smoke_test.py`는 컨테이너 내부 검증을 위해 포함했다. 민감정보, 가상환경, 보고서, 임시파일은 빌드 컨텍스트에서 제외한다. `dist`는 공개 파일 폴더이므로 인증정보를 넣지 않는다.

## 2. 실제 검증 상태

2026년 11월 6일 기준:

- 소스와 의존성, 진입점, 정적 파일 구조를 확인했다.
- Python 3.12 / Linux x86-64용 의존성 전체의 wheel 다운로드 및 의존성 해결에 성공했다. Linux용 pydantic_core 바이너리도 확인했다.
- Docker 시작 명령과 같은 Uvicorn 모듈 실행 방식을 Windows에서 별도 포트 18000으로 실행해 기존 HTTP 검사를 통과했다. 601개 약재, 주요 화면 파일, API 문서, 내부 파일 접근 차단을 확인했으며 검사 후 해당 임시 서버는 종료했다. 이는 컨테이너 실행 검증을 대신하지 않는다.
- 이 컴퓨터의 PATH와 Docker Desktop 기본 설치 경로에서 Docker 실행 파일을 찾지 못했다. **Docker 이미지 빌드, 실제 컨테이너 실행, Docker Hub push는 아직 수행하지 못했다.**
- 아래 명령의 성공 예시는 판정 기준이며 실행 완료 증빙이 아니다. 실제 실행 후 화면을 캡처해야 한다.

## 3. Docker 준비

Windows용 Docker Desktop을 설치하고 실행한다. WSL 2 기반 Linux 컨테이너 환경을 사용한다. 설치 후 PowerShell을 새로 열어 아래 명령에서 Client와 Server 정보가 모두 나오는지 확인한다.

```powershell
docker version
docker info
```

공식 설치 안내: https://docs.docker.com/desktop/setup/install/windows-install/

이하 명령은 PowerShell 기준이다. 사용자 이름은 GitHub 계정과 같다고 가정하지 않고 실제 Docker Hub 사용자 이름으로 입력한다. 비밀번호나 토큰은 파일에 기록하지 않는다.

## 4. 로컬 빌드와 실행

```powershell
Set-Location 'C:\Users\myshin\Documents\codex make'
docker build --pull --tag bonchorok:hw3 .
docker image ls bonchorok
docker run --detach --name bonchorok-hw3 --publish 127.0.0.1:8000:8000 bonchorok:hw3
```

명령별 종료 코드를 확인하고 실패하면 다음 단계로 넘어가지 않는다. `docker run`은 컨테이너 ID를 출력한다. 이름이 이미 사용 중이면 먼저 아래 종료/삭제 절차로 본인의 이전 과제 컨테이너를 정리한다.

8000번 포트가 기존 FastAPI 서버에 사용 중이면 그 서버를 직접 종료하거나 아래처럼 **호스트 포트만 8001로 변경**한다. 이 경우 브라우저 주소도 8001로 바꾸며 컨테이너 내부는 여전히 8000이다.

```powershell
docker run --detach --name bonchorok-hw3 --publish 127.0.0.1:8001:8000 bonchorok:hw3
```

두 run 명령 중 하나만 실행한다. Docker 실행에는 Python이나 Node.js를 호스트에 별도로 설치할 필요가 없다.

## 5. 실행 검증

```powershell
docker ps --filter name=bonchorok-hw3
docker logs bonchorok-hw3
docker inspect --format '{{.State.Health.Status}}' bonchorok-hw3
Invoke-RestMethod http://127.0.0.1:8000/api/health
docker exec bonchorok-hw3 python smoke_test.py
```

시작 직후에는 `starting`일 수 있으며 약 30초 후 상태를 다시 확인한다. 정상 기준은 `healthy`, 상태 API의 `status=ok`, `service=bonchorok`, `herb_count=601`, smoke test의 `PASS` 출력이다. smoke test는 HTTP 응답, 약재 ID, 주요 화면 파일, API 문서와 내부 파일 접근 차단을 확인한다. `docker exec`를 이용하므로 호스트 Python이 필요 없고 호스트 포트를 8001로 바꿔도 같은 검사를 사용할 수 있다.

브라우저에서도 다음을 확인한다.

1. `http://127.0.0.1:8000/?herb=sophorae-flos`에서 괴화 화면과 이미지가 표시된다.
2. 감초를 검색하고 상세 내용을 연다. 한글 설명과 출처 링크를 확인한다.
3. 북마크를 저장하고 새로고침한 뒤 유지되는지 확인한다.
4. 모바일 너비에서 화면이 가로로 넘치지 않는지 확인한다.
5. `http://127.0.0.1:8000/docs`에서 상태 API 문서를 확인한다.

북마크는 브라우저의 localStorage에 저장한다. 다른 컴퓨터나 다른 포트에서는 별도 저장소를 사용하며 Docker 이미지에 개인 북마크가 포함되지 않는다. 외부 참고 사이트 접속과 Swagger UI 리소스 로딩에는 인터넷이 필요할 수 있다.

종료와 컨테이너 삭제:

```powershell
docker stop bonchorok-hw3
docker rm bonchorok-hw3
```

## 6. Docker Hub 로그인과 저장소 생성

1. https://hub.docker.com 에서 본인 계정으로 로그인한다.
2. Repositories에서 Create repository를 선택하고 본인 namespace에 `bonchorok` 저장소를 만든다. 과제에서 로그인 없이 pull할 수 있어야 한다면 Public을 선택한다.
3. 터미널에서 다음 명령을 실행하고 안내되는 브라우저 인증을 완료한다.

```powershell
docker login
```

Docker Hub는 기본적으로 브라우저 장치 코드 인증을 지원한다. Docker Desktop은 운영체제 자격 증명 저장소를 사용한다. 로그인 성공 화면은 캡처하되 비밀번호, 액세스 토큰, 인증 코드는 가린다.

브라우저 로그인을 사용할 수 없다면 다음처럼 사용자 이름만 지정하고 Password 프롬프트에 Docker Hub Personal Access Token을 입력한다. push에 필요한 Read/Write 권한을 사용하며 토큰을 명령 인수, 소스 코드, 보고서에 넣지 않는다.

```powershell
docker login --username YOUR_DOCKERHUB_USERNAME
```

위 방식 중 하나만 사용하면 된다. 자동 배포용 GitHub Actions 설정도 추가되어 있다. CI에서는 로그인 액션이 GitHub Secrets의 DOCKERHUB_USERNAME과 DOCKERHUB_TOKEN을 사용한다. 등록 방법은 [CI 설정 안내](CI_SETUP.md)를 참고한다.

## 7. 태그와 업로드

`YOUR_DOCKERHUB_USERNAME`을 실제 Docker Hub 사용자 이름으로 바꾼다. 저장소 이름은 여기서는 `bonchorok`이다. 이미지 이름은 `사용자이름/저장소이름:태그` 형식이며 과제 버전은 `hw3`로 구분한다.

```powershell
docker tag bonchorok:hw3 YOUR_DOCKERHUB_USERNAME/bonchorok:hw3
docker push YOUR_DOCKERHUB_USERNAME/bonchorok:hw3
docker buildx imagetools inspect YOUR_DOCKERHUB_USERNAME/bonchorok:hw3
```

push 완료 시 출력되는 `sha256:...` digest를 기록한다. Docker Hub 저장소의 Tags에서 `hw3`와 갱신 시각을 확인하고 원격 inspect 결과의 digest와 비교한다. buildx는 Docker Desktop에 포함된다. `latest`가 별도로 필요하면 같은 검증 완료 이미지에 추가로 태그를 지정한다.

```powershell
docker tag bonchorok:hw3 YOUR_DOCKERHUB_USERNAME/bonchorok:latest
docker push YOUR_DOCKERHUB_USERNAME/bonchorok:latest
```

공개 저장소 주소는 `https://hub.docker.com/r/YOUR_DOCKERHUB_USERNAME/bonchorok`이다. **Docker Hub는 이미지를 저장하는 곳이며 push만으로 웹사이트가 인터넷에 공개되는 것은 아니다.** 앱을 사용하려면 이미지로 컨테이너를 실행해야 한다.

## 8. 다른 컴퓨터에서 pull과 실행

Docker가 실행 중인 다른 컴퓨터에서 아래 명령을 실행한다. 공개 저장소는 보통 로그인 없이 pull할 수 있으며 비공개 저장소는 먼저 권한 있는 계정으로 로그인한다.

```powershell
docker pull YOUR_DOCKERHUB_USERNAME/bonchorok:hw3
docker image inspect --format '{{json .RepoDigests}}' YOUR_DOCKERHUB_USERNAME/bonchorok:hw3
docker run --detach --name bonchorok-hw3 --publish 127.0.0.1:8000:8000 YOUR_DOCKERHUB_USERNAME/bonchorok:hw3
docker exec bonchorok-hw3 python smoke_test.py
```

브라우저에서 `http://127.0.0.1:8000`을 열고 5절의 검증을 반복한다. 기본 빌드는 빌드 머신의 Linux CPU 아키텍처를 대상으로 한다. x86-64에서 만든 이미지를 ARM 컴퓨터에서 실행하려면 에뮬레이션 지원 여부를 확인하거나 다음 선택 사항으로 다중 아키텍처 이미지를 만든다.

```powershell
docker buildx build --platform linux/amd64,linux/arm64 --tag YOUR_DOCKERHUB_USERNAME/bonchorok:hw3 --push .
```

이 선택 명령은 로그인 및 다중 아키텍처 빌드 지원이 필요하며 이번 작업에서 검증하지 않았다. 단일 아키텍처 과제 제출에는 필수가 아니다.

## 9. 수정 후 재빌드와 CI 사용

소스 또는 dist를 변경한 뒤 새 태그로 빌드하고 동일한 검증을 반복한다. 실행 중인 컨테이너는 소스 변경만으로 바뀌지 않으며 새 이미지로 컨테이너를 다시 만들어야 한다.

```powershell
docker build --pull --tag bonchorok:hw3-v2 .
docker stop bonchorok-hw3
docker rm bonchorok-hw3
docker run --detach --name bonchorok-hw3 --publish 127.0.0.1:8000:8000 bonchorok:hw3-v2
docker exec bonchorok-hw3 python smoke_test.py
docker tag bonchorok:hw3-v2 YOUR_DOCKERHUB_USERNAME/bonchorok:hw3-v2
docker push YOUR_DOCKERHUB_USERNAME/bonchorok:hw3-v2
```

기존 컨테이너가 있을 때 stop/rm을 실행한다. 패키지를 추가한 경우 `requirements.txt`에도 기록한다. 약재 수를 변경한 경우 기존 smoke_test.py의 601개 기준도 데이터 의도에 맞게 갱신해야 한다. 베이스 이미지 태그는 갱신될 수 있으므로 `--pull` 빌드는 보안 업데이트를 반영할 수 있지만 비트 단위 동일성을 보장하지는 않는다. 엄격한 재현이 필요하면 이후 기반 이미지 digest까지 고정한다.

`.github/workflows/ci.yml`에 checkout → build → 컨테이너 실행 → smoke test → 인증 → push 순서의 자동화를 추가했다. master/main push에서 검사에 성공한 동일한 이미지를 게시한다. Pull Request에서는 검사만 수행한다. 인증정보는 GitHub Secrets에서 받고 hw3, latest, 전체 커밋 SHA 태그를 사용한다. 로컬 파일 작성과 원격 실행은 구분하며, 아직 원격 Actions 실행과 Docker Hub 업로드 성공은 확인하지 못했다. 활성화 절차는 [CI 설정 안내](CI_SETUP.md)에 정리했다.

## 10. 문제 해결

| 증상 | 확인과 해결 |
| --- | --- |
| docker 명령을 찾지 못함 | Docker Desktop 설치 후 새 터미널에서 확인 |
| daemon 연결 오류 | Docker Desktop 실행 및 Linux 엔진 준비 확인 |
| 포트 사용 중 | 기존 본인 서버 종료 또는 호스트 포트 8001 사용 |
| 컨테이너 이름 충돌 | 기존 과제 컨테이너 확인 후 stop/rm 또는 다른 이름 사용 |
| 화면 접속 실패 | `docker ps -a`, `docker logs bonchorok-hw3`, 포트 매핑 확인 |
| unhealthy | `docker inspect bonchorok-hw3`에서 Health.Log 확인 |
| requirements 설치 실패 | PyPI 네트워크, 프록시와 출력된 패키지 오류 확인; 무작정 버전 해제하지 않기 |
| push 권한 오류 | Docker Hub username, 저장소 소유권, 로그인 계정과 토큰 권한 확인 |
| no matching manifest | Linux 컨테이너 모드와 대상 CPU 아키텍처 확인 |

## 11. HW3 증빙 캡처 목록

| 번호 | 캡처할 화면 | 포함할 정보 |
| --- | --- | --- |
| 1 | 프로젝트 구조와 Dockerfile | main.py, dist, requirements.txt 및 Docker 설정 |
| 2 | .dockerignore | 허용 파일과 인증정보·임시파일 제외 규칙 |
| 3 | `docker version` | Client/Server, Linux 컨테이너 환경 |
| 4 | 빌드 완료 터미널과 `docker image ls bonchorok` | 사용 명령, 성공 결과, 태그와 크기 |
| 5 | `docker ps` 및 상태 검사 | 컨테이너 이름, 포트, healthy |
| 6 | 앱 실행 브라우저 | 주소창의 localhost 주소와 괴화 상세 화면 |
| 7 | smoke test와 상태 API | PASS, status=ok, herb_count=601 |
| 8 | push 완료 터미널 | 사용자/저장소:hw3, digest; 인증정보 제외 |
| 9 | Docker Hub Tags 페이지 | 저장소 이름, 공개 여부, hw3 태그 |
| 10 | 다른 컴퓨터의 pull 및 실행 | pull digest, 실행 컨테이너, 앱 화면과 PASS |

다른 컴퓨터가 없다면 같은 PC에서 원격 이미지를 pull해 확인한 것으로 정확하게 적고, 다른 컴퓨터에서 실행했다고 기재하지 않는다. 로그인 토큰·비밀번호·인증 코드 또는 자격 증명 파일은 캡처하지 않는다. 증빙 화면은 실제 실행 후 수집한다.

## 공식 참고 문서

- Docker 빌드 권장 사항: https://docs.docker.com/build/building/best-practices/
- Docker 로그인과 자격 증명: https://docs.docker.com/reference/cli/docker/login/
- FastAPI 컨테이너 배포: https://fastapi.tiangolo.com/deployment/docker/
