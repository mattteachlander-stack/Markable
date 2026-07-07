"""`report --dashboard` — the Tier 1 instant dashboard (Part 3, Phase 8).

One self-contained HTML file per assessment (no libraries, no network): cohort
KPIs, score-distribution histogram, a question-performance matrix segmented by
cohort quartile, per-question difficulty classification, and a student
snapshot. Ranks are off by default (brief 10.4 — a school-culture decision).

Theme: electric green. The sequential ramp and accent steps were run through
the dataviz palette validator (monotone lightness, adjacent ΔL ≥ 0.06, single
hue) for both surfaces; the matrix is continuous magnitude, so the lightest
step is allowed to recede toward the surface, and every cell shows its value —
colour never carries the number alone. Dark mode is its own selected steps.
"""

from __future__ import annotations

import html as html_mod
import json
from collections import defaultdict
from pathlib import Path
from statistics import median

from .ingest import load_assessment
from .models import JudgementStatus, QuestionType
from .report import _apply_overrides, _load_run, _quartiles

# Validated electric-green sequential ramp, low→high.
# Light: light→dark on the light surface; dark mode is its own selection
# (low recedes toward the dark surface, high pops bright).
_GREEN_LIGHT = ["#c9f7d8", "#8beeae", "#45de81", "#00c853", "#00a344", "#007d34", "#005224"]
_GREEN_DARK = ["#00461f", "#006c2e", "#00913d", "#00b64c", "#12d95f", "#5ceb8f", "#a5f7c3"]
# In-cell ink per bin (by fill luminance).
_INK_LIGHT = ["#0b0b0b", "#0b0b0b", "#0b0b0b", "#0b0b0b", "#ffffff", "#ffffff", "#ffffff"]
_INK_DARK = ["#ffffff", "#ffffff", "#ffffff", "#0b0b0b", "#0b0b0b", "#0b0b0b", "#0b0b0b"]

_ACCENT_LIGHT, _ACCENT_DARK = "#00a344", "#12d95f"


def _bin(pct: float) -> int:
    return min(6, int(pct / 100 * 7))


