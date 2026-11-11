"""방문자 안내 앱 진입점: 공통 헤더, 언어 선택, 사이드바, 화면 전환."""

import streamlit as st

import settings
import ui
from i18n import LANGS, DEFAULT_LANG, t
from pages_impl import PAGES, admin, go, home, pledge, safety

st.set_page_config(page_title="Visitor Guide", page_icon="🏢", layout="centered",
                   initial_sidebar_state="collapsed")

ROUTES = {
    "home": home.render,
    "pledge": pledge.render,
    "safety": safety.render,
    "admin": admin.render,
}


def init_state() -> None:
    """세션 상태 기본값을 채운다.

    새로고침하면 세션이 새로 시작되므로, 보던 화면과 언어는 URL(?page=…&lang=…)에서 되살린다.
    입력 중인 서약서 내용(개인정보)과 관리자 로그인은 URL에 남기지 않는다.
    """
    ss, qp = st.session_state, st.query_params
    if "page" not in ss:
        ss["page"] = qp.get("page") if qp.get("page") in PAGES else "home"
    if "lang" not in ss:
        ss["lang"] = qp.get("lang") if qp.get("lang") in LANGS else DEFAULT_LANG


def sync_url() -> None:
    """현재 화면과 언어를 URL에 적어 둔다(새로고침해도 유지되게)."""
    for key in ("page", "lang"):
        if st.query_params.get(key) != st.session_state[key]:
            st.query_params[key] = st.session_state[key]


def render_header() -> None:
    """오른쪽 위 언어 선택과 로고·제목 배너를 그린다.

    언어 선택은 session_state['lang']에 바로 반영된다. 부제(환영 문구)는 첫 화면에만 둔다.
    """
    with st.container(horizontal=True, horizontal_alignment="right"):
        st.selectbox(
            t("language"),
            options=list(LANGS),
            format_func=LANGS.get,
            key="lang",
            width=150,
            label_visibility="collapsed",
        )
    subtitle = t("app_subtitle") if st.session_state["page"] == "home" else None
    ui.banner(t("app_title"), subtitle, settings.get_logo())


def render_sidebar() -> None:
    """사이드바에 관리자 메뉴를 그린다."""
    with st.sidebar:
        st.button(t("admin_menu"), key="admin_menu", on_click=go, args=("admin",),
                  width="stretch")


def main() -> None:
    """현재 화면을 그린다."""
    init_state()
    sync_url()
    ui.inject_css()
    ui.set_document_lang(st.session_state["lang"])
    render_header()
    render_sidebar()
    ROUTES.get(st.session_state["page"], home.render)()


main()
