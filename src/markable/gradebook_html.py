"""Render the gradebook dashboard — one self-contained, tabbed HTML file.

(A JS port of this renderer also lives in `studio_html.py` for the in-browser
upload box; keep the two visual systems in step when either changes.)


Power BI-style, electric-green, no libraries or network (a few lines of vanilla
JS drive tab switching + the shared tooltip). Tabs:

- **Overview** — cohort KPIs across all SACs, a SAC-comparison bar, and a
  per-student × SAC results matrix (each student's trajectory + overall).
- **One tab per SAC** — KPIs, score distribution, the question × cohort-quartile
  performance matrix, and per-question difficulty (the question-level analysis).
- **Skills & content** — where a study design is supplied: each SAC's questions
  mapped to study-design areas, and a per-student × area attainment heatmap
  (green→red traffic light) answering "what is each student performing to".

Colour: the question-performance matrices use the validated electric-green
sequential ramp (magnitude); the skills heatmap uses the semantic red→green
heat scale (state). Both were run through the dataviz palette validator; dark
mode is its own selected steps.
"""

from __future__ import annotations

import html as html_mod
from statistics import median

from .dashboard_html import (
    _GREEN_DARK,
    _GREEN_LIGHT,
    _INK_DARK,
    _INK_LIGHT,
    _ACCENT_DARK,
    _ACCENT_LIGHT,
)
from .dashboard_html import _bin as _green_bin
from .gradebook import SAC, Gradebook
from .standards_html import _BINS as _HEAT
from .studydesign import SkillsAttainment

_esc = html_mod.escape


def _heat_bin(pct: float) -> int:
    return min(len(_HEAT) - 1, int(pct / 100 * len(_HEAT)))


def _pct(aw: float, av: float) -> float | None:
    return None if not av else 100.0 * aw / av


def _difficulty(fac: float) -> str:
    return "easy" if fac >= 0.8 else "moderate" if fac >= 0.5 else "difficult"


# --------------------------------------------------------------------------- CSS

