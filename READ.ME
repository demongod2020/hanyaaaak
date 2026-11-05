# 본초록 한약재 정보 앱

한약재 601종의 이름·학명·기원·전통 효능·문헌별 용량·주의사항·관련 처방을 검색하는 학습용 웹 앱입니다. 한글 풀이, 원문 확인, 출처 링크, 기기 내 북마크와 모바일 화면을 제공합니다.

## FastAPI로 실행하기

주소는 **http://127.0.0.1:8000**입니다. `127.0.0:8000` 대신 네 자리 루프백 주소를 사용합니다.
Python 3.10 이상이 필요하며 이번 실행은 Python 3.12에서 검증했습니다.

PowerShell에서 이 README가 있는 폴더로 이동한 뒤 실행하세요. 아래 명령은 프로젝트 루트와 독립 실행용 `HW` 폴더에서 동일하게 사용할 수 있습니다.

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe main.py
```

`python`이 Windows 스토어만 열면 설치한 Python의 실행 파일 경로를 사용하거나 첫 명령을 `py -3 -m venv .venv`로 바꾸세요.
가상환경을 이미 준비했다면 마지막 명령만 실행하면 됩니다. Windows에서는 `run.cmd`를 더블클릭해도 됩니다.
종료하려면 서버가 실행되는 콘솔에서 `Ctrl+C`를 누르세요. 8000번 포트가 사용 중이면 그 포트를 사용하는 본인 서버를 먼저 종료하세요.

Python 서버 코드 수정 시 자동 재시작이 필요할 때는 다음 명령을 사용합니다. HTML·CSS·JSON을 수정한 뒤에는 브라우저를 새로고침하세요.

```powershell
.\.venv\Scripts\python.exe -m uvicorn main:app --host 127.0.0.1 --port 8000 --reload
```

Linux/macOS에서는 가상환경 실행 경로만 `.venv/bin/python`으로 바꾸면 됩니다.

## 확인할 주소

| 주소 | 용도 |
| --- | --- |
| http://127.0.0.1:8000/ | 앱 화면 |
| http://127.0.0.1:8000/?herb=sophorae-flos | 괴화 상세 정보 |
| http://127.0.0.1:8000/api/health | 서버 상태와 601개 데이터 로딩 확인 |
| http://127.0.0.1:8000/docs | FastAPI 상태 API 문서 |

`/api/health`의 정상 응답은 `{"status":"ok","service":"bonchorok","herb_count":601}`입니다.
FastAPI는 `dist` 안의 HTML·CSS·JavaScript·JSON·사진을 제공합니다. 검색과 북마크는 브라우저에서 처리하며, 별도 DB 서버나 모델은 필요하지 않습니다. 북마크는 브라우저와 접속 주소별로 저장됩니다.

## 파일 구성

- `main.py`: FastAPI 서버와 상태 확인 API
- `requirements.txt`: 검증에 사용한 실행 의존성의 고정 버전
- `run.cmd`: 설치된 가상환경으로 서버를 시작하는 Windows 실행 파일
- `dist/`: 실제 화면, 약재 JSON 및 이미지
- `smoke_test.py`: 서버 실행 후 HTTP 응답·데이터·비공개 파일 차단 확인
- `HW/`: 과제용 독립 실행 사본과 DevOps 설명 Word 문서 (프로젝트 루트에만 존재)

`HW`의 소스·데이터는 이 작업 시점의 사본입니다. 이후 변경할 때는 실행할 폴더의 파일을 수정하세요.
`.venv`, 캐시, 인증정보와 로그는 GitHub에 올리지 않습니다. `HW/.venv`는 이 컴퓨터에서 실행할 때만 사용하고 다른 컴퓨터에서는 다시 설치하세요.

## 검증

서버를 실행한 상태에서 다른 PowerShell 창을 열고 실행합니다.

```powershell
.\.venv\Scripts\python.exe smoke_test.py
```

이 검사는 HTTP와 데이터 검증입니다. 화면 동작은 브라우저에서 검색, 북마크 저장 후 새로고침, 모바일 화면을 따로 확인합니다.

## DevOps와 프로젝트의 연결

Codex를 활용해 기능을 개발하고 Git으로 변경을 기록했습니다. 기존 공개 GitHub 저장소의 커밋에는 Vercel 배포 성공 체크가 연결되어 있습니다. 코드 관리와 배포가 연결되어 수정 사항을 사용자에게 전달하는 흐름이 DevOps의 구체적인 적용 사례입니다.

- 기존 GitHub: https://github.com/demongod2020/hanyaaaak
- 기존 공개 서비스: https://hanyaaaak.vercel.app
- 기존 배포 증빙: 커밋 `ca7f2c3`의 Vercel 성공 체크 (2026-11-01 확인)
- 이번 추가 사항: FastAPI 로컬 서버, 설치 목록, README, 서버 상태 확인과 실행 검사

**이번 FastAPI 추가본은 로컬 준비본입니다.** 기존 Vercel 서비스는 정적 앱이며 이번 Python 서버가 공개 배포되었다는 뜻은 아닙니다. 이 작업에서는 GitHub에 새 커밋을 올리거나 기존 배포 설정을 변경하지 않았습니다. FastAPI 자체를 공개 운영하려면 Python 실행 환경에 맞는 배포 구성이 추가로 필요합니다.

FastAPI 개발 서버의 `--reload`는 로컬 파일 변경 감지 기능이고, GitHub와 Vercel의 자동 배포는 원격 서비스 갱신 과정입니다. 둘은 서로 다른 단계입니다.

## 자료 출처와 이용 범위

- 식품의약품안전평가원: https://www.nifds.go.kr/herb/m_442/list.do
- 약학정보원: https://health.kr/researchInfo/herbalMedicine1.asp
- 한국한의학연구원 OASIS: https://oasis.kiom.re.kr/herblib/main.do

각 약재의 상세 화면에 개별 출처와 이미지 이용 조건을 표시했습니다. 한글 독음 자료의 Unicode 라이선스는 `dist/unicode-license.txt`에 있습니다. 제3자 자료와 사진은 해당 출처의 이용 조건을 따릅니다.
이 앱은 학습용이며 진단·처방·개인 복용량을 제공하지 않습니다. 전체 자료의 전문가 검토는 완료되지 않았고, 확인되지 않은 항목·이미지도 있습니다.
