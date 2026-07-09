"""Student feedback slips — one printable page per student (market gap #4).

`markable report <pkg> --feedback` (or `run_feedback`) turns marking output the
package already holds into something that goes *back to students*: a single
self-contained `feedback_slips.html` with one slip per student — total and
percentage, a per-question table (marks, how the cohort went, the marker's
feedback line), strengths, and a "focus next on" section built from the
student's weakest questions (with curriculum codes when questions are tagged).

Names: the slip shows the student's name only if a local `class_list.csv`
(`student_id,name`) sits in the package folder — the same local-only name join
the brief prescribes (§7). Without it, slips carry IDs only.

Print: each slip is an A4 page (`page-break-after`), so the teacher opens the
file, hits Print, and hands them out — or prints to PDF for distribution.
"""

from __future__ import annotations

import csv
import html
import json
from collections import defaultdict
from pathlib import Path

from .ingest import load_assessment
from .models import JudgementStatus
from .report import _apply_overrides, _item_stats, _load_run

_CSS = """
:root{--surface:#fff;--page:#f4f6fb;--ink:#0f1729;--ink2:#48566f;--muted:#8a95a8;
  --border:rgba(15,23,41,.14);--accent:#1e63d0;--wash:rgba(30,99,208,.07);
  --good:#1f7a44;--warn:#a15c00}
*{box-sizing:border-box}
body{font-family:system-ui,sans-serif;margin:0;background:var(--page);color:var(--ink);
  font-size:13.5px;line-height:1.45}
.toolbar{position:sticky;top:0;background:var(--page);border-bottom:1px solid var(--border);
  padding:12px 26px;display:flex;gap:12px;align-items:center;z-index:5}
.btn{appearance:none;border:0;border-radius:8px;padding:9px 16px;font:inherit;font-weight:600;
  cursor:pointer;background:var(--accent);color:#fff}
.hint{color:var(--muted);font-size:12px}
.slip{background:var(--surface);max-width:52rem;margin:22px auto;padding:28px 34px;
  border:1px solid var(--border);border-radius:12px}
.slip-head{display:flex;justify-content:space-between;gap:16px;align-items:flex-start;
  border-bottom:2px solid var(--accent);padding-bottom:12px;margin-bottom:14px}
.slip-head h2{margin:0;font-size:19px}
.slip-head .meta{color:var(--ink2);font-size:12.5px;margin-top:3px}
.total{text-align:right}
.total .big{font-size:30px;font-weight:700;line-height:1}
.total .pct{color:var(--ink2)}
table{border-collapse:collapse;width:100%;margin:6px 0 14px}
th{text-align:left;color:var(--ink2);font-weight:600;font-size:12px;border-bottom:1px solid var(--border);padding:5px 8px 5px 0}
td{border-bottom:1px solid rgba(15,23,41,.07);padding:6px 8px 6px 0;vertical-align:top}
td.num{white-space:nowrap;font-variant-numeric:tabular-nums}
.pending{color:var(--warn);font-style:italic}
.cols{display:grid;grid-template-columns:1fr 1fr;gap:18px}
.cols h3{margin:0 0 6px;font-size:13px;text-transform:uppercase;letter-spacing:.05em}
.cols .s h3{color:var(--good)} .cols .f h3{color:var(--warn)}
.cols ul{margin:0;padding-left:18px}
.cols li{margin-bottom:5px}
.code{display:inline-block;background:var(--wash);border-radius:4px;padding:0 6px;
  font-size:11.5px;color:var(--accent);font-weight:600}
.slip-foot{margin-top:14px;color:var(--muted);font-size:11px;border-top:1px solid var(--border);padding-top:8px}
@media print{
  body{background:#fff}
  .toolbar{display:none}
  .slip{border:0;border-radius:0;max-width:none;margin:0;padding:10mm 6mm;page-break-after:always}
}
"""


def _load_names(package_dir: Path) -> dict[str, str]:
    """Local-only name join from class_list.csv (student_id,name) — brief §7."""
    path = package_dir / "class_list.csv"
    if not path.exists():
        return {}
    names = {}
    with path.open(encoding="utf-8") as f:
        for row in csv.DictReader(f):
            sid = (row.get("student_id") or "").strip()
            name = (row.get("name") or "").strip()
            if sid and name:
                names[sid] = name
    return names


def _stem_excerpt(stem: str, limit: int = 70) -> str:
    stem = " ".join(stem.split())
    return stem if len(stem) <= limit else stem[: limit - 1].rsplit(" ", 1)[0] + "…"