_CSS = f"""
:root{{
  --surface:#fcfcfb; --page:#f9f9f7; --ink:#0b0b0b; --ink-2:#52514e;
  --muted:#898781; --grid:#e1e0d9; --baseline:#c3c2b7;
  --border:rgba(11,11,11,.10); --accent:{_ACCENT_LIGHT};
  --accent-wash:rgba(0,163,68,.09); --empty:#f0efec; --tip-bg:#0b0b0b; --tip-ink:#fff;
}}
@media (prefers-color-scheme: dark){{
  :root{{
    --surface:#1a1a19; --page:#0d0d0d; --ink:#fff; --ink-2:#c3c2b7;
    --muted:#898781; --grid:#2c2c2a; --baseline:#383835;
    --border:rgba(255,255,255,.10); --accent:{_ACCENT_DARK};
    --accent-wash:rgba(18,217,95,.10); --empty:#383835; --tip-bg:#f4f4f2; --tip-ink:#0b0b0b;
  }}
}}
*{{box-sizing:border-box}}
body{{margin:0;background:var(--page);color:var(--ink);
  font-family:system-ui,-apple-system,"Segoe UI",sans-serif;font-size:14px;line-height:1.45}}
.wrap{{max-width:1180px;margin:0 auto;padding:24px 20px 64px}}
h1{{font-size:22px;margin:0 0 2px}}
h2{{font-size:15px;margin:0 0 12px}}
.sub{{color:var(--ink-2);margin:0 0 16px}}
/* tabs */
.tabs{{display:flex;flex-wrap:wrap;gap:4px;border-bottom:1px solid var(--border);margin-bottom:20px}}
.tabs button{{appearance:none;background:none;border:0;border-bottom:3px solid transparent;
  color:var(--ink-2);font:inherit;font-size:13.5px;padding:9px 14px;cursor:pointer;
  border-radius:6px 6px 0 0}}
.tabs button:hover{{background:var(--accent-wash);color:var(--ink)}}
.tabs button.active{{color:var(--ink);border-bottom-color:var(--accent);font-weight:600}}
.tab{{display:none}} .tab.active{{display:block}}
.kpis{{display:grid;grid-template-columns:repeat(auto-fit,minmax(132px,1fr));gap:12px;margin-bottom:18px}}
.tile{{background:var(--surface);border:1px solid var(--border);border-radius:10px;padding:13px 15px}}
.tile .label{{color:var(--ink-2);font-size:12px;margin-bottom:4px}}
.tile .value{{font-weight:600;font-size:25px}} .tile .value.hero{{font-size:44px;line-height:1.05}}
.tile .note{{color:var(--muted);font-size:11.5px;margin-top:2px}}
.card{{background:var(--surface);border:1px solid var(--border);border-radius:10px;padding:18px 20px;margin-bottom:18px}}
/* histogram */
.hist{{display:grid;grid-template-columns:repeat(10,1fr);gap:6px;align-items:end;height:140px;
  border-bottom:1px solid var(--baseline);padding:0 2px}}
.hist .col{{position:relative;background:var(--accent);border-radius:4px 4px 0 0;min-height:2px}}
.hist .col .n{{position:absolute;top:-18px;width:100%;text-align:center;font-size:11px;
  color:var(--ink-2);font-variant-numeric:tabular-nums}}
.hist-x{{display:grid;grid-template-columns:repeat(10,1fr);gap:6px;padding:4px 2px 0;
  color:var(--muted);font-size:10.5px;text-align:center}}
/* matrix / heatmap */
.mx{{overflow-x:auto}}
.mx table{{border-collapse:separate;border-spacing:2px}}
.mx th{{font-weight:500;color:var(--ink-2);font-size:11.5px;padding:2px 6px;text-align:center;white-space:nowrap}}
.mx th.rowh{{text-align:left;position:sticky;left:0;background:var(--surface);z-index:1}}
.mx td{{min-width:44px;height:28px;text-align:center;border-radius:4px;font-size:11.5px;font-variant-numeric:tabular-nums}}
.mx td:hover{{outline:2px solid var(--ink);outline-offset:-2px}}
.mx td.na{{background:var(--empty);color:var(--muted)}}
.mx tr.cohort td,.mx tr.cohort th{{font-weight:600}}
.legend{{display:flex;align-items:center;gap:6px;margin-top:10px;color:var(--ink-2);font-size:12px}}
.legend .sw{{width:24px;height:12px;border-radius:3px;display:inline-block}}
.chip{{display:inline-block;border-radius:99px;padding:1px 9px;font-size:11.5px;border:1px solid var(--border);color:var(--ink-2)}}
.chip.easy{{border-color:var(--accent)}} .chip.difficult{{border-color:#d03b3b;color:#d03b3b}}
.chip.src-auto{{border-color:var(--accent)}} .chip.src-unmapped{{border-color:#d03b3b;color:#d03b3b}}
table.plain{{border-collapse:collapse;width:100%}}
table.plain th{{color:var(--ink-2);font-weight:500;font-size:12px;text-align:left;border-bottom:1px solid var(--baseline);padding:6px 10px 6px 0;white-space:nowrap}}
table.plain td{{border-bottom:1px solid var(--grid);padding:6px 10px 6px 0}}
table.plain td.num{{font-variant-numeric:tabular-nums;text-align:right}}
table.plain tr:hover td{{background:var(--accent-wash)}}
.bars .row{{display:grid;grid-template-columns:260px 1fr 54px;align-items:center;gap:10px;padding:5px 0;border-radius:6px}}
.bars .row:hover{{background:var(--accent-wash)}}
.bars .name{{color:var(--ink-2);font-size:13px;text-align:right;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}}
.bars .track{{border-left:1px solid var(--baseline);height:16px}}
.bars .fill{{height:16px;border-radius:0 4px 4px 0;min-width:2px;background:var(--accent)}}
.bars .val{{font-size:12.5px;font-variant-numeric:tabular-nums}}
@media(max-width:700px){{.bars .row{{grid-template-columns:150px 1fr 48px}}}}
.caveat{{border-left:3px solid var(--accent);padding:8px 12px;background:var(--accent-wash);border-radius:0 8px 8px 0;font-size:13px;color:var(--ink-2);margin-bottom:18px}}
.foot{{color:var(--muted);font-size:12px;margin-top:26px}}
#tip{{position:fixed;display:none;max-width:340px;background:var(--tip-bg);color:var(--tip-ink);padding:9px 12px;border-radius:8px;font-size:13.5px;line-height:1.4;z-index:20;pointer-events:none;box-shadow:0 4px 14px rgba(0,0,0,.25)}}
#tip b{{display:block;margin-bottom:2px}}
"""


