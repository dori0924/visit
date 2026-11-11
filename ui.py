"""화면 꾸밈 전용 모듈: 공통 CSS, 상단 배너, 안내 카드.

CSS는 이 파일에만 둔다. 특정 영역은 st.container(key="...")가 붙여 주는
.st-key-<key> 클래스로 꾸민다(카드: notice_*, cat_card_*, pledge_text, done_card).
"""

from __future__ import annotations

import base64
import html
import re

import streamlit as st

BLUE = "#1E63D6"
BLUE_LIGHT = "#4A90E2"
SKY = "#EEF4FD"
NAVY = "#1A2B4A"

CSS = f"""
<style>
/* ── 기본 메뉴 숨김 (사이드바 열기 버튼은 남긴다) ── */
#MainMenu, footer, [data-testid="stToolbarActions"], [data-testid="stAppDeployButton"],
[data-testid="stDecoration"], [data-testid="stStatusWidget"] {{ display: none !important; }}
header[data-testid="stHeader"] {{ background: transparent; }}
/* set_document_lang()의 스크립트 요소가 빈 줄을 차지하지 않게 */
[data-testid="stElementContainer"]:has(script) {{ display: none; }}

/* ── 본문 폭·여백 ── */
[data-testid="stMainBlockContainer"] {{ max-width: 760px; padding-top: 2.5rem; padding-bottom: 4rem; }}
[data-testid="stMarkdownContainer"] {{ overflow-wrap: anywhere; }}
[data-testid="stMarkdownContainer"] p, [data-testid="stMarkdownContainer"] li {{ font-size: 1rem; line-height: 1.65; }}

/* ── 상단 배너 ── */
.vg-banner {{
  background: linear-gradient(120deg, {BLUE} 0%, #2A6EDB 55%, {BLUE_LIGHT} 100%);
  color: #fff; border-radius: 20px; padding: 24px 26px;
  display: flex; align-items: center; gap: 18px;
  box-shadow: 0 10px 28px rgba(30, 99, 214, .25);
}}
.vg-banner .vg-logo {{
  flex: none; background: #fff; border-radius: 12px; padding: 8px 10px;
  display: flex; align-items: center; box-shadow: 0 2px 8px rgba(0, 0, 0, .12);
}}
.vg-banner .vg-logo img {{ display: block; max-height: 44px; max-width: 140px; }}
.vg-banner .vg-title {{ font-size: 1.75rem; font-weight: 700; line-height: 1.25; margin: 0; color: #fff; }}
.vg-banner .vg-sub {{ font-size: 1rem; margin: 6px 0 0; color: #fff; }}

/* ── 강조 문구 (안내문의 > 인용) ── */
[data-testid="stMarkdownContainer"] blockquote {{
  border-left: 5px solid {BLUE} !important; background: #E3EDFC; color: {NAVY} !important;
  border-radius: 12px; padding: 12px 16px; margin: 4px 0 12px; opacity: 1 !important;
}}
[data-testid="stMarkdownContainer"] blockquote p {{ margin: 0; color: {NAVY} !important; }}

/* ── 안내 카드 ── */
[class*="st-key-notice_"] {{
  background: {SKY}; border: 1px solid #D6E4FA; border-radius: 16px; padding: 16px 18px; height: 100%;
}}
[class*="st-key-notice_"] h4 {{ font-size: 1.08rem; font-weight: 700; padding: 0 0 6px; color: {NAVY}; }}
[class*="st-key-notice_"] ul {{ padding-left: 1.1rem; margin-bottom: 0; }}
[class*="st-key-notice_"] li {{ font-size: 0.97rem !important; }}

/* ── 카테고리 카드 버튼 ── */
[class*="st-key-cat_card_"] {{
  background: #fff; border: 1px solid #D6E4FA; border-radius: 20px; padding: 18px;
  box-shadow: 0 4px 14px rgba(26, 43, 74, .08);
  transition: transform .15s ease, box-shadow .15s ease;
}}
[class*="st-key-cat_card_"]:hover {{ transform: translateY(-3px); box-shadow: 0 12px 26px rgba(30, 99, 214, .18); }}
[class*="st-key-cat_card_"] button, [class*="st-key-cat_card_"] a {{ min-height: 68px; border-radius: 14px; }}
[class*="st-key-cat_card_"] button p, [class*="st-key-cat_card_"] a p {{ font-size: 1.15rem; font-weight: 700; }}
@media (prefers-reduced-motion: reduce) {{
  [class*="st-key-cat_card_"], [class*="st-key-cat_card_"]:hover {{ transition: none; transform: none; }}
}}

/* ── 터치 영역 44px 이상 ── */
.stButton button, .stLinkButton a, .stDownloadButton button, .stFormSubmitButton button {{
  min-height: 46px; border-radius: 12px; font-weight: 600;
}}
[data-baseweb="input"], [data-baseweb="select"] > div, [data-baseweb="textarea"] {{ min-height: 46px; }}
.stCheckbox label {{ min-height: 44px; align-items: center; }}

/* ── Streamlit 기본 부품의 터치 영역 44px (#9) ── */
[data-testid="stExpandSidebarButton"], [data-testid="stSidebarCollapseButton"] button {{
  min-width: 44px; min-height: 44px;
}}
[data-testid="stTooltipHoverTarget"], [data-testid="stTooltipIcon"] {{
  min-width: 44px; min-height: 44px; display: inline-flex; align-items: center; justify-content: center;
}}

/* ── 처리 중에는 제출·저장 버튼을 누를 수 없게 하고 회전 표시 (#4) ──
   Streamlit이 실행 중이면 stApp에 data-test-script-state="running"을 붙인다. */
.stApp[data-test-script-state="running"] :is(.st-key-pf_submit, [class*="st-key-save_"],
  .st-key-retention_btn, .st-key-logo_upload) button {{
  pointer-events: none; opacity: .7; cursor: progress;
}}
.stApp[data-test-script-state="running"] :is(.st-key-pf_submit, [class*="st-key-save_"],
  .st-key-retention_btn, .st-key-logo_upload) button::after {{
  content: ""; width: 1em; height: 1em; margin-left: .6em; border-radius: 50%;
  border: 2px solid currentColor; border-right-color: transparent;
  display: inline-block; animation: vg-spin .7s linear infinite;
}}
@keyframes vg-spin {{ to {{ transform: rotate(360deg); }} }}

/* ── '처음으로' 버튼: 왼쪽 위, 글자형 ── */
.st-key-go_home button {{
  background: transparent; border: none; color: {BLUE}; padding-left: 4px; box-shadow: none;
}}
.st-key-go_home button:hover {{ background: {SKY}; color: {BLUE}; }}

/* ── 서약서 본문 카드 ── */
.st-key-pledge_text {{ background: #F7FAFF; }}
.st-key-pledge_text h3 {{ font-size: 1.2rem; }}

/* ── 제출 완료 ── */
.st-key-done_card {{
  text-align: center; background: {SKY}; border-radius: 20px; padding: 32px 20px;
}}
.vg-done-icon {{
  width: 88px; height: 88px; border-radius: 50%; background: #1B873F; color: #fff;
  font-size: 50px; line-height: 88px; font-weight: 700; margin: 0 auto 14px;
}}
.vg-done-title {{ font-size: 1.45rem; font-weight: 700; color: {NAVY}; margin: 0 0 8px; }}

/* ── 관리자 지표 카드 ── */
[data-testid="stMetric"] {{ background: {SKY}; border-radius: 16px; padding: 14px 16px; }}

/* ── 휴대폰 ── */
@media (max-width: 640px) {{
  [data-testid="stMainBlockContainer"] {{ padding: 1.75rem 16px 3rem; }}
  .vg-banner {{ padding: 18px; border-radius: 16px; gap: 12px; }}
  .vg-banner .vg-title {{ font-size: 1.4rem; }}
  .vg-banner .vg-logo img {{ max-height: 34px; max-width: 96px; }}
}}
</style>
"""


