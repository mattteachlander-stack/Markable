"""Standards-referenced reporting (Part 2, Phase 6) — `markable report --curriculum`.

Turns question-level marks into curriculum attainment: marks earned vs available
per outcome code (a question tagged with several codes contributes its marks to
each — evidence, not currency), rolled up by strand and dimension, plus the
cohort heatmap, coverage audit, and misconception signals from MCQ distractors.

Outputs:
- `export/fact_attainment.csv` + `export/dim_outcome.csv` (star schema, 10.1)
- `curriculum_report.html` — a single self-contained file (no JS libraries, no
  network) so it opens on any machine with just a browser.
"""

from __future__ import annotations

import json
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path

import yaml

from .ingest import load_assessment
from .models import CurriculumPack, DimOutcome, FactAttainment, Key, QuestionType
from .report import _apply_overrides, _load_run, _write_csv


@dataclass
class Misconception:
    text: str
    count: int
    question_id: str
    option: str
    outcome_codes: list[str] = field(default_factory=list)


@dataclass
class AttainmentResult:
    test_id: str
    curriculum: str
    # (student, code) -> [awarded, available]
    per_student: dict[tuple[str, str], list[float]]
    cohort: dict[str, list[float]]  # code -> [awarded, available]
    strand_cohort: dict[str, list[float]]  # strand -> [awarded, available]
    dimension_cohort: dict[str, list[float]]
    students: list[str]
    assessed_codes: list[str]
    unassessed: list[str]  # pack outcomes at this level never assessed
    untagged_questions: list[str]
    misconceptions: list[Misconception]


def compute_attainment(package_dir: Path, pack: CurriculumPack) -> AttainmentResult:
    assessment = load_assessment(package_dir / "assessment.yaml")
    run = _load_run(package_dir)
    run, _ = _apply_overrides(run, package_dir)
    key = Key.model_validate(yaml.safe_load((package_dir / "key.yaml").read_text(encoding="utf-8")))

    outcomes = {o.code: o for o in pack.outcomes}
    q_codes = {q.id: [c for c in q.outcome_codes if c in outcomes] for q in assessment.questions}
    untagged = [q.id for q in assessment.questions if not q_codes[q.id]]

    per_student: dict[tuple[str, str], list[float]] = defaultdict(lambda: [0.0, 0.0])
    cohort: dict[str, list[float]] = defaultdict(lambda: [0.0, 0.0])
    students: set[str] = set()

    for j in run.judgements:
        students.add(j.student)
        for code in q_codes.get(j.question, []):
            per_student[(j.student, code)][0] += j.marks_awarded
            per_student[(j.student, code)][1] += j.marks_available
            cohort[code][0] += j.marks_awarded
            cohort[code][1] += j.marks_available

    # Labels follow the official curriculum naming: full dimension names
    # ("Science Understanding", not "SU") and strands qualified by dimension.
    dim_names = {d.id: (d.name or d.id) for d in pack.dimensions}
    strand_cohort: dict[str, list[float]] = defaultdict(lambda: [0.0, 0.0])
    dimension_cohort: dict[str, list[float]] = defaultdict(lambda: [0.0, 0.0])
    for code, (aw, av) in cohort.items():
        o = outcomes[code]
        dim = dim_names.get(o.dimension, o.dimension)
        strand_cohort[f"{dim} — {o.strand}"][0] += aw
        strand_cohort[f"{dim} — {o.strand}"][1] += av
        dimension_cohort[dim][0] += aw
        dimension_cohort[dim][1] += av

    levels = {str(assessment.year_level)} if assessment.year_level else set(pack.levels)
    unassessed = [
        o.code for o in pack.outcomes if o.level in levels and o.code not in cohort
    ]

    # Misconceptions: wrong-option choices whose distractor carries a note.
    entries = {e.id: e for e in key.questions}
    questions = {q.id: q for q in assessment.questions}
    counts: dict[tuple[str, str], int] = defaultdict(int)
    for j in run.judgements:
        q = questions.get(j.question)
        e = entries.get(j.question)
        if not q or not e or q.type is not QuestionType.mcq or not j.option_chosen:
            continue
        if j.option_chosen != e.correct and (e.distractor_notes or {}).get(j.option_chosen):
            counts[(j.question, j.option_chosen)] += 1
    misconceptions = sorted(
        (
            Misconception(
                text=entries[qid].distractor_notes[opt],
                count=n,
                question_id=qid,
                option=opt,
                outcome_codes=q_codes.get(qid, []),
            )
            for (qid, opt), n in counts.items()
        ),
        key=lambda m: -m.count,
    )

    return AttainmentResult(
        test_id=assessment.test_id,
        curriculum=f"{pack.curriculum} v{pack.version}",
        per_student={k: v for k, v in per_student.items()},
        cohort=dict(cohort),
        strand_cohort=dict(strand_cohort),
        dimension_cohort=dict(dimension_cohort),
        students=sorted(students),
        assessed_codes=sorted(cohort, key=lambda c: list(outcomes).index(c) if c in outcomes else 999),
        unassessed=unassessed,
        untagged_questions=untagged,
        misconceptions=misconceptions,
    )


def export_attainment(package_dir: Path, result: AttainmentResult, pack: CurriculumPack) -> None:
    """Star-schema additions: fact_attainment + dim_outcome (brief 10.1)."""
    export = package_dir / "export"
    _write_csv(
        export / "fact_attainment.csv",
        list(FactAttainment.model_fields),
        [[result.test_id, sid, code, aw, av]
         for (sid, code), (aw, av) in sorted(result.per_student.items())],
    )
    _write_csv(
        export / "dim_outcome.csv",
        list(DimOutcome.model_fields),
        [[o.code, o.strand, o.dimension, o.level, pack.version] for o in pack.outcomes],
    )


def run_curriculum_report(package_dir: Path, pack: CurriculumPack) -> dict:
    from .standards_html import render_report

    result = compute_attainment(package_dir, pack)
    if not result.cohort:
        raise ValueError(
            "no tagged questions with marks found — run `markable tag` (and `mark`) first"
        )
    export_attainment(package_dir, result, pack)
    html_path = package_dir / "curriculum_report.html"
    html_path.write_text(render_report(result, pack), encoding="utf-8")
    return {
        "students": len(result.students),
        "outcomes_assessed": len(result.assessed_codes),
        "outcomes_unassessed": len(result.unassessed),
        "untagged_questions": result.untagged_questions,
        "misconceptions": len(result.misconceptions),
        "html": html_path,
    }