def _ramp_css() -> str:
    g_light = "".join(f".mx td.g{i}{{background:{bg};color:{ink}}}" for i, (bg, ink) in enumerate(zip(_GREEN_LIGHT, _INK_LIGHT)))
    g_dark = "".join(f".mx td.g{i}{{background:{bg};color:{ink}}}" for i, (bg, ink) in enumerate(zip(_GREEN_DARK, _INK_DARK)))
    h_light = "".join(f".mx td.h{i}{{background:{bg};color:{ink}}}" for i, (bg, ink, _, _) in enumerate(_HEAT))
    h_dark = "".join(f".mx td.h{i}{{background:{bg};color:{ink}}}" for i, (_, _, bg, ink) in enumerate(_HEAT))
    gsw = "".join(f".gsw{i}{{background:{c}}}" for i, c in enumerate(_GREEN_LIGHT))
    hsw = "".join(f".hsw{i}{{background:{c}}}" for i, (c, *_ ) in enumerate(_HEAT))
    dark_sw = "@media (prefers-color-scheme: dark){" + \
        "".join(f".gsw{i}{{background:{c}}}" for i, c in enumerate(_GREEN_DARK)) + \
        "".join(f".hsw{i}{{background:{c}}}" for i, (_, _, c, _) in enumerate(_HEAT)) + "}"
    return g_light + h_light + gsw + hsw + "@media (prefers-color-scheme: dark){" + g_dark + h_dark + "}" + dark_sw


