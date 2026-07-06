"""`mark` — AI marking engine.

Marks **per question, not per script** (brief 4.4): for each question, all
students' cropped responses are gathered and judged against that question's
key entry, keeping the marking context tight and consistent across the cohort.

The engine is marker-agnostic: anything implementing the `Marker` protocol can
judge a batch. `AnthropicMarker` (anthropic_marker.py, `ai` extra) is the real
one; tests inject a deterministic fake. Review rules are applied *here*, not in
the marker, so they hold no matter what marks:

- confidence below the question's `review_threshold` → review queue
- blank responses (flagged by `scan`) → review queue, never judged
- marker-flagged ambiguity (double bubble, illegible) → review queue
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Protocol

import yaml

from ..models import (
    Judgement,
    JudgementStatus,
    Key,
    KeyEntry,
    MarkRun,
    Question,
    ScanReport,
)
from ..ingest import load_assessment
from .review import write_review_html


@dataclass
class MarkItem:
    """One student's response to one question, ready to judge."""

    student_id: str
    crop_path: Path
    final_crop_path: Optional[Path] = None  # numerical final-answer cell
    blank: bool = False


class Marker(Protocol):
    """Judges one question's cohort batch. Implementations must return one
    Judgement per non-blank item (blank items never reach the marker)."""

    name: str

    def mark_question(
        self, question: Question, key_entry: KeyEntry, items: list[MarkItem]
    ) -> list[Judgement]: ...


def _collect_items(package_dir: Path, question_id: str, blanks: dict[str, set[str]]) -> list[MarkItem]:
    scripts = package_dir / "scripts"
    items = []
    for student_dir in sorted(p for p in scripts.iterdir() if p.is_dir() and not p.name.startswith("_")):
        crop = student_dir / f"{question_id}.png"
        if not crop.exists():
            continue  # missing page — surfaced by scan_report, not judged
        final = student_dir / f"{question_id}_final.png"
        items.append(
            MarkItem(
                student_id=student_dir.name,
                crop_path=crop,
                final_crop_path=final if final.exists() else None,
                blank=question_id in blanks.get(student_dir.name, set()),
            )
        )
    return items


def _blank_judgement(item: MarkItem, question_id: str, marks_available: float) -> Judgement:
    return Judgement(
        student=item.student_id,
        question=question_id,
        marks_awarded=0.0,
        marks_available=marks_available,
        evidence="scan flagged this response as blank",
        status=JudgementStatus.review,
        review_reason="blank response — never auto-marked (brief 4.4)",
    )


def _apply_review_rules(j: Judgement, entry: KeyEntry) -> Judgement:
    if j.status is JudgementStatus.error:
        return j
    if j.review_reason:
        j.status = JudgementStatus.review
    elif j.confidence < entry.review_threshold:
        j.status = JudgementStatus.review
        j.review_reason = (
            f"confidence {j.confidence:.2f} below threshold {entry.review_threshold:.2f}"
        )
    else:
        j.status = JudgementStatus.marked
    return j


def run_mark(package_dir: Path, marker: Marker) -> MarkRun:
    """Mark every scanned script in the package, question by question."""
    assessment = load_assessment(package_dir / "assessment.yaml")
    key = Key.model_validate(yaml.safe_load((package_dir / "key.yaml").read_text(encoding="utf-8")))
    entries = {e.id: e for e in key.questions}
    questions = {q.id: q for q in assessment.questions}

    manifest = json.loads((package_dir / "manifest.json").read_text(encoding="utf-8"))

    blanks: dict[str, set[str]] = {}
    report_path = package_dir / "scan_report.json"
    if report_path.exists():
        report = ScanReport.model_validate(json.loads(report_path.read_text(encoding="utf-8")))
        for s in report.students:
            blanks[s.student_id] = set(s.blank_questions)

    judgements: list[Judgement] = []
    for qid, question in questions.items():
        entry = entries.get(qid)
        if entry is None:
            continue
        items = _collect_items(package_dir, qid, blanks)
        to_mark = [i for i in items if not i.blank]

        judgements.extend(_blank_judgement(i, qid, entry.marks) for i in items if i.blank)

        if to_mark:
            for j in marker.mark_question(question, entry, to_mark):
                j.marks_available = float(entry.marks)
                judgements.append(_apply_review_rules(j, entry))

    run = MarkRun(
        test_id=assessment.test_id,
        version_hash=manifest["version_hash"],
        marker=marker.name,
        judgements=judgements,
    )
    (package_dir / "marks.json").write_text(
        json.dumps(run.model_dump(mode="json"), indent=2), encoding="utf-8"
    )

    review_items = [j for j in judgements if j.status is JudgementStatus.review]
    if review_items:
        write_review_html(package_dir, review_items)
    return run
