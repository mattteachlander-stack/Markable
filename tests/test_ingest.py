import pytest

from markable.ingest import IngestError, ingest_markdown
from markable.models import QuestionType


def test_fixture_parses_all_types(draft_text):
    a = ingest_markdown(draft_text, assume_yes=True)
    assert a.test_id == "2026-T3-Y9-chem"
    assert a.subject == "Science"
    assert a.year_level == "9"

    by_id = {q.id: q for q in a.questions}
    assert by_id["Q1"].type is QuestionType.mcq
    assert by_id["Q2"].type is QuestionType.short_answer
    assert by_id["Q3"].type is QuestionType.numerical
    assert by_id["Q4"].type is QuestionType.extended
    assert by_id["Q5"].type is QuestionType.diagram
    # Every question type is represented.
    assert {q.type for q in a.questions} == set(QuestionType)


def test_mcq_options_and_embedded_answer(draft_text):
    a = ingest_markdown(draft_text, assume_yes=True)
    q1 = next(q for q in a.questions if q.id == "Q1")
    assert q1.options == {
        "A": "electron",
        "B": "neutron",
        "C": "proton",
        "D": "photon",
    }
    # The trailing `*` marks the correct option embedded in the draft.
    assert q1.expected_answer == "C"


def test_multipart_parent_linking(draft_text):
    a = ingest_markdown(draft_text, assume_yes=True)
    q6a = next(q for q in a.questions if q.id == "Q6a")
    q6b = next(q for q in a.questions if q.id == "Q6b")
    assert q6a.parent == "Q6"
    assert q6b.parent == "Q6"


def test_total_marks(draft_text):
    a = ingest_markdown(draft_text, assume_yes=True)
    # 1 + 2 + 3 + 6 + 3 + 2 + 2
    assert a.total_marks == 19


def test_missing_marks_prompts_resolver():
    draft = "test_id: t\n\n## Q1 [short_answer]\nDefine an atom.\n"
    seen = {}

    def resolver(qid, gap):
        seen["qid"] = qid
        seen["field"] = gap.field
        return 4

    a = ingest_markdown(draft, resolver=resolver)
    assert seen == {"qid": "Q1", "field": "marks"}
    assert a.questions[0].marks == 4


def test_missing_marks_fails_when_non_interactive():
    draft = "test_id: t\n\n## Q1 [short_answer]\nDefine an atom.\n"
    with pytest.raises(IngestError):
        ingest_markdown(draft, assume_yes=True)


def test_missing_test_id_rejected():
    with pytest.raises(IngestError):
        ingest_markdown("## Q1 [short_answer, 1]\nDefine an atom.\n", assume_yes=True)


def test_unknown_type_rejected():
    with pytest.raises(IngestError):
        ingest_markdown("test_id: t\n\n## Q1 [essay, 1]\nText.\n", assume_yes=True)
