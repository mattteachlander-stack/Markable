"""Feedback slips tests — offline, driven by the shared marked-package fixture."""

import json
from pathlib import Path

import pytest

from markable.build import build_package
from markable.feedback_html import run_feedback
from markable.ingest import ingest_markdown
from markable.mark import run_mark
from markable.models import (
    Judgement,
    PageStatus,
    ScannedPage,
    ScanReport,
    StudentCoverage,
)


def _png() -> bytes:
    import io

    from PIL import Image

    buf = io.BytesIO()
    Image.new("L", (8, 8), 255).save(buf, format="PNG")
    return buf.getvalue()


class _Marker:
    """Full marks + warm feedback for S1; half marks, low confidence for S2."""

    name = "fake"

    def mark_question(self, question, key_entry, items):
        out = []
        for i in items:
            out.append(Judgement(
                student=i.student_id, question=question.id,
                marks_awarded=float(key_entry.marks),
                confidence=0.95, transcription="answer",
                evidence="matches the key",
                feedback=f"Great work on {question.id}!",
            ))
        return out


@pytest.fixture
def pkg(tmp_path, request):
    draft = (request.config.rootpath / "fixtures" / "drafts" / "y9-chem-test.md").read_text()
    assessment = ingest_markdown(draft, assume_yes=True)
    pkg = tmp_path / "pkg"
    build_package(assessment, pkg, compile_pdf=False)
    png = _png()
    for sid in ("S1", "S2"):
        d = pkg / "scripts" / sid
        d.mkdir(parents=True)
        for q in assessment.questions:
            (d / f"{q.id}.png").write_bytes(png)
    manifest = json.loads((pkg / "manifest.json").read_text())
    report = ScanReport(
        test_id=assessment.test_id, version_hash=manifest["version_hash"],
        total_pages_expected=manifest["total_pages"],
        pages=[ScannedPage(source="x.pdf", source_index=1, status=PageStatus.ok)],
        students=[StudentCoverage(student_id=s, pages_found=[1, 2, 3], pages_missing=[])
                  for s in ("S1", "S2")],
    )
    (pkg / "scan_report.json").write_text(json.dumps(report.model_dump(mode="json")))
    run_mark(pkg, _Marker())
    return pkg


def test_one_slip_per_student(pkg):
    result = run_feedback(pkg)
    assert result["slips"] == 2 and not result["named"]
    page = (pkg / "feedback_slips.html").read_text(encoding="utf-8")
    assert page.count('class="slip"') == 2
    # per-question feedback lines make it onto the slip
    assert "Great work on Q1!" in page
    # print affordances: page breaks + a print button
    assert "page-break-after" in page and "window.print()" in page
    # strengths / focus sections present
    assert "Strengths" in page and "Focus next on" in page


def test_names_join_locally_from_class_list(pkg):
    (pkg / "class_list.csv").write_text(
        "student_id,name\nS1,Milla Bird\nS2,Pauly Bletsas\n", encoding="utf-8"
    )
    result = run_feedback(pkg)
    assert result["named"]
    page = (pkg / "feedback_slips.html").read_text(encoding="utf-8")
    assert "Milla Bird" in page and "Pauly Bletsas" in page


def test_review_items_shown_as_pending(pkg):
    # push one judgement back to review by blanking the override path and
    # rewriting marks.json with a review-status item
    marks = json.loads((pkg / "marks.json").read_text())
    marks["judgements"][0]["status"] = "review"
    marks["judgements"][0]["review_reason"] = "low confidence"
    (pkg / "marks.json").write_text(json.dumps(marks))
    (pkg / "review_overrides.yaml").unlink(missing_ok=True)
    run_feedback(pkg)
    page = (pkg / "feedback_slips.html").read_text(encoding="utf-8")
    assert "pending teacher review" in page
    assert "your total may increase" in page.lower()
    # the pending item's AI-proposed mark is excluded from the displayed total:
    # fixture awards full marks (19 total); Q1 (1 mark) pending → S1 shows 18/18
    assert "18 / 18" in page