def inject_css() -> None:
    """공통 CSS를 넣는다. 실행마다 호출해야 한다."""
    st.html(CSS)


def set_document_lang(lang: str) -> None:
    """<html lang>을 현재 언어로 맞추고 브라우저 자동 번역을 끈다.

    Streamlit은 언어와 상관없이 lang="en"으로 고정한다. 그러면 크롬 등이 페이지를 영어로 보고
    자동 번역을 띄우거나 실행해서, 앱이 직접 보여주는 영문·한글 화면이 기계 번역으로 바뀐다.
    lang은 화이트리스트 값만 넣는다(스크립트에 사용자 입력이 들어가지 않게).
    """
    code = "en" if lang == "en" else "ko"
    st.html(
        "<script>(() => {"
        "const root = document.documentElement;"
        f"root.lang = '{code}';"
        "root.setAttribute('translate', 'no');"
        "root.classList.add('notranslate');"
        "if (!document.querySelector('meta[name=\"google\"]')) {"
        "  const m = document.createElement('meta'); m.name = 'google'; m.content = 'notranslate';"
        "  document.head.appendChild(m);"
        "}"
        "})();</script>",
        unsafe_allow_javascript=True,
    )


def banner(title: str, subtitle: str | None = None, logo: tuple[bytes, str] | None = None) -> None:
    """로고·제목·부제를 파랑 그라데이션 배너로 그린다.

    로고는 data URI <img>로 넣는다. <img> 안의 SVG는 스크립트가 실행되지 않는다.
    """
    logo_html = ""
    if logo:
        data, mime = logo
        uri = f"data:{mime};base64,{base64.b64encode(data).decode('ascii')}"
        logo_html = f'<div class="vg-logo"><img src="{uri}" alt="logo"></div>'
    sub_html = f'<p class="vg-sub">{html.escape(subtitle)}</p>' if subtitle else ""
    st.html(
        f'<div class="vg-banner" role="banner">{logo_html}'
        f'<div><p class="vg-title" role="heading" aria-level="1">{html.escape(title)}</p>{sub_html}</div></div>'
    )


def notice_cards(markdown_text: str) -> None:
    """안내문을 '#### 제목' 단위 카드로 나눠 2열로 그린다(휴대폰에서는 세로로 쌓인다).

    '#### '가 없는 안내문(관리자가 자유롭게 고친 경우)은 그대로 그린다.
    """
    parts = re.split(r"(?m)^####\s+", markdown_text)
    intro, sections = parts[0], parts[1:]
    if intro.strip():
        st.markdown(intro)
    for row in range(0, len(sections), 2):
        cols = st.columns(2)
        for offset, col in enumerate(cols):
            i = row + offset
            if i >= len(sections):
                break
            with col, st.container(key=f"notice_{i}"):
                st.markdown("#### " + sections[i])


def done_card(title: str, body: str) -> None:
    """제출 완료 카드(큰 체크 아이콘)."""
    with st.container(key="done_card"):
        st.html(
            '<div class="vg-done-icon" aria-hidden="true">✓</div>'
            f'<p class="vg-done-title" role="status">{html.escape(title)}</p>'
        )
        st.markdown(body)
