"""한/영 UI 문구 사전과 번역 함수.

화면 코드에는 문구를 직접 쓰지 않고 항상 t("key")로 가져온다.
안내문·서약서 본문처럼 관리자가 수정하는 긴 문구는 settings.py가 관리한다.
"""

import streamlit as st

DEFAULT_LANG = "ko"
LANGS = {"ko": "한국어", "en": "English"}

# 국적·방문목적 선택지: 코드 → (한글, 영문). 저장할 때는 한글 이름을 쓴다(관리자 열람 기준).
COUNTRIES: dict[str, tuple[str, str]] = {
    "KR": ("대한민국", "Republic of Korea"),
    "US": ("미국", "United States"),
    "CN": ("중국", "China"),
    "JP": ("일본", "Japan"),
    "VN": ("베트남", "Vietnam"),
    "PH": ("필리핀", "Philippines"),
    "TH": ("태국", "Thailand"),
    "ID": ("인도네시아", "Indonesia"),
    "IN": ("인도", "India"),
    "UZ": ("우즈베키스탄", "Uzbekistan"),
    "MN": ("몽골", "Mongolia"),
    "DE": ("독일", "Germany"),
    "GB": ("영국", "United Kingdom"),
    "FR": ("프랑스", "France"),
    "OTHER": ("기타", "Other"),
}
PURPOSES: dict[str, tuple[str, str]] = {
    "meeting": ("업무 협의", "Business meeting"),
    "work": ("공사·작업", "Construction / work"),
    "delivery": ("납품", "Delivery"),
    "tour": ("견학", "Site tour"),
    "OTHER": ("기타", "Other"),
}

