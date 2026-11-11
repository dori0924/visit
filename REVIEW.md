# 4단계 검토 보고서 (PRD v1.2 기준)

## 0. 수정 결과 (2026-11-11, PRD v1.3)

3장의 문제 #1~#9를 모두 수정했습니다. 다시 실행한 결과 **단위 + E2E 77개 중 70개 통과, 7개 실패**입니다. 실패 7개는 모두 이 PC에서 pandas가 차단돼 관리자 로그인 뒤 화면이 열리지 않는 환경 문제입니다(5장). 새로 생긴 앱 실패는 없습니다.

| # | 수정 내용 | 확인한 테스트 |
|---|---|---|
| 1 | 로그인 실패 횟수와 잠금을 서버 메모리(`LoginGuard`, 접속 주소별)로 옮김. 5분부터 시작해 반복할수록 두 배, 최대 60분 | E2E `test_lockout_survives_page_reload_and_new_tab` ✅, 단위 `test_lock_shared_across_sessions`, `test_login_guard_…` ✅ |
| 2 | pandas 첫 실패를 기억해 다시 열어도 같은 안내 문구를 보여줌 | E2E `test_admin_error_is_consistent_on_second_visit` ✅, 단위 `test_pandas_failure_is_remembered` ✅ |
| 3 | Sheets 삭제는 지우기 직전마다 id/key 열을 다시 읽어 확인(`_delete_by_values`). 설정 수정도 쓰기 직전에 행을 새로 계산 | 단위 `test_delete_by_values_survives_concurrent_shift`, `test_sheets_set_settings_uses_fresh_rows` ✅ |
| 4 | 처리 중에는 제출·저장·파기·로고 버튼을 누를 수 없고 회전 표시를 띄움 | E2E `test_submit_button_blocked_while_running`, `test_double_click_saves_once` ✅ |
| 5 | 안전교육 URL에 "기본값으로 되돌리기" 버튼 추가 | 단위 `test_reset_urls_restores_default` ✅ (E2E `test_safety_url_validation`은 pandas 차단) |
| 6 | PRD v1.3에 반영: FR-2.6, 2.8, 4.7, 4.10(신규), 5.2, 5.3, 7.6 | — |
| 7 | 휴대폰 번호: `+`는 맨 앞 한 번, 하이픈은 숫자 사이에만 | 단위 `test_phone_format` 12건, E2E 하이픈 연속·앞 하이픈 ✅ |
| 8 | 관리자 무동작 30분이면 자동 로그아웃. 오래 방치된 탭의 버튼 콜백도 막음(`@_admin_action`) | 단위 `test_idle_admin_is_logged_out`, `test_active_admin_stays_logged_in`, `test_admin_callbacks_blocked_after_idle` ✅ |
| 9 | 사이드바 열기 버튼과 도움말 아이콘의 터치 영역을 44px로 확대 | E2E `test_streamlit_controls_touch_targets` ✅ |

**추가 확인:** 사용자가 스마트 앱 컨트롤을 끈 뒤 `tests/e2e/test_admin.py`를 다시 실행해 **13개가 모두 통과**했습니다. 5장에서 검증하지 못했던 항목이 이제 모두 확인됐습니다.
- 기록 표·지표·필터·CSV(BOM, 수식 방어)
- 1년 경과 안내·파기
- 안내문 수정·반영·재시작 후 유지·되돌리기
- URL 검사·되돌리기
- 로고 등록·축소·삭제·불량 파일 거부
- 기록의 HTML 이스케이프

이때 필터의 기본 안내 문구가 영어("Choose options")로 나오는 것을 발견해 한/영 문구로 고쳤습니다.

검토 중 테스트 쪽 문제도 하나 고쳤습니다. 페이지 이동이 외부 글꼴 CDN 때문에 `load` 대기에서 시간 초과가 날 수 있어서, 화면 요소를 기준으로 기다리게 했습니다. 방문자 화면은 `load`를 기다리지 않으므로 사용자에게는 영향이 없습니다.

아래 1~7장은 수정 **전** 검토 내용입니다(기록용).

