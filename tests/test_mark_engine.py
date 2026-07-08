"""Mark engine tests — offline, driven by a deterministic fake marker."""

import json
from pathlib import Path

import pytest
import yaml

from markable.build import build_package
from markable.ingest import ingest_markdown
from markable.mark import MarkItem, run_mark
from markable.models import (
    Judgement,
    JudgementStatus,
    ScannedPage,
    PageStatus,
    ScanReport,
    StudentCoverage,
)

def _png_bytes() -> bytes:
    import io

    from PIL import Image

    buf = io.BytesIO()
    Image.new("L", (8, 8), 255).save(buf, format="PNG")
    return buf.getvalue()


_PNG = _png_bytes()


class FakeMarker:
    """Awards full marks with per-student canned confidence."""

    name = "fake"

    def __init__(self, confidences: dict[str, float]):
        self.confidences = confidences
        self.calls: list[tuple[str, list[str]]] = []

    def mark_question(self, question, key_entry, items):
        self.calls.append((question.id, [i.student_id for i in items]))
        return [
            Judgement(
                student=i.student_id,
                question=question.id,
                marks_awarded=float(key_entry.marks),
                confidence=self.confidences.get(i.student_id, 0.95),
                transcription="something",
                evidence="looks right",
            )
            for i in items
        ]


@pytest.fixture
def marked_package(tmp_path, request):
    """Package with fabricated crops for two students + a scan report where
    S2's Q2 is blank."""
    draft = (request.config.rootpath / "fixtures" / "drafts" / "y9-chem-test.md").read_text()
    assessment = ingest_markdown(draft, assume_yes=True)
    pkg = tmp_path / "pkg"
    build_package(assessment, pkg, compile_pdf=False)

    qids = [q.id for q in assessment.questions]
    for sid in ("S1", "S2"):
        d = pkg / "scripts" / sid
        d.mkdir(parents=True)
        for qid in qids:
            (d / f"{qid}.png").write_bytes(_PNG)

    manifest = json.loads((pkg / "manifest.json").read_text())
    report = ScanReport(
        test_id=assessment.test_id,
        version_hash=manifest["version_hash"],
        total_pages_expected=manifest["total_pages"],
        pages=[ScannedPage(source="x.pdf", source_index=1, status=PageStatus.ok)],
        students=[
            StudentCoverage(student_id="S1", pages_found=[1, 2, 3], pages_missing=[]),
            StudentCoverage(student_id="S2", pages_found=[1, 2, 3], pages_missing=[], blank_questions=["Q2"]),
        ],
    )
    (pkg / "scan_report.json").write_text(json.dumps(report.model_dump(mode="json")))
    return pkg, assessment


def test_marks_per_question_cohort_batches(marked_package):
    pkg, assessment = marked_package
    marker = FakeMarker({"S1": 0.95, "S2": 0.95})
    run = run_mark(pkg, marker)
    # One call per question; both students batched together (except blanks).
    by_q = dict(marker.calls)
    assert set(by_q) == {q.id for q in assessment.questions}
    assert len(by_q["Q1"]) == 2
    assert len(by_q["Q2"]) == 1  # S2's Q2 was blank — never sent to the marker
    # The marker never sees real student IDs — only local random aliases…
    seen = {sid for sids in by_q.values() for sid in sids}
    assert not seen & {"S1", "S2"}
    assert all(sid.startswith("anon-") for sid in seen)
    # …but the results are re-identified locally before anything is written.
    assert {j.student for j in run.judgements} == {"S1", "S2"}


def test_blank_goes_to_review_not_marker(marked_package):
    pkg, _ = marked_package
    run = run_mark(pkg, FakeMarker({}))
    blank = next(j for j in run.judgements if j.student == "S2" and j.question == "Q2")
    assert blank.status is JudgementStatus.review
    assert blank.marks_awarded == 0
    assert "blank" in (blank.review_reason or "")


def test_confidence_threshold_routes_to_review(marked_package):
    pkg, _ = marked_package
    # The marker only ever sees aliases, so canned confidences must be keyed
    # by alias too — pre-minting here reuses the same package key file that
    # run_mark's Pseudonymiser loads.
    from markable.anon import Pseudonymiser

    anon = Pseudonymiser(pkg)
    # S2 low confidence everywhere; diagram/extended threshold is 0.9 so S1's
    # 0.88 passes short_answer (0.85) but fails extended Q4 and diagram Q5.
    run = run_mark(pkg, FakeMarker({anon.alias("S1"): 0.88, anon.alias("S2"): 0.5}))
    j = {(x.student, x.question): x for x in run.judgements}
    assert j[("S1", "Q2")].status is JudgementStatus.marked
    assert j[("S1", "Q4")].status is JudgementStatus.review
    assert j[("S1", "Q5")].status is JudgementStatus.review
    assert j[("S2", "Q1")].status is JudgementStatus.review


def test_outputs_written(marked_package):
    pkg, _ = marked_package
    run_mark(pkg, FakeMarker({"S1": 0.95, "S2": 0.2}))
    assert (pkg / "marks.json").exists()
    assert (pkg / "review.html").exists()
    overrides = yaml.safe_load((pkg / "review_overrides.yaml").read_text())
    assert "S2" in overrides  # scaffolded slots for the review queue


def test_review_html_is_interactive(marked_package):
    """The review queue is a working UI: accept/set-mark controls per item,
    progress tracking, and a client-side review_overrides.yaml download in the
    exact {student: {question: marks}} shape `markable report` merges."""
    pkg, assessment = marked_package
    run_mark(pkg, FakeMarker({"S1": 0.95, "S2": 0.2}))
    page = (pkg / "review.html").read_text(encoding="utf-8")
    for el in ("const ITEMS=", "decide(", "downloadOverrides", "review_overrides.yaml",
               "Accept", "Set mark", "localStorage", "pbar"):
        assert el in page, el
    # decisions persist per test — the storage key carries the test id
    assert f"const TEST_ID={assessment.test_id!r}".replace("'", '"') in page
    # the embedded items carry what the emitter needs
    import json as _json
    items = _json.loads(page.split("const ITEMS=", 1)[1].split(";\n", 1)[0])
    assert all({"student", "question", "proposed", "available"} <= set(i) for i in items)
    assert any(i["student"] == "S2" for i in items)


def test_anthropic_marker_request_shape(tmp_path):
    """Offline: the request the Anthropic marker builds must match the current
    API surface (cached system, structured output, adaptive thinking)."""
    from markable.mark.anthropic_marker import AnthropicMarker
    from markable.models import KeyEntry, Question, QuestionType

    crop = tmp_path / "Q1.png"
    crop.write_bytes(_PNG)
    marker = AnthropicMarker(client=object())  # never called
    q = Question(id="Q1", type=QuestionType.mcq, marks=1, stem="Pick one",
                 options={"A": "x", "B": "y"})
    entry = KeyEntry(id="Q1", type=QuestionType.mcq, marks=1, correct="A")
    req = marker.build_request(q, entry, MarkItem(student_id="S1", crop_path=crop))

    assert req["model"] == "claude-opus-4-8"
    assert req["thinking"] == {"type": "adaptive"}
    assert req["system"][0]["cache_control"] == {"type": "ephemeral"}
    assert "Correct answer: A" in req["system"][0]["text"]
    assert req["output_config"]["format"]["type"] == "json_schema"
    assert req["messages"][0]["content"][0]["type"] == "image"
