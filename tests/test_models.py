import pytest
from pydantic import ValidationError

from markable.models import Assessment, Question, QuestionType


def _q(qid: str, marks: int = 1, **kw) -> Question:
    kw.setdefault("type", QuestionType.short_answer)
    return Question(id=qid, marks=marks, **kw)


def test_total_marks_sums_questions():
    a = Assessment(test_id="t", questions=[_q("Q01", 2), _q("Q02", 3)])
    assert a.total_marks == 5


def test_duplicate_ids_rejected():
    with pytest.raises(ValidationError):
        Assessment(test_id="t", questions=[_q("Q01"), _q("Q01")])


def test_mcq_requires_options():
    with pytest.raises(ValidationError):
        Question(id="Q01", type=QuestionType.mcq, marks=1)
    ok = Question(id="Q01", type=QuestionType.mcq, marks=1, options={"A": "x", "B": "y"})
    assert ok.options["A"] == "x"


def test_negative_marks_rejected():
    with pytest.raises(ValidationError):
        _q("Q01", marks=-1)