_JS = """
function markTab(id){document.querySelectorAll('.tab').forEach(t=>t.classList.toggle('active',t.id===id));
document.querySelectorAll('.tabs button').forEach(b=>b.classList.toggle('active',b.dataset.t===id));}
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


# --------------------------------------------------------------------------- stats


def _sac_totals(sac: SAC):
    totals = {st.name: sac.total_for(st) for st in sac.students}
    pct = {n: 100 * t / sac.total_marks for n, t in totals.items() if sac.total_marks}
    return totals, pct


def _quartile_seg(pct: dict[str, float]) -> dict[str, int]:
    ranked = sorted(pct, key=lambda n: -pct[n])
    n = len(ranked)
    out = {}
    for i, name in enumerate(ranked):
        q = min(4, 1 + (i * 4) // n) if n else 1
        out[name] = 1 if q == 1 else 3 if q == 4 else 2
    return out


# --------------------------------------------------------------------------- tiles/hist


def _tiles(items) -> str:
    return "".join(
        f'<div class="tile"><div class="label">{_esc(l)}</div>'
        f'<div class="value{" hero" if hero else ""}">{_esc(v)}</div>'
        + (f'<div class="note">{_esc(n)}</div>' if n else "") + "</div>"
        for l, v, n, hero in items
    )


def _histogram(pct_values) -> str:
    bins = [0] * 10
    for v in pct_values:
        bins[min(9, int(v // 10))] += 1
    peak = max(bins) or 1
    cols = "".join(
        f'<div class="col" style="height:{max(2, b / peak * 100):.0f}%" '
        f'data-tip-title="{i*10}–{i*10+9}%" data-tip="{b} student(s)">'
        + (f'<span class="n">{b}</span>' if b else "") + "</div>"
        for i, b in enumerate(bins)
    )
    xs = "".join(f"<span>{i*10}</span>" for i in range(10))
    return f'<div class="hist">{cols}</div><div class="hist-x">{xs}</div>'


# --------------------------------------------------------------------------- SAC tab


def _sac_tab(sac: SAC, idx: int) -> str:
    totals, pct = _sac_totals(sac)
    seg = _quartile_seg(pct)
    seg_name = {0: "All", 1: "Top 25%", 2: "Middle 50%", 3: "Bottom 25%"}
    values = sorted(pct.values())

    tiles = _tiles([
        ("Class average", f"{sum(values)/len(values):.0f}%", f"of {sac.total_marks:g} marks", True),
        ("Median", f"{median(values):.0f}%", "", False),
        ("Highest", f"{max(values):.0f}%", "", False),
        ("Lowest", f"{min(values):.0f}%", "", False),
        ("At or above 70%", f"{sum(1 for v in values if v >= 70)}", f"of {len(values)}", False),
        ("Below 50%", f"{sum(1 for v in values if v < 50)}", "intervention", False),
    ])

    # question × quartile-segment facility
    def facility(q, subset) -> float | None:
        marks = [st.marks.get(q.id, 0.0) for st in sac.students if st.name in subset]
        return None if not marks or not q.max_marks else sum(marks) / (q.max_marks * len(marks))

    all_names = set(pct)
    seg_sets = {s: {n for n in pct if seg[n] == s} for s in (1, 2, 3)}
    seg_sets[0] = all_names

    def cell(q, s) -> str:
        f = facility(q, seg_sets[s])
        if f is None:
            return '<td class="na">—</td>'
        p = f * 100
        return (f'<td class="g{_green_bin(p)}" data-tip-title="{_esc(q.id)} · {seg_name[s]}" '
                f'data-tip="{p:.0f}% of marks earned (max {q.max_marks:g})">{p:.0f}</td>')

    rows = []
    for q in sac.questions:
        f = facility(q, all_names) or 0
        diff = _difficulty(f)
        rows.append(
            f'<tr><th class="rowh" data-tip-title="Question {_esc(q.id)}" '
            f'data-tip="Max {q.max_marks:g} marks · cohort facility {f*100:.0f}%">{_esc(q.id)}</th>'
            + "".join(cell(q, s) for s in (0, 1, 2, 3))
            + f'<td style="background:none"><span class="chip {diff}">{diff}</span></td></tr>'
        )
    head = ('<tr><th class="rowh">Question</th>'
            + "".join(f"<th>{seg_name[s]}</th>" for s in (0, 1, 2, 3)) + "<th>Difficulty</th></tr>")
    legend = ('<div class="legend"><span>0%</span>'
              + "".join(f'<span class="sw gsw{i}"></span>' for i in range(7))
              + "<span>100%</span></div>")

    return f"""<div class="tab" id="sac{idx}">