def run_feedback(package_dir: Path) -> dict:
    assessment = load_assessment(package_dir / "assessment.yaml")
    run = _load_run(package_dir)
    run, _ = _apply_overrides(run, package_dir)
    questions = {q.id: q for q in assessment.questions}
    names = _load_names(package_dir)

    # Totals shown to students count FINALISED marks only — a pending item's
    # AI-proposed mark never appears on a slip, so "may increase" stays true.
    totals: dict[str, float] = defaultdict(float)
    avail: dict[str, float] = defaultdict(float)
    all_totals: dict[str, float] = defaultdict(float)
    by_student: dict[str, list] = defaultdict(list)
    for j in run.judgements:
        all_totals[j.student] += j.marks_awarded
        if j.status is not JudgementStatus.review:
            totals[j.student] += j.marks_awarded
            avail[j.student] += j.marks_available
        by_student[j.student].append(j)
    stats = _item_stats(run.judgements, dict(all_totals))

    q_order = [q.id for q in assessment.questions]

    slips = []
    for sid in sorted(by_student):
        js = sorted(by_student[sid], key=lambda j: q_order.index(j.question) if j.question in q_order else 99)
        total, out_of = totals.get(sid, 0.0), avail.get(sid, 0.0)
        pct = 100 * total / out_of if out_of else 0.0

        rows = ""
        scored = []  # (pct-of-marks, judgement) for strengths/focus
        pending = 0
        for j in js:
            q = questions.get(j.question)
            cohort = stats.get(j.question, {}).get("facility")
            cohort_txt = f"{cohort*100:.0f}%" if cohort is not None else "—"
            if j.status is JudgementStatus.review:
                pending += 1
                fb = '<span class="pending">mark pending teacher review</span>'
                mark_txt = "—"
            else:
                fb = html.escape(j.feedback) if j.feedback else "—"
                mark_txt = f"{j.marks_awarded:g} / {j.marks_available:g}"
                if j.marks_available:
                    scored.append((j.marks_awarded / j.marks_available, j))
            rows += (f'<tr><td><b>{html.escape(j.question)}</b></td>'
                     f'<td class="num">{mark_txt}</td>'
                     f'<td class="num">{cohort_txt}</td><td>{fb}</td></tr>')

        def _li(j) -> str:
            q = questions.get(j.question)
            codes = "".join(f' <span class="code">{html.escape(c)}</span>'
                            for c in (q.outcome_codes if q else []))
            stem = _stem_excerpt(q.stem) if q else ""
            return f"<li><b>{html.escape(j.question)}</b> — {html.escape(stem)}{codes}</li>"

        scored.sort(key=lambda t: t[0])
        focus = [j for f, j in scored if f < 1.0][:2] or [j for _f, j in scored[:1]]
        strengths = [j for f, j in reversed(scored) if f >= 0.999][:2] or [j for _f, j in list(reversed(scored))[:1]]
        focus_html = "".join(_li(j) for j in focus) or "<li>—</li>"
        strong_html = "".join(_li(j) for j in strengths) or "<li>—</li>"

        display = names.get(sid)
        who = f"{html.escape(display)} <span class='meta'>({html.escape(sid)})</span>" if display else html.escape(sid)
        pending_note = (f'<p class="pending">⚠ {pending} question(s) awaiting teacher review — '
                        "your total may increase.</p>" if pending else "")

        slips.append(f"""<div class="slip">
  <div class="slip-head">
    <div><h2>{who}</h2>
      <div class="meta">{html.escape(assessment.title)} · {html.escape(assessment.subject)}
      · Year {assessment.year_level}</div></div>
    <div class="total"><div class="big">{total:g} / {out_of:g}</div>
      <div class="pct">{pct:.0f}%</div></div>
  </div>
  {pending_note}
  <table>
    <tr><th>Question</th><th>Your marks</th><th>Class average</th><th>Feedback</th></tr>
    {rows}
  </table>
  <div class="cols">
    <div class="s"><h3>💪 Strengths</h3><ul>{strong_html}</ul></div>
    <div class="f"><h3>🎯 Focus next on</h3><ul>{focus_html}</ul></div>
  </div>
  <div class="slip-foot">Marked with teacher review · {html.escape(assessment.test_id)} ·
  Generated by Markable</div>
</div>""")

    page = f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Feedback slips — {html.escape(assessment.test_id)}</title>
<style>{_CSS}</style></head><body>
<div class="toolbar">
  <button class="btn" onclick="window.print()">🖨 Print all slips</button>
  <span class="hint">{len(slips)} slip(s), one page per student — print, or save as PDF to
  distribute.{" Names joined locally from class_list.csv." if names else
  " Add a class_list.csv (student_id,name) beside this file and re-run for named slips."}</span>
</div>
{''.join(slips)}
</body></html>"""

    out = package_dir / "feedback_slips.html"
    out.write_text(page, encoding="utf-8")
    return {"path": out, "slips": len(slips), "named": bool(names)}
