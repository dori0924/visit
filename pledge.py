"""준수서약서 작성 화면 (FR-2, FR-3).

폼 값은 위젯 key(pf_*)로 session_state에 들어 있어 언어를 바꿔도 유지된다(FR-6.2).
단, 선택 상자는 브라우저가 '표시 라벨'을 돌려보내므로 언어가 바뀌면 이전 라벨(예: "미국")이
새 선택지(영문)에 없어 값이 깨진다. 그래서 선택한 코드는 pf_nat·pf_purpose에 따로 보관하고,
위젯은 언어별 key(pf_nat__ko 등)로 만들어 보관된 코드로 초기화한다(_choice 참고).
제출은 on_click 콜백에서 처리한다. 성공하면 입력값을 지우므로, 버튼을 연달아 눌러도
두 번째 콜백은 빈 값 검증에서 걸려 기록이 중복 저장되지 않는다(FR-2.8).
"""

from __future__ import annotations

import re
import uuid
from datetime import datetime

import streamlit as st

import settings
import ui
from i18n import COUNTRIES, PURPOSES, get_lang, t
from pages_impl import go, home_button
from storage import StorageError, get_storage, now_kst

FIELD_KEYS = (
    "pf_name", "pf_phone", "pf_nat", "pf_nat_other",
    "pf_purpose", "pf_purpose_other", "pf_privacy", "pf_pledge",
)
CHOICE_DEFAULTS = {"pf_nat": "KR", "pf_purpose": "meeting"}
# 맨 앞 '+'는 한 번만, 하이픈은 숫자 사이에만(연속·앞뒤 하이픈 금지). 예: 010-1234-5678, +1-202-555-0123
PHONE_RE = re.compile(r"^\+?\d+(-\d+)*$")
MAX_NAME = 50


def validate(values: dict) -> dict[str, str]:
    """입력값을 검사해 {필드: 오류 문구 키}를 돌려준다. 오류가 없으면 빈 dict."""
    errors: dict[str, str] = {}

    name = (values.get("pf_name") or "").strip()
    if not name:
        errors["pf_name"] = "err_name_required"
    elif len(name) > MAX_NAME:
        errors["pf_name"] = "err_name_long"

    phone = (values.get("pf_phone") or "").strip()
    digits = sum(c.isdigit() for c in phone)
    if not phone:
        errors["pf_phone"] = "err_phone_required"
    elif not PHONE_RE.match(phone) or not 9 <= digits <= 15:
        errors["pf_phone"] = "err_phone_format"

    for code_key, other_key, err in (
        ("pf_nat", "pf_nat_other", "err_nationality_other"),
        ("pf_purpose", "pf_purpose_other", "err_purpose_other"),
    ):
        if values.get(code_key) == "OTHER":
            other = (values.get(other_key) or "").strip()
            if not other:
                errors[other_key] = err
            elif len(other) > MAX_NAME:
                errors[other_key] = "err_other_long"

    if not values.get("pf_privacy"):
        errors["pf_privacy"] = "err_privacy"
    if not values.get("pf_pledge"):
        errors["pf_pledge"] = "err_pledge"
    return errors


def build_record(values: dict, lang: str) -> dict:
    """검증을 통과한 입력값으로 저장할 기록을 만든다. 국적·목적은 한글 이름으로 저장한다."""

    def choice(options, code_key, other_key):
        code = values.get(code_key)
        if code == "OTHER":
            return values[other_key].strip()
        return options[code][0]

    return {
        "id": str(uuid.uuid4()),
        "submitted_at": now_kst().isoformat(timespec="seconds"),
        "language": lang,
        "name": values["pf_name"].strip(),
        "phone": values["pf_phone"].strip(),
        "nationality": choice(COUNTRIES, "pf_nat", "pf_nat_other"),
        "purpose": choice(PURPOSES, "pf_purpose", "pf_purpose_other"),
        "privacy_agreed": True,
        "pledge_agreed": True,
    }