<h2>SAC {_esc(sac.number)} — {_esc(sac.topic)}</h2>
<div class="kpis">{tiles}</div>
<div class="card"><h2>Score distribution</h2>{_histogram(values)}</div>
<div class="card"><h2>Question performance by cohort quartile</h2>
<div class="mx"><table>{head}{''.join(rows)}</table></div>{legend}
<p class="foot">Hover a question or cell for detail · easy ≥80% · moderate 50–79% · difficult &lt;50%</p></div>
</div>"""


# --------------------------------------------------------------------------- overview tab


def _overview_tab(gb: Gradebook) -> str:
    sac_pct = {sac.sheet: _sac_totals(sac)[1] for sac in gb.sacs}
    all_students = sorted({n for p in sac_pct.values() for n in p})

    # cohort KPIs across SACs
    all_vals = [v for p in sac_pct.values() for v in p.values()]
    tiles = _tiles([
        ("Students", str(len(all_students)), "", True),
        ("SACs", str(len(gb.sacs)), "", False),
        ("Overall average", f"{sum(all_vals)/len(all_vals):.0f}%", "across all SACs", False),
        ("Best SAC", max(gb.sacs, key=lambda s: sum(sac_pct[s.sheet].values())/len(sac_pct[s.sheet])).topic[:18],
         f"{max(sum(p.values())/len(p) for p in sac_pct.values()):.0f}%", False),
    ])

    # SAC comparison bars (cohort average per SAC)
    bar_rows = []
    for sac in gb.sacs:
        p = sac_pct[sac.sheet]
        avg = sum(p.values()) / len(p)
        bar_rows.append(
            f'<div class="row" data-tip-title="SAC {_esc(sac.number)} — {_esc(sac.topic)}" '
            f'data-tip="Cohort average {avg:.0f}% of {sac.total_marks:g} marks · {len(p)} students">'
            f'<div class="name">SAC {_esc(sac.number)}: {_esc(sac.topic)}</div>'
            f'<div class="track"><div class="fill" style="width:{avg:.1f}%"></div></div>'
            f'<div class="val">{avg:.0f}%</div></div>'
        )

    # per-student × SAC matrix (heat), + overall
    head = ('<tr><th class="rowh">Student</th>'
            + "".join(f'<th>SAC {_esc(s.number)}</th>' for s in gb.sacs)
            + "<th>Overall</th></tr>")
    student_rows = []
    for name in all_students:
        vals = [sac_pct[s.sheet].get(name) for s in gb.sacs]
        present = [v for v in vals if v is not None]
        overall = sum(present) / len(present) if present else None
        cells = ""
        for s, v in zip(gb.sacs, vals):
            if v is None:
                cells += '<td class="na">—</td>'
            else:
                cells += (f'<td class="h{_heat_bin(v)}" data-tip-title="{_esc(name)} · SAC {_esc(s.number)}" '
                          f'data-tip="{v:.0f}% — {s.topic}">{v:.0f}</td>')
        ov = "—" if overall is None else f'{overall:.0f}'
        ov_cls = "na" if overall is None else f"h{_heat_bin(overall)}"
        student_rows.append(f'<tr><th class="rowh">{_esc(name)}</th>{cells}<td class="{ov_cls}">{ov}</td></tr>')

    legend = ('<div class="legend"><span>0%</span>'
              + "".join(f'<span class="sw hsw{i}"></span>' for i in range(7))
              + "<span>100%</span><span style=\"margin-left:12px\">red = at risk · green = secure</span></div>")

    return f"""<div class="tab active" id="overview">
<div class="kpis">{tiles}</div>
<div class="card"><h2>Cohort average by SAC</h2><div class="bars">{''.join(bar_rows)}</div></div>
<div class="card"><h2>Every student across every SAC</h2>
<div class="mx"><table>{head}{''.join(student_rows)}</table></div>{legend}
<p class="foot">Scaled to percentage of each SAC's marks. Hover a cell for the topic.
Names shown for the owning teacher's local view only — never exported.</p></div>
</div>"""


# --------------------------------------------------------------------------- skills tab


def _skills_tab(skills: list[SkillsAttainment], pack_name: str) -> str:
    blocks = []
    for sk in skills:
        areas = sorted(sk.cohort_area, key=lambda a: _pct(*sk.cohort_area[a]) or 0)
        if not areas:
            continue
        # mapping table
        map_rows = "".join(
            f'<tr><td>{_esc(m.question_id)}</td><td class="num">{m.max_marks:g}</td>'
            f"<td>{_esc(', '.join(m.codes)) or '—'}</td>"
            f'<td><span class="chip src-{m.source}">{m.source}</span></td></tr>'
            for m in sk.question_maps
        )
        # per-student × area heatmap
        head = ('<tr><th class="rowh">Student</th>'
                + "".join(f'<th data-tip-title="{_esc(a)}" data-tip="{_esc(", ".join(sk.area_outcomes.get(a, [])))}">{_esc(_short_area(a))}</th>' for a in areas)
                + "</tr>")
        cohort_row = '<tr class="cohort"><th class="rowh">Cohort</th>' + "".join(
            _skill_cell(_pct(*sk.cohort_area[a]), f"Cohort · {a}") for a in areas
        ) + "</tr>"
        student_rows = "".join(
            f'<tr><th class="rowh">{_esc(name)}</th>'
            + "".join(_skill_cell(_pct(*sk.per_student_area.get((name, a), [0.0, 0.0])), f"{name} · {a}") for a in areas)
            + "</tr>"
            for name in sk.students
        )
        unmapped = (f'<p class="foot" style="color:#a15c00">⚠ Unmapped questions (no confident '
                    f'match — supply a teacher map): {_esc(", ".join(sk.unmapped))}</p>' if sk.unmapped else "")
        blocks.append(f"""<div class="card">
