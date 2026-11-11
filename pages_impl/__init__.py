"""화면 모듈과 화면 전환 도우미.

폴더 이름을 pages/로 하면 Streamlit이 멀티페이지 앱으로 자동 인식하므로 pages_impl/을 쓴다.
"""

import streamlit as st

from i18n import t

PAGES = ("home", "pledge", "safety", "admin")


def go(page: str) -> None:
    """현재 화면을 바꾼다. 버튼의 on_click 콜백으로 쓴다."""
    if page in PAGES:
        st.session_state["page"] = page


def home_button() -> None:
    """하위 화면 왼쪽 위에 '처음으로' 버튼을 그린다."""
    st.button(t("go_home"), key="go_home", on_click=go, args=("home",))
