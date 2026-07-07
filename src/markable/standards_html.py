"""Render `curriculum_report.html` — a single self-contained standards report.

Zero-infrastructure philosophy (same as review.html): one file, inline CSS and
~15 lines of inline JS for the hover tooltip, no libraries, no network. Opens
in any browser.

Visual system (dataviz skill):
- The attainment heatmap uses a **semantic-heat** scale (red → amber → green),
  the teacher-requested traffic-light reading. Semantic heat is the documented
  multi-hue sequential exception; its mitigations all ship: a scale legend, the
  value visible in every cell (never colour-alone), and a table-view twin.
- Strand labels follow the official curriculum naming ("Science Understanding —
  Physical sciences"), and every strand/outcome/cell has a large readable
  tooltip (a single fixed-position element, so it never clips or truncates).
- Text wears text tokens, never data colour. Hairline rules. Dark mode is its
  own selected steps, not an automatic flip.
"""

from __future__ import annotations

import html as html_mod

from .models import CurriculumPack
from .standards import AttainmentResult

# Semantic-heat bins, low→high attainment: red → amber → green.
# (bg-light, ink-light, bg-dark, ink-dark) — ink picked per fill luminance.
_BINS = [
    ("#c23b3b", "#ffffff", "#c94747", "#ffffff"),  # 0-14%
    ("#d96a3a", "#ffffff", "#d97740", "#0b0b0b"),  # 14-28
    ("#e79a41", "#0b0b0b", "#e2a24d", "#0b0b0b"),  # 28-43
    ("#dcb844", "#0b0b0b", "#d3b957", "#0b0b0b"),  # 43-57 (amber pivot)
    ("#9ebe4b", "#0b0b0b", "#8fc058", "#0b0b0b"),  # 57-71
    ("#55a344", "#ffffff", "#4fae4d", "#0b0b0b"),  # 71-86
    ("#1e7a34", "#ffffff", "#2e9647", "#ffffff"),  # 86-100
]


def _bin(pct: float) -> int:
    return min(len(_BINS) - 1, int(pct / 100 * len(_BINS)))


def _esc(s: str) -> str:
    return html_mod.escape(str(s))


def _pct(aw: float, av: float) -> float | None:
    return None if not av else 100.0 * aw / av


