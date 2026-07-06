"""`report` — scores, item analysis, and the star-schema export.

Inputs: `marks.json` (from `mark`) merged with `review_overrides.yaml` (the
teacher's final word on review-queue items — human-in-the-loop by design).

Outputs, all in the package folder:

- `results.csv`      one row per student × question
- `totals.csv`       per-student raw score + percentage
- `item_analysis.csv` facility + discrimination per question, distractor counts
- `summary.md`       offline-computed teacher summary (hardest questions,
                     misconception signals from distractor_notes)
- `export/`          the star schema (brief 10.1) — fact_response + dims as CSV.
                     A Part 1 commitment so Parts 2-3 are purely additive.
                     Contains NO student names (privacy, brief 7/10.4); the name
                     join happens locally from class_list.csv if present.
"""

from __future__ import annotations

import csv
import json
from collections import defaultdict
from pathlib import Path
from typing import Optional

import yaml

from .ingest import load_assessment
from .models import (
    DimAssessment,
    DimQuestion,
    DimStudent,
    FactResponse,
    Judgement,
    JudgementStatus,
    MarkRun,
    QuestionType,
)


def _load_run(package_dir: Path) -> MarkRun:
    marks_path = package_dir / "marks.json"
    if not marks_path.exists():
        raise FileNotFoundError(
            f"{marks_path} not found — run `markable mark` first."
        )
    return MarkRun.model_validate(json.loads(marks_path.read_text(encoding="utf-8")))


def _apply_overrides(run: MarkRun, package_dir: Path) -> tuple[MarkRun, int]:
    """Merge teacher review decisions over the AI judgements."""
    path = package_dir / "review_overrides.yaml"
    if not path.exists():
        return run, 0
    overrides = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    applied = 0
    for j in run.judgements:
        value = (overrides.get(j.student) or {}).get(j.question)
        if value is None:
            continue
        j.marks_awarded = float(value)
        j.status = JudgementStatus.marked
        j.review_reason = "finalised by teacher review"
        applied += 1
    return run, applied


