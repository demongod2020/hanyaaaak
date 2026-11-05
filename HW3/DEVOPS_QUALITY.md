# 배포 품질 개선과 측정 방법

## 기존 구성 분석

기존 CI는 Ubuntu에서 이미지를 빌드하고 HTTP smoke test 후 Docker Hub에 게시했다. Windows Self-hosted Runner는 임시 컨테이너를 검사한 뒤 기존 8000번 컨테이너를 멈추고 새 컨테이너를 시작했다. 이때 포트가 비는 구간이 존재할 수 있었다. 상태 API에는 코드 버전이 없었고, 지속적인 외부 관측·성능 비교·실패 복구 시험·측정 Artifact가 없었다.

## 새 배포 구조

8000번 포트는 bonchorok-local nginx 프록시가 유지한다. 앱은 별도 Docker 네트워크에서 버전별 컨테이너로 실행한다. 후보를 먼저 HTTP/내용/SHA로 검증하고 nginx 설정 검사 후 graceful reload로 연결 대상을 바꾼다. 이전 앱은 종료하지 않고 유지하므로 전환 후 검사가 실패하면 이전 프록시 설정으로 복구한다. 기존 사용자 주소와 브라우저 북마크 origin은 그대로 유지된다.

**첫 도입은 기존 직접 실행 컨테이너의 8000번 포트를 프록시로 넘겨야 한다.** 이 구간은 접속 공백이 생길 수 있으며 모니터링 결과에 포함한다. nginx reload도 실제 관측 없이 무중단이라고 단정하지 않는다.

main.py는 상태 JSON의 deployment_sha와 모든 응답의 X-Deployment-SHA 헤더로 배포 커밋을 제공한다. Docker 빌드에 GIT_SHA를 전달하고 이미지 revision label도 남긴다. 기존 버전의 SHA 없는 응답은 unknown으로 기록하며 태그에서 추정한 값을 실제 응답 버전으로 표시하지 않는다.

## 독립 관측

ops/monitor.py는 배포 프로세스와 별개로 실행된다. 상태 API, 괴화 페이지, herbs.json, app-v2.js를 각 스레드에서 목표 500ms 간격으로 관측한다. 상태/601개 약재/괴화 ID/스크립트 연결/북마크 코드를 검사한다.

각 요청의 UTC 시작/종료 시각, 단조 시계값, 응답시간, HTTP 상태, 내용 검증, 응답 버전, body hash, 전송 크기, 오류를 UTF-8 JSONL로 즉시 flush한다. 실제 시작 간격과 이전 종료부터 다음 시작까지의 미관측 공백을 기록한다. 실패 요청도 보존하며 시간 초과로 샘플을 놓쳐도 가짜 기록을 만들지 않는다.

모든 경로가 첫 관측을 남긴 뒤 작업을 진행하며, 운영 서비스 전환 직전에도 모니터 생존을 확인한다. 성공·실패에 관계없이 배포 종료 후 최소 30초 동안 유지한다. 각 경로의 첫/마지막 관측, 실제 간격과 최대 미관측 공백을 보고한다. 요청 사이의 시간과 관측 시작 전·종료 후는 검증되지 않은 구간이다. 호스트 강제 종료, Runner 강제 취소, 업로드 서버 장애에서는 마지막 로그/Artifact가 없을 수 있으므로 검증 완료로 주장하지 않는다.

## 동일 조건 성능 비교

운영 서비스와 분리한 bonchorok-test-* 네트워크·프록시의 18080번 포트를 사용한다. 이전 이미지와 후보 이미지에 같은 2 CPU/1GiB 제한을 적용한다. 동일 Chromium/Playwright 1.64.1, 1440×1000, ko-KR, 새 브라우저 컨텍스트로 캐시·북마크를 초기화한다. 이전 10회 → 후보 10회 → 이전 10회 → 후보 10회의 교차 배치로 각각 20회 측정한다. 브라우저가 파싱한 JSON의 해시가 같아야 비교를 인정한다.

초기 로딩은 navigation 시작부터 601개 목록·괴화 상세 및 두 번의 animation frame 준비까지 측정한다. Navigation Timing의 load/DOMContentLoaded도 원본에 기록한다. 검색은 감초 input 이벤트부터 두 프레임까지의 시간이며 결과 목록도 데이터 기반 기대값과 비교한다. 괴화 선택, 북마크 저장 후 reload 유지까지 각 표본에서 자동 검증한다.

동일 환경에서 각 HTTP 경로도 전후 20회씩 요청해 p50·p95와 실패율을 계산한다. 성공한 표본만 지연시간 분위수에 포함하고 실패율은 전체 표본을 분모로 한다. p95는 nearest-rank이며 20개 표본의 해상도에는 한계가 있다. OS 캐시, 다른 프로그램의 부하까지 완벽히 통제하지는 못한다. 초기 로딩에는 자동화 왕복 시간이 포함되고 검색에는 프레임 대기가 포함된다. 로컬 시험은 인터넷 성능이나 동시 사용자 부하 시험을 대체하지 않는다.

성능 변경은 JSON gzip 압축(level 3)과 약재별 검색 문자열 WeakMap 캐시에 한정한다. 측정 결과가 나쁘면 그것도 그대로 표시하며 개선률을 꾸며내지 않는다.

## 복구 시험과 로그

격리 환경에서 이전 앱을 서비스하다 후보로 전환한 뒤 후보 컨테이너를 강제 정지한다. 실제 요청 실패를 확인하고 이전 nginx 설정을 복원해 HTTP 내용·버전·설정 일치를 확인한다. fault 옵션은 bonchorok-test-*와 8000 이외 포트에서만 허용한다. 운영 장애 주입은 하지 않는다.

artifacts/deployment에 monitor.jsonl, performance-http.jsonl, browser.jsonl, production-browser.jsonl, environment.json, production/sandbox 이벤트와 Docker 로그, result.json, report.json, summary.md를 저장한다. 실패 시 failure.log와 가능한 로그를 보존한다. CI도 빌드·서버·smoke test 로그를 수집한다. GitHub Actions는 always 조건으로 Artifacts를 업로드하고 Summary에 전후 지표, 버전 전환, 실패 요청, 실제 간격과 미관측 공백, 복구 결과와 한계를 함께 표시한다.

준비 단계 실패는 검증되지 않음 Summary를 남긴다. 원본 로그는 Git 대신 Actions Artifacts에 14일 보관한다. 기존 scripts/deploy-local.ps1도 새 검증 절차를 호출한다.
