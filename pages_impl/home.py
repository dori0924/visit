"""첫 화면: 방문자 기본 안내와 카테고리 선택 (FR-1)."""

import streamlit as st

import settings
import ui
from i18n import get_lang, t
from pages_impl import go


def render() -> None:
    """첫 화면을 그린다. 안내문은 카드로, 카테고리는 큰 카드형 버튼으로 보여준다."""
    lang = get_lang()
    ui.notice_cards(settings.localized("notice", lang))

    st.subheader(t("choose_category"))
    col1, col2 = st.columns(2)
    with col1, st.container(key="cat_card_pledge"):
        st.button(t("cat_pledge"), key="cat_pledge", type="primary", on_click=go,
                  args=("pledge",), width="stretch")
        st.caption(t("cat_pledge_desc"))
    with col2, st.container(key="cat_card_safety"):
        # URL이 있으면 한 번에 안전교육 새 창을 연다(FR-5.1). 없으면 '준비 중' 화면으로 보낸다.
        url = settings.safety_url(lang)
        if url:
            st.link_button(t("cat_safety"), url, width="stretch")
        else:
            st.button(t("cat_safety"), key="cat_safety", on_click=go, args=("safety",),
                      width="stretch")
        st.caption(t("cat_safety_desc"))
