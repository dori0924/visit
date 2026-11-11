# 방문자 안내 앱 (Visitor Guide, 한/영)

방문자가 기본 안내를 확인하고 준수서약서를 작성하거나 안전교육 페이지로 이동하는 Streamlit 웹앱입니다.
요구사항은 [PRD.md](PRD.md), 개발 단계는 [PROMPTS.md](PROMPTS.md)를 참고하세요.

> 현재 **4단계(Playwright 검토)** 까지 완료되었습니다. 검토 결과는 [REVIEW.md](REVIEW.md)를 보세요.
>
> 테스트 실행: `.\.venv\Scripts\python.exe -m pytest` (테스트용 서버·임시 DB를 자동으로 띄웁니다)

## 실행 방법 (Windows)

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
copy .streamlit\secrets.toml.example .streamlit\secrets.toml   # ADMIN_PASSWORD 채우기
.\.venv\Scripts\python.exe -m streamlit run app.py
```

브라우저에서 http://localhost:8501 이 열립니다.

- `secrets.toml`에 Google Sheets 정보가 없으면 로컬 SQLite 파일(`data/visitor.db`)에 저장합니다.
- 환경 변수 `VISITOR_APP_DB`로 SQLite 파일 위치를 바꿀 수 있습니다(테스트용).
- 관리자 화면은 왼쪽 위 **»** 버튼으로 사이드바를 연 뒤 **🔐 관리자**에서 `ADMIN_PASSWORD`로 로그인합니다.
- 방문자에게 오류 상세가 보이지 않도록 `showErrorDetails = "none"`으로 설정했습니다. 개발 중 오류를 보려면 `--client.showErrorDetails full`을 붙여 실행하세요.
- 안내문을 관리자 모드에서 고칠 때 `#### 제목`으로 시작하는 구역은 첫 화면에서 카드 한 장으로 표시되고, `> 문장`은 파란 강조 박스로 표시됩니다.

> ⚠️ **Windows 스마트 앱 컨트롤**이 켜져 있으면 pandas·pyarrow의 DLL이 차단되어
> 관리자 화면(기록 표)이 "애플리케이션 제어 정책에서 이 파일을 차단했습니다" 오류로 열리지 않습니다.
> 방문자 화면은 정상 동작합니다. Streamlit Cloud(Linux)에서는 문제가 없습니다.

## 관리자 기능

| 탭 | 기능 |
|---|---|
| 📋 서약서 기록 | 최신순 표, 날짜·이름·국적·방문목적 필터, CSV 다운로드(엑셀 한글 호환), 1년 지난 기록 파기 |
| ⚙️ 앱 설정 | 안전교육 URL(한/영), 회사 로고(PNG/JPG/SVG), 첫 화면 안내문·서약서 본문(한/영) 수정·미리보기·기본값 되돌리기 |

- 비밀번호를 5번 연속 틀리면 5분간 잠깁니다.
- 1년 지난 기록이 있으면 관리자 화면 위에 안내가 뜨고, 확인 체크 후 파기 버튼으로 삭제합니다.

## Google Sheets 연결 (운영 배포 시)

1. [Google Cloud Console](https://console.cloud.google.com/)에서 프로젝트를 만들고 **Google Sheets API**와 **Google Drive API**를 사용 설정합니다.
2. **IAM 및 관리자 → 서비스 계정**에서 서비스 계정을 만들고, **키 → 키 추가 → JSON**으로 키 파일을 내려받습니다.
3. Google 스프레드시트를 새로 만들고, **공유** 버튼으로 서비스 계정 이메일(`...@....iam.gserviceaccount.com`)을 **편집자**로 추가합니다.
4. 시트 주소 `https://docs.google.com/spreadsheets/d/<SHEET_ID>/edit` 에서 `<SHEET_ID>` 부분을 복사합니다.
5. `secrets.toml`(또는 Streamlit Cloud의 Secrets)에 `SHEET_ID`와 `[gcp_service_account]` 섹션을 채웁니다. JSON 키 파일의 각 항목을 `키 = "값"`으로 옮기면 됩니다.
6. 앱을 실행하면 `pledges`(서약서 기록), `settings`(앱 설정) 시트가 자동으로 만들어집니다.

참고
- 셀 값은 입력 그대로(RAW) 저장되므로 `=`로 시작하는 입력이 수식으로 실행되지 않고, 휴대폰 번호 앞의 0도 유지됩니다.
- 시트를 직접 고쳐도 되지만 **첫 줄(제목 행)은 바꾸지 마세요.** 앱이 열 이름으로 데이터를 찾습니다.
- 앱은 시트 내용을 최대 60초 동안 기억합니다. 시트를 직접 고친 내용은 최대 1분 뒤 반영됩니다.

## 파일 구성

| 파일 | 역할 |
|---|---|
| `app.py` | 진입점. 로고·제목·언어 선택, 사이드바 관리자 메뉴, `session_state["page"]`에 따른 화면 전환 |
| `pages_impl/home.py` | 첫 화면: 기본 안내 + 카테고리 버튼(안전교육은 URL이 있으면 바로 새 창) |
| `pages_impl/pledge.py` | 준수서약서 입력·검증·저장, 제출 완료 화면 |
| `pages_impl/safety.py` | 안전교육 이동(URL 없으면 '준비 중') |
| `pages_impl/admin.py` | 관리자 로그인, 기록 열람·CSV·파기, 앱 설정 |
| `i18n.py` | 한/영 UI 문구, 국적·방문목적 선택지 |
| `ui.py` | 화면 꾸밈 전용: 공통 CSS, 상단 파랑 배너, 안내 카드, 제출 완료 카드 |
| `.streamlit/config.toml` | 파랑 계열 테마 색상, Pretendard 글꼴, 업로드 2MB 제한 |
| `storage.py` | 저장소 인터페이스, SQLite·Google Sheets 구현 |
| `settings.py` | 관리자 설정 읽기·저장, 기본값 처리, 로고 처리 |
| `content/*.md` | 기본 안내서·준수서약서 (관리자가 수정하기 전 초기 문구) |

`pages/`가 아니라 `pages_impl/`인 이유: 폴더 이름이 `pages/`면 Streamlit이 멀티페이지 앱으로 자동 인식해 사이드바에 메뉴를 만들어 버립니다.