| 항목 | 내용 |
|---|---|
| 검토일 | 2026-11-11 |
| 방법 | Playwright E2E 테스트(Chromium) + 코드 직접 검토 |
| 실행 환경 | Windows 11, Python 3.15, Streamlit 1.67.0, 임시 SQLite, 테스트 전용 비밀번호 |
| 테스트 코드 | `tests/e2e/` (`conftest.py`, `test_visitor.py`, `test_admin.py`, `test_layout.py`) |
| 실행 방법 | `.\.venv\Scripts\python.exe -m pytest` |

## 1. 요약

**전체 50개 중 42개 통과, 8개 실패**

| 파일 | 통과 | 실패 | 비고 |
|---|---|---|---|
| `test_visitor.py` (방문자 화면) | 28 | 0 | |
| `test_layout.py` (모바일·스크린샷) | 10 | 0 | |
| `test_admin.py` (관리자) | 4 | 8 | 7개는 환경 문제, 1개는 **앱 보안 문제** |

- **방문자 화면은 PRD를 모두 충족**했습니다. 첫 화면, 한/영, 서약서 검증·저장, 중복 제출 방지, 안전교육 링크, 새로고침 유지, 모바일 화면을 확인했습니다.
- **관리자 화면 7개 실패는 이 PC 환경 때문**입니다. Windows 스마트 앱 컨트롤이 pandas·pyarrow DLL을 차단해 로그인 뒤 화면이 열리지 않습니다. 앱 결함인지는 아직 **판단할 수 없습니다**(5장 참고).
- **앱 결함 2건을 새로 찾았습니다.** 관리자 잠금이 새로고침으로 풀리는 문제(높음)와 pandas 오류 문구가 깨지는 문제(보통)입니다.
- 테스트를 통과시키려고 테스트를 고친 적은 없습니다. 테스트 코드 자체의 실수 1건(선택 상자 값을 텍스트로 비교)만 고쳤고, 고치기 전에도 접근성 트리에서 앱이 올바른 값을 갖고 있음을 확인했습니다.

## 2. PRD 요구사항별 결과

✅ 통과 · ❌ 실패 · ⚠️ 이 PC에서 검증 불가 · △ 부분 충족