def _write_csv(path: Path, header: list[str], rows: list[list]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(header)
        writer.writerows(rows)


def _quartiles(totals: dict[str, float]) -> dict[str, int]:
    """1 = top quartile … 4 = bottom (for fact_response.quartile_at_assessment)."""
    ranked = sorted(totals, key=lambda s: -totals[s])
    n = len(ranked)
    out = {}
    for idx, sid in enumerate(ranked):
        out[sid] = min(4, 1 + (idx * 4) // n) if n else 1
    return out


def _item_stats(judgements: list[Judgement], totals: dict[str, float]) -> dict[str, dict]:
    """Facility + discrimination (top-third vs bottom-third facility)."""
    by_q: dict[str, list[Judgement]] = defaultdict(list)
    for j in judgements:
        by_q[j.question].append(j)

    ranked = sorted(totals, key=lambda s: -totals[s])
    third = max(1, len(ranked) // 3)
    top, bottom = set(ranked[:third]), set(ranked[-third:])

    stats = {}
    for qid, js in by_q.items():
        avail = max((j.marks_available for j in js), default=0.0)

        def facility(subset: list[Judgement]) -> Optional[float]:
            if not subset or not avail:
                return None
            return sum(j.marks_awarded for j in subset) / (avail * len(subset))

        fac = facility(js)
        disc = None
        top_js = [j for j in js if j.student in top]
        bot_js = [j for j in js if j.student in bottom]
        f_top, f_bot = facility(top_js), facility(bot_js)
        if f_top is not None and f_bot is not None:
            disc = f_top - f_bot

        options = defaultdict(int)
        for j in js:
            if j.option_chosen:
                options[j.option_chosen] += 1

        stats[qid] = {
            "facility": fac,
            "discrimination": disc,
            "options": dict(options),
            "reviewed": sum(1 for j in js if j.status is JudgementStatus.review),
        }
    return stats


def _difficulty(facility: Optional[float]) -> Optional[str]:
    """easy ≥80% / moderate 50-79% / difficult <50% (brief section 10)."""
    if facility is None:
        return None
    return "easy" if facility >= 0.8 else "moderate" if facility >= 0.5 else "difficult"


def run_report(package_dir: Path) -> dict:
    assessment = load_assessment(package_dir / "assessment.yaml")
    run = _load_run(package_dir)
    run, overrides_applied = _apply_overrides(run, package_dir)
    manifest = json.loads((package_dir / "manifest.json").read_text(encoding="utf-8"))
    questions = {q.id: q for q in assessment.questions}

    # --- per-student totals -------------------------------------------------
    totals: dict[str, float] = defaultdict(float)
    avail: dict[str, float] = defaultdict(float)
    for j in run.judgements:
        totals[j.student] += j.marks_awarded
        avail[j.student] += j.marks_available
    quartiles = _quartiles(dict(totals))

    # --- results.csv ----------------------------------------------------------
    _write_csv(
        package_dir / "results.csv",
        ["student_id", "question_id", "marks_awarded", "marks_available",
         "criteria_met", "option_chosen", "confidence", "status", "feedback"],
        [[j.student, j.question, j.marks_awarded, j.marks_available,
          "; ".join(j.criteria_met), j.option_chosen or "", j.confidence,
          j.status.value, j.feedback]
         for j in sorted(run.judgements, key=lambda j: (j.student, j.question))],
    )

    _write_csv(
        package_dir / "totals.csv",
        ["student_id", "raw_score", "max_score", "percentage", "quartile"],
        [[sid, totals[sid], avail[sid],
          round(100 * totals[sid] / avail[sid], 1) if avail[sid] else "",
          quartiles.get(sid, "")]
         for sid in sorted(totals)],
    )

    # --- item analysis --------------------------------------------------------
    stats = _item_stats(run.judgements, dict(totals))
    _write_csv(
        package_dir / "item_analysis.csv",
        ["question_id", "type", "marks", "facility", "discrimination",
         "difficulty", "in_review", "option_counts"],
        [[qid,
          questions[qid].type.value if qid in questions else "",
          questions[qid].marks if qid in questions else "",
          round(s["facility"], 3) if s["facility"] is not None else "",
          round(s["discrimination"], 3) if s["discrimination"] is not None else "",
          _difficulty(s["facility"]) or "",
          s["reviewed"],
          json.dumps(s["options"]) if s["options"] else ""]
         for qid, s in sorted(stats.items())],
    )

    # --- star schema (brief 10.1) ----------------------------------------------
    export = package_dir / "export"
    _write_csv(
        export / "fact_response.csv",
        list(FactResponse.model_fields),
        [[assessment.test_id, j.student, j.question, j.marks_awarded, j.marks_available,
          (j.option_chosen == _correct(questions, j.question)) if j.option_chosen else "",
          j.option_chosen or "",
          len(j.criteria_met),
          j.confidence,
          j.status is not JudgementStatus.marked or j.review_reason == "finalised by teacher review",
          quartiles.get(j.student, "")]
         for j in run.judgements],
    )
    _write_csv(
        export / "dim_assessment.csv",
        list(DimAssessment.model_fields),
        [[assessment.test_id, assessment.title, assessment.subject,
          assessment.year_level, "", "", "", assessment.total_marks,
          manifest["version_hash"]]],
    )
    _write_csv(
        export / "dim_question.csv",
        list(DimQuestion.model_fields),
        [[q.id, q.type.value, "", q.marks,
          _difficulty(stats.get(q.id, {}).get("facility")) or "",
          ";".join(q.outcome_codes), ""]
         for q in assessment.questions],
    )
    # dim_student: IDs only — names never enter the export folder (brief 10.4).
    _write_csv(
        export / "dim_student.csv",
        [f for f in DimStudent.model_fields if f != "name"],
        [[sid, ""] for sid in sorted(totals)],
    )

    # --- teacher summary ---------------------------------------------------------
    _write_summary(package_dir, assessment, run, stats, totals, avail)

    return {
        "students": len(totals),
        "judgements": len(run.judgements),
        "overrides_applied": overrides_applied,
        "still_in_review": sum(1 for j in run.judgements if j.status is JudgementStatus.review),
    }


def _correct(questions: dict, qid: str) -> Optional[str]:
    q = questions.get(qid)
    return q.expected_answer if q and q.type is QuestionType.mcq else None


def _write_summary(package_dir, assessment, run, stats, totals, avail) -> None:
    hardest = sorted(
        ((qid, s) for qid, s in stats.items() if s["facility"] is not None),
        key=lambda kv: kv[1]["facility"],
    )[:3]
    pct = [100 * totals[s] / avail[s] for s in totals if avail[s]]
    lines = [
        f"# Teacher summary — {assessment.test_id}",
        "",
        f"- Students marked: {len(totals)}",
        f"- Cohort average: {sum(pct) / len(pct):.1f}%" if pct else "- Cohort average: n/a",
        f"- Below 50%: {sum(1 for p in pct if p < 50)} student(s)",
        "",
        "## Hardest questions",
        "",
    ]
    for qid, s in hardest:
        lines.append(f"- **{qid}** — facility {s['facility']:.0%}"
                     + (f", {s['reviewed']} in review" if s["reviewed"] else ""))
    review_count = sum(1 for j in run.judgements if j.status is JudgementStatus.review)
    if review_count:
        lines += ["", f"⚠ {review_count} judgement(s) still in the review queue — see review.html."]
    (package_dir / "summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