_CSS = """
:root{
  --surface:#fcfcfb; --page:#f9f9f7; --ink:#0b0b0b; --ink-2:#52514e;
  --muted:#898781; --grid:#e1e0d9; --baseline:#c3c2b7;
  --border:rgba(11,11,11,.10); --series:#2a78d6; --empty:#f0efec;
  --tip-bg:#0b0b0b; --tip-ink:#ffffff;
}
@media (prefers-color-scheme: dark){
  :root{
    --surface:#1a1a19; --page:#0d0d0d; --ink:#ffffff; --ink-2:#c3c2b7;
    --muted:#898781; --grid:#2c2c2a; --baseline:#383835;
    --border:rgba(255,255,255,.10); --series:#3987e5; --empty:#383835;
    --tip-bg:#f4f4f2; --tip-ink:#0b0b0b;
  }
}
*{box-sizing:border-box}
body{margin:0;background:var(--page);color:var(--ink);
  font-family:system-ui,-apple-system,"Segoe UI",sans-serif;font-size:14px;line-height:1.45}
.wrap{max-width:1100px;margin:0 auto;padding:28px 20px 64px}
h1{font-size:21px;margin:0 0 2px}
h2{font-size:15px;margin:0 0 12px}
.sub{color:var(--ink-2);margin:0 0 24px}
.card{background:var(--surface);border:1px solid var(--border);border-radius:10px;
  padding:18px 20px;margin-bottom:18px}
.kpis{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:12px;margin-bottom:18px}
.tile{background:var(--surface);border:1px solid var(--border);border-radius:10px;padding:14px 16px}
.tile .label{color:var(--ink-2);font-size:12.5px;margin-bottom:4px}
.tile .value{font-weight:600;font-size:27px}
.tile .note{color:var(--muted);font-size:12px;margin-top:2px}
/* tooltip — one fixed element, never clipped, sized for reading */
#tip{position:fixed;display:none;max-width:320px;background:var(--tip-bg);
  color:var(--tip-ink);padding:9px 12px;border-radius:8px;font-size:13.5px;
  line-height:1.4;z-index:10;pointer-events:none;box-shadow:0 4px 14px rgba(0,0,0,.25)}
#tip b{display:block;margin-bottom:2px}
[data-tip]{cursor:default}
/* heatmap */
.hm{overflow-x:auto}
.hm table{border-collapse:separate;border-spacing:2px}
.hm th{font-weight:500;color:var(--ink-2);font-size:12px;padding:2px 6px;text-align:left;white-space:nowrap}
.hm th.col{text-align:center;text-decoration:underline dotted var(--muted);text-underline-offset:3px}
.hm td{min-width:52px;height:30px;text-align:center;border-radius:4px;
  font-size:12px;font-variant-numeric:tabular-nums}
.hm td:hover,.hm th.col:hover{outline:2px solid var(--ink);outline-offset:-2px}
.hm td.na{background:var(--empty);color:var(--muted)}
.hm tr.cohort td{font-weight:600}
.hm tr.cohort th{color:var(--ink);font-weight:600}
.legend{display:flex;align-items:center;gap:6px;margin-top:10px;color:var(--ink-2);font-size:12px}
.legend .sw{width:26px;height:12px;border-radius:3px;display:inline-block}
/* bars */
.bars .row{display:grid;grid-template-columns:320px 1fr 52px;align-items:center;
  gap:10px;padding:5px 0;border-radius:6px}
.bars .row:hover{background:color-mix(in srgb,var(--ink) 5%,transparent)}
.bars .name{color:var(--ink-2);font-size:13px;text-align:right;white-space:nowrap;
  overflow:hidden;text-overflow:ellipsis}
.bars .track{border-left:1px solid var(--baseline);height:16px}
.bars .fill{height:16px;border-radius:0 4px 4px 0;min-width:2px}
.bars .val{font-size:12.5px;font-variant-numeric:tabular-nums;color:var(--ink)}
@media (max-width:700px){.bars .row{grid-template-columns:170px 1fr 48px}}
/* tables */
table.plain{border-collapse:collapse;width:100%}
table.plain th{color:var(--ink-2);font-weight:500;font-size:12.5px;text-align:left;
  border-bottom:1px solid var(--baseline);padding:6px 10px 6px 0}
table.plain td{border-bottom:1px solid var(--grid);padding:6px 10px 6px 0;vertical-align:top}
table.plain td.num{font-variant-numeric:tabular-nums;text-align:right}
.pill{display:inline-block;border:1px solid var(--border);border-radius:99px;
  padding:1px 9px;margin:2px 4px 2px 0;font-size:12px;color:var(--ink-2)}
.warn{color:#a15c00}
details{margin-top:12px}
summary{cursor:pointer;color:var(--ink-2);font-size:13px}
.foot{color:var(--muted);font-size:12px;margin-top:26px}
"""

# One fixed tooltip element fed by data-tip / data-tip-title attributes:
# readable size, never clipped by scroll containers, clamped to the viewport.
_TIP_JS = """
const tip = document.getElementById('tip');
function show(e){
  const el = e.target.closest('[data-tip]');
  if(!el){ tip.style.display='none'; return; }
  const t = el.getAttribute('data-tip-title');
  tip.innerHTML = (t ? '<b></b>' : '');
  if(t) tip.querySelector('b').textContent = t;
  tip.appendChild(document.createTextNode(el.getAttribute('data-tip')));
  tip.style.display='block';
  const pad = 14, w = tip.offsetWidth, h = tip.offsetHeight;
  let x = e.clientX + pad, y = e.clientY + pad;
  if (x + w > innerWidth - 8)  x = e.clientX - w - pad;
  if (y + h > innerHeight - 8) y = e.clientY - h - pad;
  tip.style.left = Math.max(8,x) + 'px';
  tip.style.top  = Math.max(8,y) + 'px';
}
document.addEventListener('mousemove', show);
document.addEventListener('mouseleave', () => tip.style.display='none');
"""


def _cell(pct: float | None, tip_title: str, tip_body: str) -> str:
    if pct is None:
        return (
            f'<td class="na" data-tip-title="{_esc(tip_title)}" '
            f'data-tip="Not assessed by this test">—</td>'
        )
    b = _bin(pct)
    return (
        f'<td class="b{b}" data-tip-title="{_esc(tip_title)}" '
        f'data-tip="{_esc(tip_body)}">{pct:.0f}</td>'
    )