_CSS = f"""
:root{{
  --surface:#fcfcfb; --page:#f9f9f7; --ink:#0b0b0b; --ink-2:#52514e;
  --muted:#898781; --grid:#e1e0d9; --baseline:#c3c2b7;
  --border:rgba(11,11,11,.10); --accent:{_ACCENT_LIGHT};
  --accent-wash:rgba(0,163,68,.09); --empty:#f0efec;
  --tip-bg:#0b0b0b; --tip-ink:#fff;
}}
@media (prefers-color-scheme: dark){{
  :root{{
    --surface:#1a1a19; --page:#0d0d0d; --ink:#fff; --ink-2:#c3c2b7;
    --muted:#898781; --grid:#2c2c2a; --baseline:#383835;
    --border:rgba(255,255,255,.10); --accent:{_ACCENT_DARK};
    --accent-wash:rgba(18,217,95,.10); --empty:#383835;
    --tip-bg:#f4f4f2; --tip-ink:#0b0b0b;
  }}
}}
*{{box-sizing:border-box}}
body{{margin:0;background:var(--page);color:var(--ink);
  font-family:system-ui,-apple-system,"Segoe UI",sans-serif;font-size:14px;line-height:1.45}}
.wrap{{max-width:1100px;margin:0 auto;padding:28px 20px 64px}}
h1{{font-size:21px;margin:0 0 2px}}
h2{{font-size:15px;margin:0 0 12px}}
.sub{{color:var(--ink-2);margin:0 0 18px}}
.rule{{height:3px;width:64px;background:var(--accent);border-radius:2px;margin:0 0 22px}}
.card{{background:var(--surface);border:1px solid var(--border);border-radius:10px;
  padding:18px 20px;margin-bottom:18px}}
.kpis{{display:grid;grid-template-columns:repeat(auto-fit,minmax(140px,1fr));gap:12px;margin-bottom:18px}}
.tile{{background:var(--surface);border:1px solid var(--border);border-radius:10px;padding:14px 16px}}
.tile .label{{color:var(--ink-2);font-size:12.5px;margin-bottom:4px}}
.tile .value{{font-weight:600;font-size:27px}}
.tile .value.hero{{font-size:48px;line-height:1.05}}
.tile .note{{color:var(--muted);font-size:12px;margin-top:2px}}
/* histogram */
.hist{{display:grid;grid-template-columns:repeat(10,1fr);gap:8px;align-items:end;
  height:150px;border-bottom:1px solid var(--baseline);padding:0 4px}}
.hist .col{{position:relative;background:var(--accent);border-radius:4px 4px 0 0;min-height:2px}}
.hist .col .n{{position:absolute;top:-19px;width:100%;text-align:center;font-size:11.5px;
  color:var(--ink-2);font-variant-numeric:tabular-nums}}
.hist-x{{display:grid;grid-template-columns:repeat(10,1fr);gap:8px;padding:4px 4px 0;
  color:var(--muted);font-size:11px;text-align:center}}
/* matrix */
.mx{{overflow-x:auto}}
.mx table{{border-collapse:separate;border-spacing:2px}}
.mx th{{font-weight:500;color:var(--ink-2);font-size:12px;padding:2px 8px;text-align:center;white-space:nowrap}}
.mx th.rowh{{text-align:left}}
.mx td{{min-width:72px;height:30px;text-align:center;border-radius:4px;font-size:12px;
  font-variant-numeric:tabular-nums}}
.mx td:hover{{outline:2px solid var(--ink);outline-offset:-2px}}
.mx td.na{{background:var(--empty);color:var(--muted)}}
.chip{{display:inline-block;border-radius:99px;padding:1px 10px;font-size:12px;
  border:1px solid var(--border);color:var(--ink-2)}}
.chip.easy{{border-color:var(--accent)}}
.chip.difficult{{border-color:#d03b3b;color:#d03b3b}}
.legend{{display:flex;align-items:center;gap:6px;margin-top:10px;color:var(--ink-2);font-size:12px}}
.legend .sw{{width:26px;height:12px;border-radius:3px;display:inline-block}}
/* tables */
table.plain{{border-collapse:collapse;width:100%}}
table.plain th{{color:var(--ink-2);font-weight:500;font-size:12.5px;text-align:left;
  border-bottom:1px solid var(--baseline);padding:6px 10px 6px 0}}
table.plain td{{border-bottom:1px solid var(--grid);padding:6px 10px 6px 0}}
table.plain td.num{{font-variant-numeric:tabular-nums;text-align:right}}
table.plain tr:hover td{{background:var(--accent-wash)}}
details{{margin-top:12px}}
summary{{cursor:pointer;color:var(--ink-2);font-size:13px}}
#tip{{position:fixed;display:none;max-width:320px;background:var(--tip-bg);color:var(--tip-ink);
  padding:9px 12px;border-radius:8px;font-size:13.5px;line-height:1.4;z-index:10;
  pointer-events:none;box-shadow:0 4px 14px rgba(0,0,0,.25)}}
#tip b{{display:block;margin-bottom:2px}}
.foot{{color:var(--muted);font-size:12px;margin-top:26px}}
"""

_TIP_JS = """
const tip=document.getElementById('tip');
document.addEventListener('mousemove',e=>{const el=e.target.closest('[data-tip]');
if(!el){tip.style.display='none';return}
const t=el.getAttribute('data-tip-title');tip.innerHTML=t?'<b></b>':'';
if(t)tip.querySelector('b').textContent=t;
tip.appendChild(document.createTextNode(el.getAttribute('data-tip')));
tip.style.display='block';const p=14,w=tip.offsetWidth,h=tip.offsetHeight;
let x=e.clientX+p,y=e.clientY+p;
if(x+w>innerWidth-8)x=e.clientX-w-p;if(y+h>innerHeight-8)y=e.clientY-h-p;
tip.style.left=Math.max(8,x)+'px';tip.style.top=Math.max(8,y)+'px';});
"""


