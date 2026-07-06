"""Report tests — synthetic judgements through results, item analysis, and the
star-schema export."""

import csv
import json

import pytest
import yaml

from markable.build import build_package
from markable.ingest import ingest_markdown
from markable.models import Judgement, JudgementStatus, MarkRun
from markable.report import run_report


def _j(student, question, awarded, available, status=JudgementStatus.marked, option=None):
    return Judgement(
        student=student, question=question, marks_awarded=awarded,
        marks_available=available, confidence=0.95, status=status,
        option_chosen=option,
    )


@pytest.fixture
def reported(tmp_path, request):
    draft = (request.config.rootpath / "fixtures" / "drafts" / "y9-chem-test.md").read_text()
    assessment = ingest_markdown(draft, assume_yes=True)
    pkg = tmp_path / "pkg"
    build_package(assessment, pkg, compile_pdf=False)
    manifest = json.loads((pkg / "manifest.json").read_text())

    judgements = [
        # Q1 (mcq, 1): S1 correct, S2 & S3 wrong via distractor A
        _j("S1", "Q1", 1, 1, option="C"), _j("S2", "Q1", 0, 1, option="A"), _j("S3", "Q1", 0, 1, option="A"),
        # Q2 (short, 2): everyone full marks — easy
        _j("S1", "Q2", 2, 2), _j("S2", "Q2", 2, 2), _j("S3", "Q2", 2, 2),
        # Q4 (extended, 6): spread + one still in review
        _j("S1", "Q4", 6, 6), _j("S2", "Q4", 2, 6), _j("S3", "Q4", 1, 6, status=JudgementStatus.review),
    ]
    run = MarkRun(test_id=assessment.test_id, version_hash=manifest["version_hash"],
                  marker="fake", judgements=judgements)
    (pkg / "marks.json").write_text(json.dumps(run.model_dump(mode="json")))
    return pkg


def _rows(path):
    with path.open() as f:
        return list(csv.DictReader(f))


def test_outputs_exist(reported):
    result = run_report(reported)
    for name in ("results.csv", "totals.csv", "item_analysis.csv", "summary.md"):
        assert (reported / name).exists(), name
    for name in ("fact_response.csv", "dim_assessment.csv", "dim_question.csv", "dim_student.csv"):
        assert (reported / "export" / name).exists(), name
    assert result["students"] == 3
    assert result["still_in_review"] == 1


def test_item_analysis_math(reported):
    run_report(reported)
    stats = {r["question_id"]: r for r in _rows(reported / "item_analysis.csv")}
    assert float(stats["Q2"]["facility"]) == 1.0
    assert stats["Q2"]["difficulty"] == "easy"
    # Q1 facility = 1/3; distractor A chosen twice
    assert abs(float(stats["Q1"]["facility"]) - 1 / 3) < 0.01
    assert json.loads(stats["Q1"]["option_counts"]) == {"C": 1, "A": 2}
    # Q4 discriminates: top scorer 6/6 vs bottom 1/6
    assert float(stats["Q4"]["discrimination"]) > 0.5


def test_star_schema_has_no_names(reported):
    run_report(reported)
    with (reported / "export" / "dim_student.csv").open() as f:
        header = f.readline().strip().split(",")
    assert "name" not in header
    facts = _rows(reported / "export" / "fact_response.csv")
    assert len(facts) == 9
    q1 = next(r for r in facts if r["student_id"] == "S2" and r["question_id"] == "Q1")
    assert q1["correct"] == "False" and q1["option_chosen"] == "A"


def test_review_overrides_merge(reported):
    (reported / "review_overrides.yaml").write_text(yaml.safe_dump({"S3": {"Q4": 3}}))
    result = run_report(reported)
    assert result["overrides_applied"] == 1
    assert result["still_in_review"] == 0
    rows = _rows(reported / "results.csv")
    s3q4 = next(r for r in rows if r["student_id"] == "S3" and r["question_id"] == "Q4")
    assert float(s3q4["marks_awarded"]) == 3.0
    assert s3q4["status"] == "marked"