def _bin_css() -> str:
    light = "".join(f".hm td.b{i}{{background:{bg};color:{ink}}}" for i, (bg, ink, _, _) in enumerate(_BINS))
    dark = "".join(f".hm td.b{i}{{background:{bg};color:{ink}}}" for i, (_, _, bg, ink) in enumerate(_BINS))
    # Bars reuse the heat scale so strand bars read on the same traffic light.
    light += "".join(f".bars .fill.b{i}{{background:{bg}}}" for i, (bg, _, _, _) in enumerate(_BINS))
    dark_b = "".join(f".bars .fill.b{i}{{background:{bg}}}" for i, (_, _, bg, _) in enumerate(_BINS))
    return f"{light}@media (prefers-color-scheme: dark){{{dark}{dark_b}}}"


def render_report(result: AttainmentResult, pack: CurriculumPack) -> str:
    outcomes = {o.code: o for o in pack.outcomes}
    dim_names = {d.id: (d.name or d.id) for d in pack.dimensions}
    codes = result.assessed_codes

    def outcome_tip(code: str) -> tuple[str, str]:
        o = outcomes[code]
        dim = dim_names.get(o.dimension, o.dimension)
        title = f"{code} · {dim} — {o.strand}" + (f" · {o.topic}" if o.topic else "")
        return title, o.description

    # ---- KPI tiles -----------------------------------------------------------
    total_aw = sum(v[0] for v in result.cohort.values())
    total_av = sum(v[1] for v in result.cohort.values())
    cohort_pct = _pct(total_aw, total_av)
    weakest = min(codes, key=lambda c: _pct(*result.cohort[c]) or 0) if codes else None
    tiles = [
        ("Students", str(len(result.students)), ""),
        ("Cohort attainment", f"{cohort_pct:.0f}%" if cohort_pct is not None else "—",
         "marks earned vs available on tagged questions"),
        ("Outcomes assessed", str(len(codes)),
         f"{len(result.unassessed)} at this level not yet assessed"),
        ("Weakest outcome", weakest or "—",
         f"{_pct(*result.cohort[weakest]):.0f}% facility" if weakest else ""),
    ]
    kpi_html = "".join(
        f'<div class="tile"><div class="label">{_esc(l)}</div>'
        f'<div class="value">{_esc(v)}</div>'
        + (f'<div class="note">{_esc(n)}</div>' if n else "") + "</div>"
        for l, v, n in tiles
    )

    # ---- Heatmap --------------------------------------------------------------
    head = "<tr><th></th>" + "".join(
        '<th class="col" data-tip-title="{t}" data-tip="{d}">{c}</th>'.format(
            t=_esc(outcome_tip(c)[0]), d=_esc(outcome_tip(c)[1]), c=_esc(c)
        )
        for c in codes
    ) + "</tr>"
    cohort_row = '<tr class="cohort"><th>Cohort</th>' + "".join(
        _cell(_pct(*result.cohort[c]), *_with_pct("Cohort", c, result.cohort[c], outcome_tip))
        for c in codes
    ) + "</tr>"
    student_rows = "".join(
        f"<tr><th>{_esc(sid)}</th>"
        + "".join(
            _cell(
                _pct(*result.per_student.get((sid, c), [0.0, 0.0])),
                *_with_pct(sid, c, result.per_student.get((sid, c), [0.0, 0.0]), outcome_tip),
            )
            for c in codes
        )
        + "</tr>"
        for sid in result.students
    )
    legend = '<div class="legend"><span>0%</span>' + "".join(
        f'<span class="sw" style="background:{bg}"></span>' for bg, *_ in _BINS
    ) + "<span>100%</span><span style=\"margin-left:12px\">red = reteach · green = secure · — = not assessed</span></div>"

    table_twin_rows = "".join(
        f"<tr><td>{_esc(sid)}</td><td>{_esc(c)}</td>"
        f"<td>{_esc(outcome_tip(c)[0].split(' · ', 1)[1])}</td>"
        f'<td class="num">{aw:g}</td><td class="num">{av:g}</td>'
        f'<td class="num">{(100*aw/av):.0f}%</td></tr>'
        for (sid, c), (aw, av) in sorted(result.per_student.items()) if av
    )
    table_twin = (
        "<details><summary>Table view (all values)</summary>"
        '<table class="plain"><tr><th>Student</th><th>Code</th><th>Strand</th>'
        "<th>Awarded</th><th>Available</th><th>%</th></tr>" + table_twin_rows + "</table></details>"
    )

    # ---- Strand / dimension bars (heat-coloured, official labels) -------------
    def bar_rows(data: dict[str, list[float]]) -> str:
        rows = []
        for name, (aw, av) in sorted(data.items(), key=lambda kv: -(_pct(*kv[1]) or 0)):
            pct = _pct(aw, av)
            if pct is None:
                continue
            rows.append(
                f'<div class="row" data-tip-title="{_esc(name)}" '
                f'data-tip="{pct:.0f}% attainment — {aw:g} of {av:g} marks across the cohort">'
                f'<div class="name">{_esc(name)}</div>'
                f'<div class="track"><div class="fill b{_bin(pct)}" style="width:{pct:.1f}%"></div></div>'
                f'<div class="val">{pct:.0f}%</div></div>'
            )
        return "".join(rows)

    # ---- Misconceptions ---------------------------------------------------------
    if result.misconceptions:
        mis_rows = "".join(
            f"<tr><td>{_esc(m.text)}</td><td class='num'>{m.count}</td>"
            f"<td>{_esc(m.question_id)} ({_esc(m.option)})</td>"
            f"<td>{_esc(', '.join(m.outcome_codes)) or '—'}</td></tr>"
            for m in result.misconceptions
        )
        mis_html = (
            '<table class="plain"><tr><th>Misconception</th><th>Students</th>'
            "<th>Evidence</th><th>Outcomes</th></tr>" + mis_rows + "</table>"
        )
    else:
        mis_html = '<p class="sub">No noted distractors were chosen — add distractor_notes in key.yaml to grow this.</p>'

    # ---- Coverage audit ------------------------------------------------------------
    unassessed_html = (
        "".join(
            f'<span class="pill" data-tip-title="{_esc(outcome_tip(c)[0])}" '
            f'data-tip="{_esc(outcomes[c].description)}">{_esc(c)}</span>'
            for c in result.unassessed
        )
        or '<p class="sub">Every outcome at this level has been assessed.</p>'
    )
    untagged_note = (
        f'<p class="warn">⚠ Untagged questions excluded from this report: '
        f"{_esc(', '.join(result.untagged_questions))} — run <code>markable tag</code>.</p>"
        if result.untagged_questions
        else ""
    )

    return f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Curriculum report — {_esc(result.test_id)}</title>
