# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 프로젝트와 기준 문서

Streamlit(Python) 방문자 안내 웹앱(한/영)으로, Streamlit Community Cloud에 배포한다. 방문자는 로그인 없이 기본 안내를 보고 준수서약서를 제출하거나 안전교육 외부 링크로 이동한다. 관리자는 비밀번호로 서약서 기록을 열람하고 앱 문구·URL·로고를 수정한다.

- `PRD.md`(v1.3)가 요구사항의 단일 기준이다. 기능은 `FR-x.y`로 참조한다. 요구사항이 바뀌면 PRD를 먼저 고치고 버전을 올린다.
- `PROMPTS.md`는 4단계 개발 순서다(1 뼈대 → 2 기능 → 3 UI → 4 Playwright 검토). 모두 완료됐다. 사용자가 단계를 요청하면 그 범위를 넘어서 구현하지 않는다.
- `REVIEW.md`는 4단계 검토 결과(발견한 문제 #1~#9)다. 모두 수정됐다.
- 코드를 바꾸면 이 파일과 README.md를 실제 코드에 맞게 갱신한다.

## 명령어 (Windows, 가상환경 `.venv`)

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m streamlit run app.py --server.headless true   # headless: 첫 실행의 이메일 입력 안내에서 멈추지 않게
#   오류 상세 보기: --client.showErrorDetails full  (config.toml은 방문자용으로 "none")
#   SQLite 위치 바꾸기: $env:VISITOR_APP_DB = "$env:TEMP\x.db"   (기본 data/visitor.db)

.\.venv\Scripts\python.exe -m pytest                                        # 단위 + E2E 전체 (약 7분)
.\.venv\Scripts\python.exe -m pytest tests/unit                             # 단위만 (2초)
.\.venv\Scripts\python.exe -m pytest tests/e2e/test_visitor.py              # 파일 하나
.\.venv\Scripts\python.exe -m pytest "tests/e2e/test_admin.py::test_logout_hides_admin"   # 테스트 하나
```

`ui.py`나 `.streamlit/config.toml`을 바꾸면 실행 중인 서버를 재시작해야 반영된다. 로컬 Python은 3.15이고, 3.11 이상과 호환된다.

**스마트 앱 컨트롤**: 예전에는 Windows 스마트 앱 컨트롤이 pandas·pyarrow DLL을 차단해 관리자 로그인 뒤 화면이 열리지 않았다. 사용자가 이를 끈 뒤로는 전체 테스트가 통과한다. 다시 "애플리케이션 제어 정책에서 이 파일을 차단했습니다" 오류가 나면 이 설정을 의심한다. pandas는 관리자 로그인 뒤에만 불러오므로, 차단돼도 방문자 화면은 정상이고 관리자 화면은 안내 문구만 보여준다.

로컬 관리자 비밀번호는 `.streamlit/secrets.toml`(Git 제외)에 있다. 아이디는 없고 비밀번호만 쓴다.

## 테스트 구조와 요령

- `tests/`, `tests/unit/`, `tests/e2e/`는 패키지(`__init__.py`)다. 두 `conftest.py`의 이름이 겹치므로 `from .conftest import ...`로 가져온다.
- **E2E**: `tests/e2e/conftest.AppServer`가 빈 포트에 서버를 띄운다. 이때 `--secrets.files tests/e2e/test_secrets.toml`(가짜 비밀번호, Sheets 정보 없음), 임시 `VISITOR_APP_DB`, `VISITOR_ADMIN_LOCK_SECONDS=6`을 넘긴다. `db` fixture는 테스트마다 기록·설정을 비운다. 실제 Google Sheets에는 절대 쓰지 않는다.
  - 실행이 끝날 때까지 기다릴 때는 `settle()`을 쓴다(`stApp[data-test-script-state="notRunning"]`).
  - 이동은 `wait_until="domcontentloaded"`로 한다. `load`는 외부 글꼴(Pretendard CDN)까지 기다려 시간 초과가 날 수 있다.
  - 위젯은 `.st-key-<key>`로 찾는다. 선택 상자의 선택값은 텍스트가 아니라 combobox 값이라 `to_match_aria_snapshot`으로 확인한다.
  - Streamlit 입력은 포커스가 빠질 때 값을 보내므로 `fill` 뒤에 `Tab`을 누른다.
  - 잠금 테스트 뒤에는 `wait_unlock_and_reset()`으로 잠금을 풀어 다음 테스트에 영향이 없게 한다.
  - 캡처는 세로로 긴 viewport(예: 375×3000)로 찍는다. Streamlit은 본문 안에서 스크롤해서 `full_page`가 잘린다.
- **단위(AppTest)**: `AppTest.from_file`에는 절대 경로를 넘긴다. 비밀번호는 `at.secrets[...]`, 화면은 `at.query_params["page"]`로 정한다.
  - 실행 맥락이 필요한 함수(관리자 콜백 등)는 `AppTest.from_function(harness, args=(ROOT,))`로 부른다(`tests/unit/test_fixes.py`).
  - 국적·방문목적 선택 상자는 언어별 key(`pf_nat__ko`)에 `select("<코드>")`를 쓴다. `select_index`는 쓰지 않는다.
  - 로고·배너는 `st.html`이라 `at.get("html")[i].proto.body`에서 `class="vg-logo"`로 찾는다(CSS에도 `vg-logo` 글자가 있다).
  - 폼 안의 입력은 제출 전에 `run()`하면 버려진다. 입력한 뒤 바로 제출 버튼을 누른다.
  - AppTest에서는 `st.context.ip_address`가 실행마다 다른 MagicMock이다.

## 아키텍처

- **화면 전환**: 멀티페이지(`pages/`)를 쓰지 않는다. 폴더 이름이 `pages/`면 Streamlit이 자동으로 인식하므로 `pages_impl/`을 유지한다. `app.py`가 `session_state["page"]`(home/pledge/safety/admin)에 따라 `pages_impl/<화면>.render()`를 부른다. 이동은 `pages_impl.go(page)`를 `on_click` 콜백으로 넘긴다.
- **새로고침 유지**: `app.init_state()`가 URL `?page=…&lang=…`에서 화면·언어를 되살리고, `sync_url()`이 매 실행마다 URL에 다시 적는다. 서약서 입력값(개인정보)과 관리자 로그인은 일부러 URL에 남기지 않는다.
- **다국어**: 언어 선택 상자의 key가 곧 `session_state["lang"]`이다. UI 문구는 `i18n.t(key)`로만 가져오고 화면 코드에 직접 쓰지 않는다.
  - 텍스트 입력·체크박스는 key가 같으면 라벨이 바뀌어도 값이 유지된다.
  - `format_func`로 번역하는 선택 상자는 유지되지 않는다. 브라우저는 이전 언어의 라벨을 돌려보내고, Streamlit은 새 선택지에 없는 그 문자열을 그대로 값으로 쓴다. 그래서 `pledge._choice()`처럼 코드를 언어와 무관한 키(`pf_nat`)에 보관하고, 위젯은 언어별 key로 만든다. `format_func`에는 렌더링 시점의 언어를 기본 인자로 고정한다. 새 번역 선택 상자도 이 패턴을 따른다.
  - Streamlit은 `<html lang="en">`으로 고정해서 크롬 자동 번역이 화면을 망친다. `ui.set_document_lang()`이 `lang`을 맞추고 번역을 끈다(`st.html(..., unsafe_allow_javascript=True)`, 값은 `ko`/`en` 화이트리스트).
- **콜백 + flash**: 버튼 동작은 `on_click` 콜백에서 처리한다. 결과 메시지는 `session_state["flash_<구역>"]`에 i18n 키로 넣고 다음 실행에서 보여준다. 위젯 값(폼 초기화, 편집창 되돌리기)은 콜백 안에서만 바꿀 수 있다.
- **저장소**: `storage.Storage` 인터페이스 뒤에 `GoogleSheetsStorage`(운영)와 `SQLiteStorage`(로컬·테스트)가 있다. `st.secrets`에 `gcp_service_account`가 없으면 SQLite를 쓴다. `get_storage()`는 `st.cache_resource` 하나다.
  - 모든 오류는 `StorageError`로 바뀐다. 방문자 화면의 설정 읽기(`settings.get`)는 실패하면 기본값으로 대신한다.
  - Sheets는 읽은 내용을 60초 동안 메모리에 두고, 자기가 쓰면 그 캐시를 비운다. 값은 `value_input_option="RAW"`로 쓴다(수식 실행 방지, 앞자리 0 유지).
  - Sheets에서 행을 지울 때는 행 번호를 미리 계산하지 않는다. `_delete_by_values()`가 지우기 직전마다 id/key 열을 다시 읽어 확인한다.
  - `submitted_at`은 KST ISO 문자열이라 문자열 비교로 기간을 거른다.
  - Streamlit Cloud의 파일 시스템은 재시작하면 지워지므로 운영에서 로컬 파일에 의존하지 않는다.
- **관리자 설정**: 안내문·서약서 본문(한/영), 안전교육 URL(한/영), 로고는 저장소의 `settings` key-value에 둔다. 값이 없으면 `content/*.md` 또는 `settings.DEFAULT_VALUES`(안전교육 기본 주소, 임시값)를 쓰고, `settings.reset(key)`로 되돌린다.
  - 모듈 이름이 `settings`이므로 `import settings` 후 `settings.get/set`으로 쓴다.
  - 로고는 Sheets 셀 5만 자 제한 때문에 가로 400px 이하 PNG로 줄인다. base64를 `logo_0`, `logo_1`…로 나누고 `logo_chunks`, `logo_mime`을 함께 저장한다. SVG는 200KB 이하이고 스크립트·이벤트 속성이 없을 때만 받는다.
- **관리자 보안** (`pages_impl/admin.py`):
  - 인증 전에는 로그인 폼만 그리고 저장소를 읽지 않는다. 비밀번호는 `hmac.compare_digest`로 비교한다.
  - 로그인 잠금은 `LoginGuard`가 서버 메모리에 접속 주소별로 둔다(session_state에 두면 새로고침으로 풀린다). 5회 실패 시 5분, 반복될 때마다 두 배, 최대 60분이다. 주소가 문자열이 아니면 "unknown" 한 묶음으로 센다.
  - 무동작 30분이면 자동 로그아웃한다(`_check_idle`). **관리자 버튼 콜백에는 반드시 `@_admin_action`을 붙인다.** 콜백은 render보다 먼저 실행되므로 붙이지 않으면 만료된 탭에서도 동작한다.
  - 테스트용으로 시간을 줄이려면 `VISITOR_ADMIN_LOCK_SECONDS`, `VISITOR_ADMIN_IDLE_SECONDS`를 쓴다.
  - pandas는 `_load_pandas()`로만 불러온다. 첫 실패를 기억해서, 반쯤 불러온 모듈 때문에 나는 AttributeError가 화면에 그대로 보이지 않게 한다.
  - CSV는 UTF-8 BOM(엑셀 한글)으로 만들고, `csv_safe()`로 `= + - @`로 시작하는 값을 무력화한다.

## UI 규칙

- 파랑 계열 테마(PRD 8.4 색상)는 `.streamlit/config.toml`에, 커스텀 CSS는 `ui.CSS` 한 곳에만 둔다. 영역은 `st.container(key=...)`가 붙이는 `.st-key-<key>` 클래스로 꾸민다(`notice_*`, `cat_card_*`, `pledge_text`, `done_card`). key를 바꾸면 스타일이 풀린다.
- 안내문의 `#### 제목` 구역은 첫 화면에서 카드 한 장(`ui.notice_cards`), `> 문장`은 강조 박스가 된다.
- 처리 중 버튼 차단(#4)은 `stApp[data-test-script-state="running"]` 속성에 건 CSS다. Streamlit 버전을 올리면 이 속성이 그대로 있는지 확인한다.
- 관리자 메뉴가 사이드바에 있으므로 헤더를 통째로 숨기지 않는다(사이드바 열기 버튼이 헤더에 있다).
- 배너에 넣는 문자열은 `html.escape`를 거친다. `unsafe_allow_html`은 쓰지 않는다.