| FR | 요구사항 | 구현 | 결과 | 근거 |
|---|---|---|---|---|
| FR-1.1~1.4 | 첫 화면 기본 안내, 카테고리 2개 | ✅ | ✅ | `test_home_shows_notice_and_two_categories` |
| FR-1.5 | 안내문 관리자 수정 | ✅ | ⚠️ | `test_edit_notice_reflects_persists_and_resets` (pandas 차단) |
| FR-1.6 | 로고 표시 | ✅ | ⚠️ | `test_logo_upload_show_and_delete` (pandas 차단) |
| FR-2.1~2.5 | 서약서 본문·입력 항목·기타 입력·동의 2개 | ✅ | ✅ | `test_other_inputs_saved`, `test_other_selected_but_empty_rejected` |
| FR-2.6 | 입력값 검증 | ✅ | ✅ | `test_invalid_pledge_rejected` 7건, `test_name_longer_than_50_cannot_be_entered` |
| FR-2.7 | 저장 + 완료 메시지(제출 일시) | ✅ | ✅ | `test_valid_pledge_saved_with_kst`, `test_english_submission_saved` |
| FR-2.8 | 중복 저장 방지 | △ | ✅ | `test_double_click_saves_once`. 중복은 막지만 "제출 중 버튼 비활성"은 없음(문제 #4) |
| FR-3.1~3.2 | 저장 필드, KST, 영구 저장 | ✅ | ✅ | `test_valid_pledge_saved_with_kst` |
| FR-3.3 | 방문자 화면에서 기록 조회 불가 | ✅ | ✅ | `test_records_never_visible_to_visitors`, `test_admin_requires_password` |
| FR-4.1~4.2 | 비밀번호 인증, Secrets 관리 | ✅ | ✅ | `test_admin_requires_password` |
| FR-4.3~4.5 | 기록 표·필터·CSV(BOM) | ✅ | ⚠️ | `test_records_metrics_filter_and_csv` (pandas 차단) |
| FR-4.6 | 로그아웃 | ✅ | ✅ | `test_logout_hides_admin` |
| FR-4.7 | 5회 실패 잠금 | △ | ❌ | `test_wrong_password_rejected_and_locked_after_5` ✅ / `test_lockout_survives_page_reload` ❌ (문제 #1) |
| FR-4.8~4.9 | 1년 경과 안내·파기 | ✅ | ⚠️ | `test_retention_banner_and_purge` (pandas 차단) |
| FR-5.1~5.2 | 안전교육 새 창, 언어별 URL, 영문 대체 | ✅ | ✅ | `test_safety_link_uses_default_url_in_new_tab` 2건, `test_safety_url_from_settings_and_en_fallback` |
| FR-5.3 | URL 미설정 시 "준비 중" | △ | — | 기본 URL이 생겨 도달할 수 없음(문제 #6) |
| FR-6.1~6.2 | 한/영 전환, 입력값 유지 | ✅ | ✅ | `test_english_has_no_korean_left` 4건, `test_english_sidebar_and_pledge_errors`, `test_language_switch_keeps_form_values`, `test_browser_translation_disabled` |
| FR-7.1~7.5, 7.7~7.8 | 앱 설정(문구·URL·로고), 즉시 반영, 재시작 유지 | ✅ | ⚠️ | `test_edit_notice_…`, `test_safety_url_validation`, `test_logo_…` (pandas 차단) |
| FR-7.6 | 항목별 "기본값으로 되돌리기" | △ | ⚠️ | 안내문·서약서에는 있고 URL에는 없음(문제 #5) |
| 5장 사용성 | 모바일 가로 스크롤 없음, 터치 44px | ✅ | ✅ | `test_mobile_no_horizontal_scroll_and_touch_targets` 8건 |
| 5장 성능 | 첫 화면 3초 이내 | ✅ | ✅ | `test_home_loads_within_3_seconds` |
| 그 외 | 화면 이동·"처음으로"·새로고침 유지 | ✅ | ✅ | `test_navigation_and_home_button`, `test_refresh_keeps_page_and_language` |

## 3. 발견한 문제

### #1 [높음] 관리자 로그인 잠금이 새로고침하면 풀린다
- **재현:** 관리자 화면에서 틀린 비밀번호를 5번 입력 → "잠겼습니다" 표시 → 브라우저 새로고침(F5)
- **기대:** 5분 동안 잠금 유지
- **실제:** 로그인 창이 다시 나타나고 다시 5번 시도할 수 있다. 새로고침을 반복하면 비밀번호를 무제한으로 시도할 수 있다.
- **근거:** `test_lockout_survives_page_reload`
- **원인:** 실패 횟수와 잠금 시각을 `st.session_state`(브라우저 세션)에만 저장한다. 새로고침하면 세션이 새로 만들어진다. (`pages_impl/admin.py` `_login()`)
- **수정 제안:** 실패 횟수·잠금 시각을 서버 쪽(저장소 `settings` 또는 서버 메모리)에 둔다. 잠금이 전체 사용자 공통이 되면 공격자가 일부러 틀려서 관리자를 잠가 버릴 수 있다. 그래서 잠금 시간은 짧게(예: 5분) 하고 실패가 반복될 때마다 대기 시간을 늘리는 방식을 권장한다. 운영 비밀번호는 길고 추측하기 어렵게 정한다.

### #2 [보통] 관리자 화면을 두 번째로 열면 안내 문구 대신 파이썬 오류가 그대로 보인다
- **재현:** pandas를 불러올 수 없는 PC에서 관리자 로그인 → 다시 관리자 화면을 열거나 다시 로그인
- **기대:** 처음과 같은 안내 문구("데이터 처리 라이브러리(pandas)를 불러오지 못해…")
- **실제:** `AttributeError: partially initialized module 'pandas'…` 오류 화면
- **원인:** 처음 불러오기에 실패하면 pandas 일부가 메모리에 반쯤 남는다. 그래서 다음 시도에서는 `ImportError`가 아닌 다른 오류가 나는데, `_load_pandas()` 호출부가 `ImportError`만 잡는다. (`pages_impl/admin.py` `render()`)
- **영향:** pandas가 정상인 배포 환경(Streamlit Cloud)에서는 생기지 않는다. 운영에서는 `showErrorDetails = "none"`이라 오류 상세도 보이지 않는다.
- **수정 제안:** 모든 예외(`Exception`)를 잡고, 첫 실패 결과를 기억해 같은 안내를 보여준다.

### #3 [보통] Google Sheets에서 행 번호로 지우거나 고칠 때 동시 작업이 겹치면 다른 행이 바뀔 수 있다
- **상황:** 관리자 두 명이 동시에 파기를 누르거나, 파기와 설정 저장이 거의 동시에 일어날 때
- **원인:** `delete_pledges_before()`와 `set_settings()`가 시트 전체를 읽어 행 번호를 계산한 뒤 그 번호로 지우거나 고친다. 그 사이에 다른 요청이 행을 지우면 번호가 밀린다. (`storage.py`)
- **영향:** 관리자가 한 명이면 사실상 일어나지 않는다. 서약서 추가(맨 아래 append)는 영향이 없다.
- **수정 제안:** 지우기 직전에 해당 행의 `id`/`key`가 맞는지 다시 확인한다. 또는 관리자 작업을 한 번에 하나만 하도록 잠근다.

### #4 [낮음] FR-2.8 "제출 중 버튼 비활성"은 구현되지 않았다
- 중복 저장 자체는 막힌다(첫 제출 뒤 입력값을 비우므로 두 번째 클릭은 검증에서 걸린다. `test_double_click_saves_once` 통과).
- 다만 네트워크가 느린 Google Sheets 저장 중에는 버튼이 눌리는 것처럼 보인다.
- **수정 제안:** 그대로 두거나, 저장 중 표시(스피너)를 추가한다.

### #5 [낮음] FR-7.6 안전교육 URL에는 "기본값으로 되돌리기" 버튼이 없다
- 칸을 비우고 저장하면 기본 주소로 돌아가므로 기능상 같지만, PRD 문구와 다르다.
- **수정 제안:** 버튼을 추가하거나, PRD에 "빈칸 저장 = 기본값"으로 적는다.

### #6 [낮음·정보] FR-5.3 "준비 중" 화면은 이제 볼 수 없다
- 사용자 요청으로 안전교육 기본 주소를 넣었기 때문이다(의도된 변경).
- 관리자가 주소를 지워도 기본 주소로 돌아간다.
- **수정 제안:** PRD FR-5.2, 5.3에 기본 주소를 반영한다.

### #7 [낮음] 휴대폰 번호 형식 검사가 느슨하다
- `0-1-0-1-2-3-4-5-6`, `---0101234567`처럼 하이픈 위치가 이상한 번호도 통과한다(숫자 9~15자리 조건만 본다).
- **수정 제안:** 하이픈 연속·앞뒤 하이픈 금지 정도만 추가한다(해외 번호 형식이 다양해서 엄격한 형식 검사는 권하지 않는다).

### #8 [낮음] 관리자 로그인에 유휴 시간 만료가 없다
- 관리자 탭을 열어 두면 계속 로그인 상태다. 공용 PC에서 쓰면 다른 사람이 기록을 볼 수 있다.
- **수정 제안:** 마지막 동작 후 30분이 지나면 자동으로 로그아웃한다.

### #9 [정보] Streamlit 기본 부품 일부가 44px보다 작다
- 사이드바 열기 버튼(28px), 휴대폰 번호 도움말 아이콘(16px). 앱이 만든 버튼은 모두 46px 이상이다.

## 4. 코드 검토 결과 (테스트 외)

| 점검 항목 | 결과 |
|---|---|
| 비밀번호·키가 코드에 있는지 | ✅ 없음. `ADMIN_PASSWORD`, 서비스 계정은 `st.secrets`로만 읽는다. `secrets.toml`은 `.gitignore`에 있다. `tests/e2e/test_secrets.toml`은 테스트 전용 가짜 비밀번호다. |
| 인증 전 관리자 데이터 노출 | ✅ 없음. `admin.render()`는 인증 전에 로그인 폼만 그리고 저장소를 읽지 않는다. 기록은 session_state에 저장하지 않는다. |
| HTML·스크립트 삽입(XSS) | ✅ `unsafe_allow_html`을 쓰지 않는다. 배너는 `html.escape`를 거친다. 안내문·서약서는 `st.markdown` 기본값(HTML 이스케이프)으로 그린다. `unsafe_allow_javascript`는 `ui.set_document_lang()` 한 곳뿐이고 `ko`/`en` 고정값만 넣는다. 로고 SVG는 스크립트·이벤트 속성을 거부하고, `<img>` data URI로만 그려서 스크립트가 실행되지 않는다(`st.image`도 data URI로 그림을 확인). |
| CSV 수식 삽입 | ✅ `=`, `+`, `-`, `@`, 탭, CR로 시작하는 값 앞에 `'`를 붙인다(`admin.csv_safe`). E2E 확인은 pandas 차단으로 못 함. |
| Google Sheets 수식 실행 | ✅ `value_input_option="RAW"`로 써서 `=…` 입력이 수식이 되지 않고 휴대폰 번호 앞자리 0이 유지된다. |
| Google Sheets 오류·네트워크 장애 | ✅ 모든 오류를 `StorageError`로 바꾼다. 방문자 화면은 기본 문구로 대신 보여주고, 제출 실패·관리자 화면은 안내 문구를 띄운다(2단계 가짜 시트 테스트로 확인). |
| 시간대 | ✅ 저장은 KST ISO 문자열(`+09:00`), 비교도 같은 형식이다. 관리자 표는 Asia/Seoul로 변환한다. |
| 동시 제출 | ✅ 서약서 추가는 SQLite 트랜잭션 / Sheets append라 서로 덮어쓰지 않는다. 파기·설정 수정의 동시성은 문제 #3 참고. |
| 개인정보 | ✅ 입력 중인 서약서 내용은 URL·브라우저 저장소에 남기지 않는다. 완료 화면에도 개인정보를 표시하지 않는다. |

## 5. 이 PC에서 검증하지 못한 항목

Windows 스마트 앱 컨트롤이 pandas·pyarrow DLL을 막아 **관리자 로그인 뒤 화면**을 실행할 수 없었습니다. WSL도 설치돼 있지 않습니다. 해당 테스트는 건너뛰지 않고 실패로 남겨 두었습니다.

- 기록 표·지표·필터·CSV 다운로드(FR-4.3~4.5)
- 1년 경과 안내·파기(FR-4.8~4.9)
- 앱 설정 화면 전체(FR-7): 안내문 수정·반영·재시작 유지·되돌리기, URL 검사, 로고 등록·삭제·불량 파일 거부
- 기록 표의 HTML 이스케이프(`test_html_in_record_is_not_rendered`는 통과했지만, 표가 그려지지 않은 상태라 **의미 있는 검증이 아닙니다**)

**검증 방법:** 아래 중 하나에서 `pytest tests/e2e/test_admin.py`를 다시 실행하면 됩니다.
- 스마트 앱 컨트롤을 끈 PC
- WSL
- Linux 서버나 CI(예: GitHub Actions)

이 기능들의 저장 로직(설정 저장·되돌리기, 로고 처리·청크 저장, URL 검사, 1년 파기)은 2단계에서 pandas 없이 단위 수준으로 확인했습니다.

## 6. 스크린샷

`tests/e2e/screenshots/`
- `desktop_{home,pledge,safety,admin}_{ko,en}.png`: PC 1280px
- `mobile_{home,pledge,safety,admin}_{ko,en}.png`: 휴대폰 375px
- `{desktop,mobile}_pledge_errors_ko.png`, `{desktop,mobile}_pledge_done_ko.png`: 오류 표시, 제출 완료

## 7. 권장 수정 순서

1. **#1 관리자 잠금 우회** (보안, 배포 전 필수)
2. **#2 pandas 오류 문구** (간단)
3. **#5, #6 PRD 정리**와 **#7 휴대폰 형식** (간단)
4. **#8 관리자 유휴 만료** (공용 PC에서 쓸 경우)
5. **#3 Sheets 동시성** (관리자가 여러 명일 경우)
6. **#4 제출 중 표시** (선택)