def _bin_css() -> str:
    light = "".join(
        f".mx td.g{i}{{background:{bg};color:{ink}}}"
        for i, (bg, ink) in enumerate(zip(_GREEN_LIGHT, _INK_LIGHT))
    )
    dark = "".join(
        f".mx td.g{i}{{background:{bg};color:{ink}}}"
        for i, (bg, ink) in enumerate(zip(_GREEN_DARK, _INK_DARK))
    )
    return f"{light}@media (prefers-color-scheme: dark){{{dark}}}"


def _difficulty(facility: float) -> str:
    return "easy" if facility >= 0.8 else "moderate" if facility >= 0.5 else "difficult"


def run_dashboard(package_dir: Path, show_ranks: bool = False) -> Path:
    esc = html_mod.escape
    assessment = load_assessment(package_dir / "assessment.yaml")
    run = _load_run(package_dir)
    run, _ = _apply_overrides(run, package_dir)
    questions = {q.id: q for q in assessment.questions}

    totals: dict[str, float] = defaultdict(float)
    avail: dict[str, float] = defaultdict(float)
    for j in run.judgements:
        totals[j.student] += j.marks_awarded
        avail[j.student] += j.marks_available
    pct = {s: 100 * totals[s] / avail[s] for s in totals if avail[s]}
    quartiles = _quartiles(dict(totals))
    seg_of = {s: (1 if quartiles[s] == 1 else 3 if quartiles[s] == 4 else 2) for s in pct}
    segments = {0: "All", 1: "Top 25%", 2: "Middle 50%", 3: "Bottom 25%"}

    values = sorted(pct.values())
    kpis = [
        ("Class average", f"{sum(values)/len(values):.0f}%", "", True),
        ("Median", f"{median(values):.0f}%", "", False),
        ("Highest", f"{max(values):.0f}%", "", False),
        ("Lowest", f"{min(values):.0f}%", "", False),
        ("At or above 70%", f"{sum(1 for v in values if v >= 70)}", f"of {len(values)} students", False),
        ("Below 50%", f"{sum(1 for v in values if v < 50)}", "intervention flag", False),
    ]
    kpi_html = "".join(
        f'<div class="tile"><div class="label">{esc(l)}</div>'
        f'<div class="value{" hero" if hero else ""}">{esc(v)}</div>'
        + (f'<div class="note">{esc(n)}</div>' if n else "") + "</div>"
        for l, v, n, hero in kpis
    )

    # Histogram: 10-point score bins.
    bins = [0] * 10
    for v in values:
        bins[min(9, int(v // 10))] += 1
    peak = max(bins) or 1
    hist = "".join(
        f'<div class="col" style="height:{max(2, b / peak * 100):.0f}%" '
        f'data-tip-title="{i*10}–{i*10+9}%" data-tip="{b} student(s)">'
        + (f'<span class="n">{b}</span>' if b else "") + "</div>"
        for i, b in enumerate(bins)
    )
    hist_x = "".join(f"<span>{i*10}s</span>" for i in range(10))

    # Question × quartile-segment facility matrix.
    per_q: dict[str, dict[int, list[float]]] = defaultdict(lambda: defaultdict(lambda: [0.0, 0.0]))
    review_q: dict[str, int] = defaultdict(int)
    for j in run.judgements:
        seg = seg_of.get(j.student)
        if seg is None:
            continue
        for s in (0, seg):
            per_q[j.question][s][0] += j.marks_awarded
            per_q[j.question][s][1] += j.marks_available
        if j.status is JudgementStatus.review:
            review_q[j.question] += 1

    def cell(qid: str, seg: int) -> str:
        aw, av = per_q[qid].get(seg, [0.0, 0.0])
        if not av:
            return '<td class="na">—</td>'
        p = 100 * aw / av
        return (
            f'<td class="g{_bin(p)}" data-tip-title="{esc(qid)} · {segments[seg]}" '
            f'data-tip="{p:.0f}% of marks earned ({aw:g} of {av:g})">{p:.0f}</td>'
        )

    mx_rows = []
    for q in assessment.questions:
        if q.id not in per_q:
            continue
        aw, av = per_q[q.id][0]
        fac = aw / av if av else 0
        diff = _difficulty(fac)
        stem_tip = q.stem[:220] + ("…" if len(q.stem) > 220 else "")
        review_note = f" · {review_q[q.id]} in review" if review_q[q.id] else ""
        mx_rows.append(
            f'<tr><th class="rowh" data-tip-title="{esc(q.id)} ({q.type.value}, {q.marks} marks)" '
            f'data-tip="{esc(stem_tip)}{esc(review_note)}">{esc(q.id)}</th>'
            + "".join(cell(q.id, s) for s in (0, 1, 2, 3))
            + f'<td style="background:none"><span class="chip {diff}">{diff}</span></td></tr>'
        )
    mx_head = (
        '<tr><th class="rowh">Question</th>'
        + "".join(f"<th>{segments[s]}</th>" for s in (0, 1, 2, 3))
        + "<th>Difficulty</th></tr>"
    )
    legend = '<div class="legend"><span>0%</span>' + "".join(
        f'<span class="sw gsw{i}"></span>' for i in range(7)
    ) + "<span>100%</span></div>"
    legend_css = "".join(f".gsw{i}{{background:{c}}}" for i, c in enumerate(_GREEN_LIGHT)) + \
        "@media (prefers-color-scheme: dark){" + \
        "".join(f".gsw{i}{{background:{c}}}" for i, c in enumerate(_GREEN_DARK)) + "}"

    # Student snapshot — ranks off by default (brief 10.4).
    snapshot_rows = "".join(
        f"<tr><td>{esc(s)}</td><td class='num'>{totals[s]:g} / {avail[s]:g}</td>"
        f"<td class='num'>{pct[s]:.0f}%</td>"
        f"<td>{segments[seg_of[s]] if seg_of[s] != 2 else 'Middle 50%'}</td></tr>"
        for s in sorted(pct, key=lambda s: -pct[s] if show_ranks else 0) or sorted(pct)
    )

    total_marks = assessment.total_marks
    page = f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Dashboard — {esc(assessment.test_id)}</title>
<style>{_CSS}{_bin_css()}{legend_css}</style></head>
<body><div class="wrap">
<h1>{esc(assessment.title or assessment.test_id)}</h1>
<p class="sub">{esc(assessment.test_id)} · {len(assessment.questions)} questions ·
{total_marks} marks · {len(pct)} students marked</p>
<div class="rule"></div>
<div class="kpis">{kpi_html}</div>

<div class="card"><h2>Score distribution</h2>
<div class="hist">{hist}</div><div class="hist-x">{hist_x}</div></div>

<div class="card"><h2>Question performance by cohort segment</h2>
<div class="mx"><table>{mx_head}{''.join(mx_rows)}</table></div>
{legend}
<p class="note" style="color:var(--muted);font-size:12.5px">Hover a question id for its stem;
hover a cell for exact marks. Difficulty: easy ≥80% · moderate 50–79% · difficult &lt;50%.</p></div>

<div class="card"><h2>Student snapshot</h2>
<table class="plain"><tr><th>Student</th><th>Raw score</th><th>%</th><th>Cohort segment</th></tr>
{snapshot_rows}</table>
<p class="note" style="color:var(--muted);font-size:12.5px">Ranks are hidden by default
(school-culture setting). Names never appear — join locally from class_list.csv.</p></div>

<p class="foot">Generated by Markable · single-file dashboard — safe to email or archive</p>
</div>
<div id="tip"></div>
<script>{_TIP_JS}</script>
</body></html>"""

    out = package_dir / "dashboard.html"
    out.write_text(page, encoding="utf-8")
    return out
