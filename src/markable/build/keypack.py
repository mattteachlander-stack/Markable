"""Scaffold `key.yaml` — the marking pack — from an assessment.

`build` produces a *scaffold* the teacher then refines (brief section 4.2 / 8):
criteria placeholders, accept/reject lists, MCQ correct answer + distractor
notes, rubric bands. Marking (Phase 2+) reads the refined `key.yaml`; no marking
logic lives here.
"""

from __future__ import annotations

from ..models import (
    Assessment,
    Criterion,
    Key,
    KeyEntry,
    Question,
    QuestionType,
    RubricBand,
)

# Diagrams and extended responses default to a higher review threshold — they
# are always spot-checkable in v1 (brief section 4.4).
_HIGH_REVIEW = {QuestionType.diagram, QuestionType.extended}


def _criteria_scaffold(marks: int) -> list[Criterion]:
    """One 1-mark placeholder criterion per mark, for the teacher to edit."""
    return [Criterion(point=f"TODO: criterion {i + 1}", marks=1) for i in range(marks)]


def _rubric_scaffold(marks: int) -> list[RubricBand]:
    """Rough banded rubric scaffold for extended responses."""
    if marks <= 0:
        return []
    hi = marks
    mid_hi = max(1, round(marks * 2 / 3))
    lo_hi = max(1, round(marks / 3))
    return [
        RubricBand(band=f"{mid_hi + 1}-{hi}", descriptor="TODO: top-band descriptor"),
        RubricBand(band=f"{lo_hi + 1}-{mid_hi}", descriptor="TODO: mid-band descriptor"),
        RubricBand(band=f"1-{lo_hi}", descriptor="TODO: low-band descriptor"),
    ]


def _entry(q: Question) -> KeyEntry:
    review_threshold = 0.9 if q.type in _HIGH_REVIEW else 0.85
    entry = KeyEntry(id=q.id, type=q.type, marks=q.marks, review_threshold=review_threshold)

    if q.type is QuestionType.mcq:
        entry.correct = q.expected_answer  # may be None if not embedded in the draft
        if q.options:
            entry.distractor_notes = {
                label: "" for label in q.options if label != q.expected_answer
            }
    elif q.type is QuestionType.extended:
        entry.rubric = _rubric_scaffold(q.marks)
    else:  # short_answer, numerical, diagram
        entry.criteria = _criteria_scaffold(q.marks)
        if q.type is QuestionType.numerical:
            entry.final_answer = None
            entry.tolerance = None

    return entry


def scaffold(assessment: Assessment) -> Key:
    return Key(
        test_id=assessment.test_id,
        total_marks=assessment.total_marks,
        questions=[_entry(q) for q in assessment.questions],
    )
