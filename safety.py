"""안전교육 이동 화면 (FR-5)."""

import streamlit as st

import settings
from i18n import get_lang, t
from pages_impl import home_button


def render() -> None:
    """안전교육 화면을 그린다. URL이 없으면 '준비 중'을 보여준다."""
    home_button()
    st.header(t("safety_title"))
    url = settings.safety_url(get_lang())
    if not url:
        st.warning(t("safety_not_ready"))
        return
    with st.container(key="cat_card_safety_page"):
        st.markdown(t("safety_body"))
        st.link_button(t("safety_open"), url, type="primary", width="stretch")
