"""안전교육 시험 문제의 읽기와 채점 (FR-5).

관리자가 텍스트 편집창에서 고칠 수 있도록 문제는 아래와 같은 간단한 글 형식으로 둔다.

    1. 사업장 안에서 사진을 찍어도 되나요?
    - 자유롭게 찍어도 된다
    * 담당자의 사전 승인 없이는 찍을 수 없다

- 문제: '-'·'*'로 시작하지 않는 줄. 앞의 번호("1.", "1)", "Q1.")는 떼어 낸다.
- 보기: '- '로 시작하면 오답, '* '로 시작하면 정답. 문제마다 보기 2개 이상, 정답은 정확히 1개.
- 빈 줄과 '#'로 시작하는 줄(메모)은 무시한다.
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass

MAX_QUESTIONS = 30
MAX_OPTIONS = 8

NUMBER_RE = re.compile(r"^(?:Q\s*)?\d+\s*[.)]\s*", re.IGNORECASE)


@dataclass(frozen=True)
class Question:
    text: str
    options: tuple[str, ...]
    answer: int  # 정답 보기의 위치(0부터)


class QuizError(ValueError):
    """문제 형식이 올바르지 않음. args[0]은 i18n 키, line은 문제가 있는 줄 번호(1부터, 없으면 0)."""

    def __init__(self, key: str, line: int = 0):
        super().__init__(key)
        self.line = line


def parse(text: str) -> list[Question]:
    """문제 글을 Question 목록으로 바꾼다. 형식이 틀리면 QuizError."""
    questions: list[Question] = []
    current: dict | None = None

    def close() -> None:
        if current is None:
            return
        line = current["line"]
        if len(current["options"]) < 2:
            raise QuizError("quiz_err_options", line)
        if len(current["answers"]) != 1:
            raise QuizError("quiz_err_answer", line)
        questions.append(Question(current["text"], tuple(current["options"]), current["answers"][0]))

    for no, raw in enumerate(text.splitlines(), start=1):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if line[0] in "-*":
            option = line[1:].strip()
            if current is None:
                raise QuizError("quiz_err_orphan", no)
            if not option:
                raise QuizError("quiz_err_empty_option", no)
            if len(current["options"]) >= MAX_OPTIONS:
                raise QuizError("quiz_err_too_many_options", no)
            if line[0] == "*":
                current["answers"].append(len(current["options"]))
            current["options"].append(option)
            continue
        close()
        if len(questions) >= MAX_QUESTIONS:
            raise QuizError("quiz_err_too_many", no)
        current = {"text": NUMBER_RE.sub("", line) or line, "options": [], "answers": [], "line": no}
    close()
    if not questions:
        raise QuizError("quiz_err_none")
    return questions


def grade(questions: list[Question], answers: list[int | None]) -> list[int]:
    """틀린(또는 답하지 않은) 문제의 위치 목록을 돌려준다. 빈 목록이면 100점."""
    return [i for i, q in enumerate(questions) if i >= len(answers) or answers[i] != q.answer]


def score(questions: list[Question], wrong: list[int]) -> int:
    """100점 만점 점수(반올림)."""
    if not questions:
        return 0
    return round(100 * (len(questions) - len(wrong)) / len(questions))


def signature(text: str, lang: str) -> str:
    """문제 글과 언어의 짧은 지문. 문제가 바뀌면 이전 답·결과를 쓰지 않도록 위젯 key에 넣는다."""
    return hashlib.sha1(f"{lang}\n{text}".encode()).hexdigest()[:10]