STRINGS: dict[str, dict[str, str]] = {
    # 공통
    "app_title": {"ko": "방문자 안내", "en": "Visitor Guide"},
    "app_subtitle": {
        "ko": "방문해 주셔서 감사합니다. 아래 안내를 확인해 주세요.",
        "en": "Thank you for visiting. Please read the guidance below.",
    },
    "language": {"ko": "언어", "en": "Language"},
    "go_home": {"ko": "← 처음으로", "en": "← Home"},
    "home": {"ko": "처음으로", "en": "Home"},
    "storage_error": {
        "ko": "저장소에 연결하지 못했습니다. 잠시 후 다시 시도하거나 안내 데스크에 문의해 주세요.",
        "en": "Could not connect to the storage. Please try again later or ask the front desk.",
    },
    # 첫 화면
    "choose_category": {"ko": "무엇을 하시겠어요?", "en": "What would you like to do?"},
    "cat_pledge": {"ko": "📝 준수서약서 작성", "en": "📝 Sign the Compliance Pledge"},
    "cat_pledge_desc": {
        "ko": "방문 전 준수사항에 서약하고 방문 정보를 입력합니다.",
        "en": "Agree to the site rules and enter your visit details.",
    },
    "cat_safety": {"ko": "🦺 안전교육 이동", "en": "🦺 Go to Safety Training"},
    "cat_safety_desc": {
        "ko": "안전교육 페이지가 새 창으로 열립니다.",
        "en": "The safety training page opens in a new tab.",
    },
    # 서약서
    "pledge_title": {"ko": "준수서약서", "en": "Compliance Pledge"},
    "pledge_form_title": {"ko": "방문자 정보", "en": "Visitor Information"},
    "f_name": {"ko": "이름", "en": "Full name"},
    "f_phone": {"ko": "휴대폰 번호", "en": "Mobile number"},
    "f_phone_help": {
        "ko": "숫자, +, - 만 입력할 수 있습니다. 예: 010-1234-5678, +1-202-555-0123",
        "en": "Digits, + and - only. e.g. +1-202-555-0123, 010-1234-5678",
    },
    "f_nationality": {"ko": "국적", "en": "Nationality"},
    "f_nationality_other": {"ko": "국적 직접 입력", "en": "Enter your nationality"},
    "f_purpose": {"ko": "방문목적", "en": "Purpose of visit"},
    "f_purpose_other": {"ko": "방문목적 직접 입력", "en": "Enter the purpose of your visit"},
    "f_privacy": {
        "ko": "[필수] 개인정보 수집·이용에 동의합니다. (수집 항목: 이름, 휴대폰 번호, 국적, 방문목적 / 보유 기간: 1년)",
        "en": "[Required] I agree to the collection and use of my personal information. "
              "(Items: name, mobile number, nationality, purpose / Retention: 1 year)",
    },
    "f_pledge": {
        "ko": "[필수] 위 준수서약서의 내용을 확인했으며, 이를 지킬 것을 서약합니다.",
        "en": "[Required] I have read the pledge above and agree to comply with it.",
    },
    "submit": {"ko": "서약서 제출", "en": "Submit Pledge"},
    "err_name_required": {"ko": "이름을 입력해 주세요.", "en": "Please enter your name."},
    "err_name_long": {"ko": "이름은 50자 이하로 입력해 주세요.", "en": "Name must be 50 characters or fewer."},
    "err_phone_required": {"ko": "휴대폰 번호를 입력해 주세요.", "en": "Please enter your mobile number."},
    "err_phone_format": {
        "ko": "휴대폰 번호는 숫자, +, - 만 사용하여 숫자 9~15자리로 입력해 주세요.",
        "en": "Use digits, + and - only, with 9 to 15 digits in total.",
    },
    "err_nationality_other": {"ko": "국적을 입력해 주세요.", "en": "Please enter your nationality."},
    "err_purpose_other": {"ko": "방문목적을 입력해 주세요.", "en": "Please enter the purpose of your visit."},
    "err_other_long": {"ko": "50자 이하로 입력해 주세요.", "en": "Please use 50 characters or fewer."},
    "err_privacy": {
        "ko": "개인정보 수집·이용에 동의해야 제출할 수 있습니다.",
        "en": "You must agree to the collection and use of personal information.",
    },
    "err_pledge": {
        "ko": "준수서약서에 동의해야 제출할 수 있습니다.",
        "en": "You must agree to the pledge.",
    },
    "err_form": {"ko": "입력 내용을 확인해 주세요.", "en": "Please check the highlighted fields."},
    "err_save": {
        "ko": "제출하지 못했습니다. 잠시 후 다시 시도해 주세요.",
        "en": "Submission failed. Please try again in a moment.",
    },
    "done_title": {"ko": "서약서가 제출되었습니다.", "en": "Your pledge has been submitted."},
    "done_body": {
        "ko": "제출 일시: {time}\n\n협조해 주셔서 감사합니다. 안전한 방문 되세요.",
        "en": "Submitted at: {time} (KST)\n\nThank you for your cooperation. Have a safe visit.",
    },
    "done_new": {"ko": "새 서약서 작성", "en": "Submit another pledge"},
    # 안전교육
    "safety_title": {"ko": "안전교육", "en": "Safety Training"},
    "safety_body": {
        "ko": "아래 버튼을 누르면 안전교육 페이지가 새 창으로 열립니다. 교육을 마친 뒤 이 화면으로 돌아오세요.",
        "en": "Press the button below to open the safety training in a new tab. Come back here when you finish.",
    },
    "safety_open": {"ko": "안전교육 시작하기 ↗", "en": "Start Safety Training ↗"},
    "safety_not_ready": {
        "ko": "안전교육 페이지는 준비 중입니다. 안내 데스크에 문의해 주세요.",
        "en": "The safety training page is not ready yet. Please ask the front desk.",
    },
    # 관리자 — 인증
    "admin_menu": {"ko": "🔐 관리자", "en": "🔐 Admin"},
    "admin_title": {"ko": "관리자", "en": "Administrator"},
    "admin_password": {"ko": "관리자 비밀번호", "en": "Admin password"},
    "admin_login": {"ko": "로그인", "en": "Log in"},
    "admin_logout": {"ko": "로그아웃", "en": "Log out"},
    "admin_wrong": {
        "ko": "비밀번호가 올바르지 않습니다. (남은 시도: {left}회)",
        "en": "Incorrect password. ({left} attempts left)",
    },
    "admin_locked": {
        "ko": "비밀번호를 여러 번 틀려 잠겼습니다. {minutes}분 후 다시 시도해 주세요.",
        "en": "Too many failed attempts. Try again in {minutes} minute(s).",
    },
    "admin_idle_logout": {
        "ko": "{minutes}분 동안 사용하지 않아 자동으로 로그아웃되었습니다. 다시 로그인해 주세요.",
        "en": "You were logged out after {minutes} minutes of inactivity. Please log in again.",
    },
    "admin_no_password": {
        "ko": "관리자 비밀번호가 설정되지 않았습니다. Secrets에 ADMIN_PASSWORD를 추가해 주세요.",
        "en": "The admin password is not configured. Add ADMIN_PASSWORD to Secrets.",
    },
    "admin_pandas_error": {
        "ko": "이 컴퓨터에서 데이터 처리 라이브러리(pandas)를 불러오지 못해 관리자 화면을 열 수 없습니다. "
              "Windows 스마트 앱 컨트롤이 켜져 있으면 차단될 수 있습니다. 배포된 앱에서는 정상 동작합니다.",
        "en": "The data library (pandas) could not be loaded on this computer, so the admin screen is unavailable. "
              "Windows Smart App Control may be blocking it. The deployed app is not affected.",
    },
    "metric_total": {"ko": "전체 기록", "en": "Total records"},
    "metric_today": {"ko": "오늘 방문자", "en": "Visitors today"},
    "metric_expired": {"ko": "파기 대상", "en": "To be destroyed"},
    "tab_records": {"ko": "📋 서약서 기록", "en": "📋 Pledge Records"},
    "tab_settings": {"ko": "⚙️ 앱 설정", "en": "⚙️ App Settings"},
    # 관리자 — 기록
    "col_submitted_at": {"ko": "제출 일시", "en": "Submitted at"},
    "col_language": {"ko": "언어", "en": "Language"},
    "col_name": {"ko": "이름", "en": "Name"},
    "col_phone": {"ko": "휴대폰", "en": "Mobile"},
    "col_nationality": {"ko": "국적", "en": "Nationality"},
    "col_purpose": {"ko": "방문목적", "en": "Purpose"},
    "col_privacy_agreed": {"ko": "개인정보 동의", "en": "Privacy consent"},
    "col_pledge_agreed": {"ko": "서약 동의", "en": "Pledge consent"},
    "col_id": {"ko": "ID", "en": "ID"},
    "filter_dates": {"ko": "제출일 범위", "en": "Date range"},
    "filter_name": {"ko": "이름 검색", "en": "Search name"},
    "filter_nationality": {"ko": "국적", "en": "Nationality"},
    "filter_purpose": {"ko": "방문목적", "en": "Purpose"},
    "filter_all": {"ko": "전체 (선택하면 해당 항목만)", "en": "All (pick to filter)"},
    "records_count": {"ko": "조회 결과 {n}건 / 전체 {total}건", "en": "{n} of {total} records"},
    "records_empty": {"ko": "아직 제출된 서약서가 없습니다.", "en": "No pledges have been submitted yet."},
    "download_csv": {"ko": "⬇️ CSV 다운로드", "en": "⬇️ Download CSV"},
    "retention_title": {"ko": "보유 기간 경과 기록 (1년)", "en": "Records past retention (1 year)"},
    "retention_banner": {
        "ko": "보유 기간(1년)이 지난 기록이 {n}건 있습니다. '서약서 기록' 탭 아래에서 파기해 주세요.",
        "en": "{n} record(s) are past the 1-year retention period. Destroy them at the bottom of the Records tab.",
    },
    "retention_none": {"ko": "파기할 기록이 없습니다.", "en": "No records to destroy."},
    "retention_confirm": {
        "ko": "{n}건을 영구 삭제하는 것에 동의합니다. (되돌릴 수 없습니다)",
        "en": "I confirm permanent deletion of {n} record(s). (This cannot be undone)",
    },
    "retention_button": {"ko": "🗑️ 보유 기간 경과 기록 파기", "en": "🗑️ Destroy expired records"},
    "retention_done": {"ko": "{n}건을 파기했습니다.", "en": "{n} record(s) destroyed."},
    # 관리자 — 설정
    "settings_updated": {"ko": "마지막 수정: {time}", "en": "Last updated: {time}"},
    "settings_never": {"ko": "아직 수정한 설정이 없습니다(기본값 사용 중).", "en": "No changes yet (using defaults)."},
    "set_notice": {"ko": "첫 화면 안내문", "en": "Home screen notice"},
    "set_pledge": {"ko": "서약서 본문", "en": "Pledge text"},
    "set_lang_ko": {"ko": "한글", "en": "Korean"},
    "set_lang_en": {"ko": "영문", "en": "English"},
    "set_markdown_help": {
        "ko": "마크다운을 쓸 수 있습니다. (### 제목, - 목록, **굵게**)",
        "en": "Markdown is supported. (### heading, - list, **bold**)",
    },
    "set_preview": {"ko": "미리보기", "en": "Preview"},
    "set_save": {"ko": "저장", "en": "Save"},
    "set_reset": {"ko": "기본값으로 되돌리기", "en": "Reset to default"},
    "set_saved": {"ko": "저장했습니다.", "en": "Saved."},
    "set_reset_done": {"ko": "기본값으로 되돌렸습니다.", "en": "Reset to default."},
    "set_using_default": {"ko": "현재 기본값 사용 중", "en": "Currently using the default"},
    "set_err_empty": {"ko": "내용이 비어 있습니다. 기본값을 쓰려면 '기본값으로 되돌리기'를 누르세요.",
                      "en": "The text is empty. Use 'Reset to default' to restore the default."},
    "set_err_long": {"ko": "20,000자 이하로 입력해 주세요.", "en": "Please use 20,000 characters or fewer."},
    "set_safety": {"ko": "안전교육 페이지 주소", "en": "Safety training URL"},
    "set_safety_ko": {"ko": "한글용 URL (비우면 기본 주소 사용)", "en": "URL (Korean, empty = default URL)"},
    "set_safety_en": {"ko": "영문용 URL (비우면 한글용 URL 사용)", "en": "URL (English, falls back to Korean if empty)"},
    "set_url_invalid": {
        "ko": "주소는 http:// 또는 https:// 로 시작해야 합니다.",
        "en": "The URL must start with http:// or https://.",
    },
    "set_logo": {"ko": "회사 로고", "en": "Company logo"},
    "set_logo_help": {
        "ko": "PNG, JPG, SVG (2MB 이하). 가로 400px보다 크면 자동으로 줄입니다.",
        "en": "PNG, JPG or SVG (up to 2MB). Images wider than 400px are resized.",
    },
    "set_logo_current": {"ko": "현재 로고", "en": "Current logo"},
    "set_logo_none": {"ko": "등록된 로고가 없습니다.", "en": "No logo uploaded."},
    "set_logo_upload": {"ko": "로고 등록", "en": "Upload logo"},
    "set_logo_delete": {"ko": "로고 삭제", "en": "Delete logo"},
    "set_logo_deleted": {"ko": "로고를 삭제했습니다.", "en": "Logo deleted."},
    "set_logo_pick": {"ko": "먼저 파일을 선택해 주세요.", "en": "Choose a file first."},
    "logo_err_size": {"ko": "파일이 2MB를 넘습니다.", "en": "The file is larger than 2MB."},
    "logo_err_svg_size": {"ko": "SVG 파일은 200KB 이하만 등록할 수 있습니다.", "en": "SVG files must be 200KB or smaller."},
    "logo_err_invalid": {
        "ko": "PNG, JPG, SVG 이미지 파일만 등록할 수 있습니다.",
        "en": "Only PNG, JPG and SVG images are allowed.",
    },
    "logo_err_unsafe": {
        "ko": "스크립트가 들어 있는 SVG는 등록할 수 없습니다.",
        "en": "SVG files containing scripts are not allowed.",
    },
}


def get_lang() -> str:
    """현재 선택된 언어 코드(ko/en)를 돌려준다."""
    lang = st.session_state.get("lang", DEFAULT_LANG)
    return lang if lang in LANGS else DEFAULT_LANG


def t(key: str, **kwargs) -> str:
    """현재 언어의 문구를 돌려준다. 키가 없으면 키 자체를 돌려줘 누락을 드러낸다."""
    entry = STRINGS.get(key)
    if entry is None:
        return key
    text = entry.get(get_lang()) or entry.get(DEFAULT_LANG, key)
    return text.format(**kwargs) if kwargs else text