def _submit() -> None:
    """제출 버튼 콜백: 검증 → 저장 → 폼 초기화."""
    ss = st.session_state
    values = {k: ss.get(k) for k in FIELD_KEYS}
    for k, default in CHOICE_DEFAULTS.items():
        values[k] = values[k] or default
    errors = validate(values)
    if errors:
        ss["pf_errors"] = errors
        return
    record = build_record(values, get_lang())
    try:
        get_storage().save_pledge(record)
    except StorageError:
        ss["pf_errors"] = {"_save": "err_save"}
        return
    ss["pf_errors"] = {}
    ss["pf_done_at"] = record["submitted_at"]
    for k in list(ss.keys()):
        if k in FIELD_KEYS or k.startswith(tuple(f"{c}__" for c in CHOICE_DEFAULTS)):
            del ss[k]


def _sync_choice(widget_key: str, field: str) -> None:
    """언어별 선택 상자의 값을 언어와 무관한 코드 키로 옮긴다."""
    st.session_state[field] = st.session_state[widget_key]


def _choice(label: str, options: dict[str, tuple[str, str]], field: str) -> str:
    """국적·방문목적 선택 상자를 그리고 선택한 코드를 돌려준다."""
    lang = get_lang()
    codes = list(options)
    current = st.session_state.get(field) or CHOICE_DEFAULTS[field]
    widget_key = f"{field}__{lang}"
    st.selectbox(
        label,
        options=codes,
        index=codes.index(current),
        key=widget_key,
        # 언어를 그리는 시점에 고정한다(나중에 다른 언어로 호출돼도 라벨이 바뀌지 않게).
        format_func=lambda c, lang=lang: options[c][1 if lang == "en" else 0],
        on_change=_sync_choice,
        args=(widget_key, field),
    )
    st.session_state[field] = st.session_state[widget_key]
    return st.session_state[field]


def _new_pledge() -> None:
    """완료 화면에서 새 서약서를 쓰러 돌아간다."""
    st.session_state.pop("pf_done_at", None)


def _go_home_and_reset() -> None:
    """완료 화면을 닫고 첫 화면으로 간다."""
    _new_pledge()
    go("home")


def _err(field: str) -> None:
    """필드 바로 아래에 오류를 표시한다."""
    key = st.session_state.get("pf_errors", {}).get(field)
    if key:
        st.error(t(key), icon="⚠️")


def render_done() -> None:
    """제출 완료 화면."""
    submitted = datetime.fromisoformat(st.session_state["pf_done_at"])
    ui.done_card(t("done_title"), t("done_body", time=submitted.strftime("%Y-%m-%d %H:%M")))
    col1, col2 = st.columns(2)
    col1.button(t("home"), key="done_home", on_click=_go_home_and_reset,
                width="stretch")
    col2.button(t("done_new"), key="done_new", on_click=_new_pledge, width="stretch")


def render() -> None:
    """서약서 화면을 그린다."""
    home_button()
    st.header(t("pledge_title"))

    if st.session_state.get("pf_done_at"):
        render_done()
        return

    # 서약서 본문은 스크롤 카드 안에 둬서 입력 폼이 너무 아래로 밀리지 않게 한다.
    with st.container(border=True, height=320, key="pledge_text"):
        st.markdown(settings.localized("pledge", get_lang()))

    st.subheader(t("pledge_form_title"))
    st.text_input(t("f_name"), key="pf_name", max_chars=MAX_NAME)
    _err("pf_name")
    st.text_input(t("f_phone"), key="pf_phone", max_chars=20, help=t("f_phone_help"),
                  placeholder="010-1234-5678")
    _err("pf_phone")

    if _choice(t("f_nationality"), COUNTRIES, "pf_nat") == "OTHER":
        st.text_input(t("f_nationality_other"), key="pf_nat_other", max_chars=MAX_NAME)
        _err("pf_nat_other")

    if _choice(t("f_purpose"), PURPOSES, "pf_purpose") == "OTHER":
        st.text_input(t("f_purpose_other"), key="pf_purpose_other", max_chars=MAX_NAME)
        _err("pf_purpose_other")

    st.checkbox(t("f_privacy"), key="pf_privacy")
    _err("pf_privacy")
    st.checkbox(t("f_pledge"), key="pf_pledge")
    _err("pf_pledge")

    errors = st.session_state.get("pf_errors", {})
    if errors.get("_save"):
        st.error(t("err_save"))
    elif errors:
        st.warning(t("err_form"))

    st.button(t("submit"), key="pf_submit", type="primary", on_click=_submit, width="stretch")
