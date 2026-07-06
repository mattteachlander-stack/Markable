import importlib.util
import json

import pytest

from markable.build import build_package
from markable.build import layout
from markable.ids import version_hash
from markable.ingest import ingest_markdown
from markable.models import Manifest, QuestionType

TYPST_AVAILABLE = importlib.util.find_spec("typst") is not None


@pytest.fixture
def assessment(draft_text):
    return ingest_markdown(draft_text, assume_yes=True)


def test_layout_is_deterministic(assessment):
    vh = version_hash(assessment)
    a = layout.lay_out(assessment, vh)
    b = layout.lay_out(assessment, vh)
    za = [(p.number, z.question.id, z.zone.bbox.x, z.zone.bbox.y) for p in a.pages for z in p.questions]
    zb = [(p.number, z.question.id, z.zone.bbox.x, z.zone.bbox.y) for p in b.pages for z in p.questions]
    assert za == zb


def test_zones_stay_within_page(assessment):
    paper = layout.lay_out(assessment, version_hash(assessment))
    for page in paper.pages:
        for pq in page.questions:
            b = pq.zone.bbox
            assert b.x >= 0 and b.y >= 0
            assert b.x + b.w <= paper.page_w + 0.01
            assert b.y + b.h <= paper.page_h + 0.01


def test_numerical_has_final_answer_cell(assessment):
    paper = layout.lay_out(assessment, version_hash(assessment))
    zones = {pq.question.id: pq for page in paper.pages for pq in page.questions}
    q3 = zones["Q3"]
    assert q3.question.type is QuestionType.numerical
    fa = q3.zone.final_answer_bbox
    assert fa is not None
    # Final-answer cell sits at the bottom of the working box.
    assert fa.y + fa.h == pytest.approx(q3.zone.bbox.y + q3.zone.bbox.h)


def test_build_writes_all_artifacts(assessment, tmp_path):
    pkg = tmp_path / "pkg"
    result = build_package(assessment, pkg, compile_pdf=TYPST_AVAILABLE)

    assert (pkg / "assessment.yaml").exists()
    assert (pkg / "key.yaml").exists()
    assert (pkg / "manifest.json").exists()
    assert (pkg / "paper.typ").exists()
    assert (pkg / "scripts").is_dir()

    if TYPST_AVAILABLE:
        assert result.pdf_path is not None and result.pdf_path.exists()
        assert result.pdf_path.stat().st_size > 0


def test_manifest_has_a_zone_for_every_question(assessment, tmp_path):
    pkg = tmp_path / "pkg"
    build_package(assessment, pkg, compile_pdf=False)
    man = Manifest.model_validate(json.loads((pkg / "manifest.json").read_text()))

    all_zone_ids = {z.question_id for page in man.pages for z in page.zones}
    assert all_zone_ids == {q.id for q in assessment.questions}
    assert man.version_hash == version_hash(assessment)
    # Every page carries a parseable QR payload tied to this version.
    for page in man.pages:
        assert man.version_hash in page.qr_payload


def test_key_scaffold_shape(assessment, tmp_path):
    import yaml

    from markable.models import Key

    pkg = tmp_path / "pkg"
    build_package(assessment, pkg, compile_pdf=False)
    key = Key.model_validate(yaml.safe_load((pkg / "key.yaml").read_text()))

    assert key.total_marks == assessment.total_marks
    by_id = {e.id: e for e in key.questions}
    # MCQ correct answer carried through from the embedded draft answer.
    assert by_id["Q1"].correct == "C"
    # Short-answer criteria scaffolded one-per-mark.
    assert len(by_id["Q2"].criteria) == 2
    # Extended gets a rubric scaffold; diagram gets the higher review threshold.
    assert by_id["Q4"].rubric
    assert by_id["Q5"].review_threshold == 0.9
