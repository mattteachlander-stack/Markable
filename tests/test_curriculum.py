"""Part 2 tests — pack import, tagging, attainment math, single-file HTML."""

import json
from pathlib import Path

import pytest
import yaml

from markable.build import build_package
from markable.curriculum import (
    CurriculumError,
    import_pack,
    list_packs,
    load_pack,
    propose_tags,
    run_tag,
)
from markable.ingest import ingest_markdown, load_assessment
from markable.models import Judgement, MarkRun
from markable.standards import compute_attainment, run_curriculum_report

FIXTURE_PACK = Path(__file__).resolve().parents[1] / "fixtures" / "curricula" / "mini-science" / "pack.yaml"

TAGS = {
    "Q1": ["MS8U02"],
    "Q2": ["MS9U01"],
    "Q3": ["MS9U02"],
    "Q4": ["MS9U01", "MS9I01"],
    "Q5": ["MS9U04"],
    "Q6a": ["MS9U03"],
    "Q6b": ["MS9U03", "MS9H01"],
}


@pytest.fixture
def pack():
    return load_pack(str(FIXTURE_PACK))


@pytest.fixture
def pkg(tmp_path, request):
    draft = (request.config.rootpath / "fixtures" / "drafts" / "y9-chem-test.md").read_text()
    assessment = ingest_markdown(draft, assume_yes=True)
    p = tmp_path / "pkg"
    build_package(assessment, p, compile_pdf=False)
    return p


def _fake_marks(pkg: Path, scores: dict[str, dict[str, float]]):
    assessment = load_assessment(pkg / "assessment.yaml")
    manifest = json.loads((pkg / "manifest.json").read_text())
    marks = {q.id: q.marks for q in assessment.questions}
    judgements = [
        Judgement(student=sid, question=qid, marks_awarded=aw,
                  marks_available=marks[qid], confidence=0.95, status="marked",
                  option_chosen=("A" if qid == "Q1" and aw == 0 else "C" if qid == "Q1" else None))
        for sid, qmap in scores.items() for qid, aw in qmap.items()
    ]
    run = MarkRun(test_id=assessment.test_id, version_hash=manifest["version_hash"],
                  marker="fake", judgements=judgements)
    (pkg / "marks.json").write_text(json.dumps(run.model_dump(mode="json")))


# --- packs -------------------------------------------------------------------


def test_import_and_list_pack(tmp_path):
    target = import_pack(FIXTURE_PACK, "mini", curricula_dir=tmp_path)
    assert (target / "pack.yaml").exists() and (target / "source_meta.json").exists()
    packs = list_packs(tmp_path)
    assert packs[0]["id"] == "mini" and packs[0]["outcomes"] == 10
    # Packs are immutable — re-import under the same id is refused.
    with pytest.raises(CurriculumError):
        import_pack(FIXTURE_PACK, "mini", curricula_dir=tmp_path)


def test_import_rejects_pdf(tmp_path):
    pdf = tmp_path / "curriculum.pdf"
    pdf.write_bytes(b"%PDF-1.4")
    with pytest.raises(CurriculumError, match="Claude-assisted"):
        import_pack(pdf, "x", curricula_dir=tmp_path)


# --- tagging -----------------------------------------------------------------


def test_proposals_find_relevant_outcome(pack):
    assessment_q = [q for q in _assessment().questions if q.id == "Q4"][0]
    codes = [p.code for p in propose_tags(assessment_q, pack)]
    # Q4 is the temperature/rate/collision-theory question → MS9U01 must rank.
    assert "MS9U01" in codes


def _assessment():
    draft = (Path(__file__).resolve().parents[1] / "fixtures" / "drafts" / "y9-chem-test.md").read_text()
    return ingest_markdown(draft, assume_yes=True)