<style>{_CSS}{_bin_css()}</style></head>
<body><div class="wrap">
<h1>Curriculum report — {_esc(result.test_id)}</h1>
<p class="sub">Standards-referenced attainment against {_esc(result.curriculum)}.
Hover any code, cell, or strand for detail. Every figure is marks earned vs
marks available on questions tagged to that outcome.</p>
{untagged_note}
<div class="kpis">{kpi_html}</div>

<div class="card"><h2>Attainment by outcome — cohort and per student</h2>
<div class="hm"><table>{head}{cohort_row}{student_rows}</table></div>
{legend}{table_twin}</div>

<div class="card"><h2>Cohort attainment by strand</h2>
<div class="bars">{bar_rows(result.strand_cohort)}</div></div>

<div class="card"><h2>Cohort attainment by dimension</h2>
<div class="bars">{bar_rows(result.dimension_cohort)}</div></div>

<div class="card"><h2>Misconceptions to reteach</h2>{mis_html}</div>

<div class="card"><h2>Coverage audit — not yet assessed at this level</h2>
{unassessed_html}</div>

<p class="foot">Generated by Markable · single-file report — safe to email or archive ·
evidence for every mark lives in the assessment package (scripts/ crops + marks.json)</p>
</div>
<div id="tip"></div>
<script>{_TIP_JS}</script>
</body></html>"""


def _with_pct(who: str, code: str, pair: list[float], outcome_tip) -> tuple[str, str]:
    title, desc = outcome_tip(code)
    aw, av = pair
    detail = f"{who}: {aw:g} of {av:g} marks. {desc}" if av else desc
    return f"{who} · {title}", detail