<h2>SAC {_esc(sk.sac_number)} — {_esc(sk.sac_topic)}: attainment by study-design area</h2>
<div class="mx"><table>{head}{cohort_row}{student_rows}</table></div>
<div class="legend"><span>0%</span>{''.join(f'<span class="sw hsw{i}"></span>' for i in range(7))}<span>100%</span>
<span style="margin-left:12px">red = reteach · green = secure</span></div>
<details><summary>Question → study-design mapping ({len(sk.question_maps)} items)</summary>
<table class="plain"><tr><th>Question / criterion</th><th>Marks</th><th>Study-design code(s)</th><th>Source</th></tr>{map_rows}</table></details>
{unmapped}</div>""")

    caveat = (f'<div class="caveat">Mapped against {_esc(pack_name)}. Codes are Markable\'s '
              "representative scheme, proposed from criterion names / teacher map — not official VCAA "
              "identifiers. Confirm the mapping and verify codes against the current VCE Study Design "
              "before official use.</div>")
    return f'<div class="tab" id="skills"><h2>Skills &amp; content by student</h2>{caveat}{"".join(blocks)}</div>'


def _short_area(area: str) -> str:
    # "Key science skills · Data & analysis" → "Data & analysis"
    return area.split("·", 1)[1].strip() if "·" in area else area


def _skill_cell(pct: float | None, tip: str) -> str:
    if pct is None:
        return f'<td class="na" data-tip-title="{_esc(tip)}" data-tip="not assessed">—</td>'
    return (f'<td class="h{_heat_bin(pct)}" data-tip-title="{_esc(tip)}" '
            f'data-tip="{pct:.0f}% of marks in this area">{pct:.0f}</td>')


# --------------------------------------------------------------------------- top level


def render_gradebook(gb: Gradebook, skills: list[SkillsAttainment] | None = None, pack_name: str = "") -> str:
    tabs = [('overview', 'Overview')]
    tab_bodies = [_overview_tab(gb)]
    for i, sac in enumerate(gb.sacs):
        tabs.append((f"sac{i}", f"SAC {sac.number}"))
        tab_bodies.append(_sac_tab(sac, i))
    if skills:
        tabs.append(("skills", "Skills & content"))
        tab_bodies.append(_skills_tab(skills, pack_name))

    def _button(tid: str, label: str) -> str:
        active = ' class="active"' if tid == "overview" else ""
        return f'<button data-t="{tid}"{active} onclick="markTab(&#39;{tid}&#39;)">{_esc(label)}</button>'

    tab_buttons = "".join(_button(tid, label) for tid, label in tabs)

    return f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>SAC dashboard — {_esc(gb.source)}</title>
<style>{_CSS}{_ramp_css()}</style></head>
<body><div class="wrap">
<h1>SAC results dashboard</h1>
<p class="sub">{_esc(gb.source)} · {len(gb.sacs)} SACs · single-file dashboard — no dev tools, works offline</p>
<div class="tabs">{tab_buttons}</div>
{''.join(tab_bodies)}
<p class="foot">Generated by Markable · single-file dashboard — safe to email or archive ·
student names are for the owning teacher's local view and never leave this file</p>
</div>
<div id="tip"></div>
<script>{_JS}</script>
</body></html>"""