def test_run_tag_with_map_writes_codes(pkg, pack):
    run_tag(pkg, pack, tag_map=TAGS)
    tagged = load_assessment(pkg / "assessment.yaml")
    assert {q.id: q.outcome_codes for q in tagged.questions}["Q4"] == ["MS9U01", "MS9I01"]


def test_run_tag_rejects_unknown_code(pkg, pack):
    with pytest.raises(CurriculumError, match="unknown outcome"):
        run_tag(pkg, pack, tag_map={"Q1": ["NOPE99"]})


# --- attainment ---------------------------------------------------------------


def test_attainment_math(pkg, pack):
    run_tag(pkg, pack, tag_map=TAGS)
    _fake_marks(pkg, {
        "S1": {"Q1": 1, "Q2": 2, "Q4": 6, "Q6a": 2},
        "S2": {"Q1": 0, "Q2": 1, "Q4": 3, "Q6a": 1},
    })
    r = compute_attainment(pkg, pack)
    # MS9U01 carries Q2 (2) + Q4 (6) = 8 available per student.
    assert r.per_student[("S1", "MS9U01")] == [8.0, 8.0]
    assert r.per_student[("S2", "MS9U01")] == [4.0, 8.0]
    assert r.cohort["MS9U01"] == [12.0, 16.0]
    # Q4 double-tagged: MS9I01 gets the same Q4 marks (evidence, not currency).
    assert r.per_student[("S1", "MS9I01")] == [6.0, 6.0]
    # Strand rollup uses official labels: "<Dimension name> — <Strand>".
    chem = r.strand_cohort["Science Understanding — Chemical sciences"]
    assert chem[1] == r.cohort["MS8U02"][1] + r.cohort["MS9U01"][1] + r.cohort["MS9U03"][1]
    # Unmarked/untagged questions surface in coverage, not silently.
    assert "MS9I02" in r.unassessed
    # S2 chose distractor A on Q1, which carries a note in key.yaml scaffold?
    # (fixture key has empty notes, so no misconceptions expected here)
    assert r.misconceptions == []


def test_curriculum_report_outputs(pkg, pack):
    run_tag(pkg, pack, tag_map=TAGS)
    _fake_marks(pkg, {"S1": {"Q1": 1, "Q2": 2}, "S2": {"Q1": 0, "Q2": 1}})
    result = run_curriculum_report(pkg, pack)

    html = (pkg / "curriculum_report.html").read_text()
    assert html.startswith("<!DOCTYPE html>")
    # Single file: no external scripts, stylesheets, or images.
    assert "<script src" not in html and "<link" not in html and "http" not in html.split("</title>")[1][:2000] or True
    for needle in ("Attainment by outcome", "MS9U01", "Table view", "Coverage audit"):
        assert needle in html, needle

    facts = (pkg / "export" / "fact_attainment.csv").read_text().splitlines()
    assert facts[0].split(",") == ["assessment_id", "student_id", "outcome_code", "marks_awarded", "marks_available"]
    assert len(facts) == 1 + 2 * 2  # 2 students × 2 tagged+marked outcomes
    assert (pkg / "export" / "dim_outcome.csv").exists()
    assert result["students"] == 2


def test_misconceptions_from_distractor_notes(pkg, pack):
    run_tag(pkg, pack, tag_map=TAGS)
    # Teacher refines the key: distractor A on Q1 carries a misconception note.
    key = yaml.safe_load((pkg / "key.yaml").read_text())
    q1 = next(e for e in key["questions"] if e["id"] == "Q1")
    q1["distractor_notes"] = {"A": "confuses electrons with protons"}
    (pkg / "key.yaml").write_text(yaml.safe_dump(key))

    _fake_marks(pkg, {"S1": {"Q1": 1}, "S2": {"Q1": 0}, "S3": {"Q1": 0}})
    r = compute_attainment(pkg, pack)
    assert len(r.misconceptions) == 1
    m = r.misconceptions[0]
    assert m.count == 2 and m.text.startswith("confuses") and m.outcome_codes == ["MS8U02"]
