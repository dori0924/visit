"""안전교육 화면: 학습 내용 → 시험 → 채점 (FR-5).

학습 내용과 시험 문제는 관리자 설정(safety_*, quiz_*)에서 가져온다.
답은 위젯 key quiz_ans_<지문>_<번호>에 둔다. 지문(quiz.signature)은 언어와 문제 글로 만들므로,
언어를 바꾸거나 관리자가 문제를 고치면 이전 답·결과가 새 문제에 섞이지 않는다.
채점 결과는 session_state["quiz_results"][지문]에 두고, 저장소에는 남기지 않는다.
통과하면 그 날짜를 PASSED_KEY에 둔다. 이 값은 언어나 문제가 바뀌어도 유지되고, 통과 화면에서
서약서의 이름·휴대폰(VISITOR_KEY)과 함께 안전관리 필증으로 보여준다(FR-5.7).
"""

from __future__ import annotations

import logging

import streamlit as st

import quiz
import settings
import ui
from i18n import get_lang, t
from pages_impl import PASSED_KEY, VISITOR_KEY, go, home_button
from storage import now_kst

log = logging.getLogger(__name__)

ANSWER_PREFIX = "quiz_ans_"


def load_questions(lang: str) -> tuple[list[quiz.Question], str]:
    """해당 언어의 시험 문제와 지문. 저장된 문제가 깨져 있으면 기본 문제를 쓴다."""
    text = settings.localized("quiz", lang)
    try:
        return quiz.parse(text), quiz.signature(text, lang)
    except quiz.QuizError:
        log.exception("저장된 시험 문제를 읽지 못해 기본 문제를 사용합니다: %s", lang)
        text = settings.default(f"quiz_{lang}")
        return quiz.parse(text), quiz.signature(text, lang)


def _answer_key(sig: str, i: int) -> str:
    return f"{ANSWER_PREFIX}{sig}_{i}"


def _grade(lang: str) -> None:
    """제출 버튼 콜백: 모두 답했는지 확인하고 채점한다."""
    ss = st.session_state
    questions, sig = load_questions(lang)
    answers = [ss.get(_answer_key(sig, i)) for i in range(len(questions))]
    results = ss.setdefault("quiz_results", {})
    if any(a is None for a in answers):
        results[sig] = {**results.get(sig, {}), "missing": True}
        return
    wrong = quiz.grade(questions, answers)
    results[sig] = {"wrong": wrong, "missing": False}
    if not wrong:
        ss[PASSED_KEY] = now_kst().date().isoformat()


def _retake(sig: str) -> None:
    """결과와 답을 지우고 처음부터 다시 푼다."""
    ss = st.session_state
    ss.pop(PASSED_KEY, None)
    ss.get("quiz_results", {}).pop(sig, None)
    for k in [k for k in ss.keys() if k.startswith(f"{ANSWER_PREFIX}{sig}_")]:
        del ss[k]


def _go_home() -> None:
    go("home")


def _go_pledge() -> None:
    go("pledge")


def render_certificate() -> None:
    """안전관리 필증. 이 세션에서 제출한 서약서가 없으면 서약서를 먼저 쓰도록 안내한다."""
    visitor = st.session_state.get(VISITOR_KEY)
    if not visitor:
        st.info(t("cert_need_pledge"))
        st.button(t("cat_pledge"), key="cert_pledge", type="primary", on_click=_go_pledge,
                  width="stretch")
        return
    ui.certificate(
        t("cert_title"),
        [(t("cert_name"), visitor["name"]), (t("cert_phone"), visitor["phone"]),
         (t("cert_date"), st.session_state[PASSED_KEY])],
        t("cert_footer"),
    )


def render_passed(sig: str, total: int) -> None:
    """통과 화면: 완료 카드 + 안전관리 필증."""
    ui.done_card(t("quiz_passed_title"), t("quiz_passed_body", total=total))
    render_certificate()
    col1, col2 = st.columns(2)
    col1.button(t("home"), key="quiz_home", on_click=_go_home, width="stretch")
    col2.button(t("quiz_retake"), key="quiz_retake_passed", on_click=_retake, args=(sig,),
                width="stretch")


def render_quiz(questions: list[quiz.Question], sig: str, lang: str, result: dict) -> None:
    """시험 문제 폼. 직전 채점에서 틀린 문제에는 표시를 붙인다."""
    wrong = set(result.get("wrong", []))
    st.subheader(t("quiz_title"))
    st.caption(t("quiz_desc", n=len(questions)))
    with st.form("quiz_form", border=False):
        for i, q in enumerate(questions):
            with st.container(key=f"quiz_q_{i}"):
                st.radio(
                    f"{i + 1}. {q.text}",
                    options=list(range(len(q.options))),
                    format_func=lambda j, opts=q.options: opts[j],
                    index=None,
                    key=_answer_key(sig, i),
                )
                if i in wrong:
                    st.error(t("quiz_wrong_mark"), icon="❌")
        if result.get("missing"):
            st.warning(t("quiz_unanswered"))
        elif "wrong" in result:
            st.error(t("quiz_failed", score=quiz.score(questions, result["wrong"]),
                       wrong=len(wrong), total=len(questions)))
        st.form_submit_button(t("quiz_submit"), type="primary", on_click=_grade, args=(lang,),
                              width="stretch")


def render() -> None:
    """안전교육 화면을 그린다."""
    home_button()
    st.header(t("safety_title"))
    lang = get_lang()
    questions, sig = load_questions(lang)
    result = st.session_state.get("quiz_results", {}).get(sig, {})

    if st.session_state.get(PASSED_KEY):
        render_passed(sig, len(questions))
        return

    ui.notice_cards(settings.localized("safety", lang))
    st.divider()
    render_quiz(questions, sig, lang, result)
