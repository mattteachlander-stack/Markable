"""`analyse` + dashboard tests — offline, driven by fixtures."""

import csv
import json
from pathlib import Path

import pytest

from markable.analysis import analyse_assessment, cognitive_level, run_analyse
from markable.curriculum import load_pack
from markable.ingest import ingest_markdown
from markable.models import Question, QuestionType

VC2_PACK = Path(__file__).resolve().parents[1] / "fixtures" / "curricula" / "vc2-science" / "pack.yaml"


@pytest.fixture
def pack():
    return load_pack(str(VC2_PACK))


@pytest.fixture
def assessment(request):
    draft = (request.config.rootpath / "fixtures" / "drafts" / "y9-chem-test.md").read_text()
    return ingest_markdown(draft, assume_yes=True)


def _q(stem, qtype=QuestionType.short_answer):
    opts = {"A": "x", "B": "y"} if qtype is QuestionType.mcq else None
    return Question(id="Qx", type=qtype, marks=2, stem=stem, options=opts)


def test_blooms_verb_classification():
    assert cognitive_level(_q("State the formula for average velocity.")) == "Remember"
    assert cognitive_level(_q("Explain how temperature affects reaction rate.")) == "Understand"
    assert cognitive_level(_q("Calculate the number of moles in 36 g of water.")) == "Apply"
    assert cognitive_level(_q("Compare the two experimental designs.")) == "Analyse"
    assert cognitive_level(_q("Justify which method gives more reliable results.")) == "Evaluate"
    assert cognitive_level(_q("Design an investigation to test the claim.")) == "Create"
    # No verb match → question-type fallback.
    assert cognitive_level(_q("The total resistance of the circuit?", QuestionType.numerical)) == "Apply"


def test_analysis_rows_map_to_vc2_codes(assessment, pack):
    rows = {r.question_id: r for r in analyse_assessment(assessment, pack)}
    # Q4 (temperature/rate/collision theory) must map to the reaction-rates code.
    assert rows["Q4"].code == "VC2S9U07"
    assert "Chemical sciences" in rows["Q4"].concept_area
    assert rows["Q4"].concept_area.startswith("Science Understanding")
    # Q3 is numerical mole calculation → Apply.
    assert rows["Q3"].cognitive_level == "Apply"
    # Every row carries a skill statement and marks.
    assert all(r.skill and r.marks > 0 for r in rows.values())


def test_confirmed_tags_beat_proposals(assessment, pack):
    q1 = next(q for q in assessment.questions if q.id == "Q1")
    q1.outcome_codes = ["VC2S10U09"]  # teacher says: this is actually Motion
    rows = {r.question_id: r for r in analyse_assessment(assessment, pack)}
    assert rows["Q1"].code == "VC2S10U09" and rows["Q1"].confidence == 1.0
    assert "Motion" in rows["Q1"].concept_area


def test_run_analyse_writes_html_and_csv(tmp_path, request, pack):
    draft = request.config.rootpath / "fixtures" / "drafts" / "y9-chem-test.md"
    result = run_analyse(draft, pack, out_dir=tmp_path)
    html = (tmp_path / "test_analysis.html").read_text()
    assert "VCAA / ACARA code" in html and "Cognitive level" in html
    assert "Proof of concept" in html  # the verify-before-official-use caveat
    assert "<script src" not in html  # self-contained
    with (tmp_path / "test_analysis.csv").open() as f:
        rows = list(csv.DictReader(f))
    assert len(rows) == 7
    assert result["mapped"] >= 5  # most fixture items find a code offline


def test_dashboard_html(tmp_path, request):
    from markable.build import build_package
    from markable.dashboard_html import run_dashboard
    from markable.models import Judgement, MarkRun

    draft = (request.config.rootpath / "fixtures" / "drafts" / "y9-chem-test.md").read_text()
    assessment = ingest_markdown(draft, assume_yes=True)
    pkg = tmp_path / "pkg"
    build_package(assessment, pkg, compile_pdf=False)
    manifest = json.loads((pkg / "manifest.json").read_text())
    marks = {q.id: q.marks for q in assessment.questions}
    judgements = [
        Judgement(student=f"S{i}", question=qid, marks_awarded=float(min(av, i % (av + 1))),
                  marks_available=float(av), confidence=0.95, status="marked")
        for i in range(1, 9) for qid, av in marks.items()
    ]
    run = MarkRun(test_id=assessment.test_id, version_hash=manifest["version_hash"],
                  marker="fake", judgements=judgements)
    (pkg / "marks.json").write_text(json.dumps(run.model_dump(mode="json")))

    out = run_dashboard(pkg)
    html = out.read_text()
    for needle in ("Score distribution", "Question performance by cohort segment",
                   "Student snapshot", "Top 25%", "Bottom 25%", "difficult"):
        assert needle in html, needle
    assert "<script src" not in html and "https://" not in html.split("</title>")[1]
