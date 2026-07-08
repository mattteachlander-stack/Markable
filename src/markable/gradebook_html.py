"""Render the gradebook dashboard — one self-contained, tabbed HTML file.

Landscape, Power BI-style, professional blue chrome with a green→red heat scale
for every performance matrix. No libraries or network (a little vanilla JS drives
tabs + the shared tooltip + the student picker). Tabs:

- **Overview** — cohort KPIs, SAC-comparison bars, and a per-student × SAC heat
  matrix (each student's trajectory + overall).
- **One tab per SAC** — KPIs, score distribution, and the question performance
  matrix **run lengthways** (questions along the top, cohort quartiles down the
  side, a difficulty row) plus per-question difficulty.
- **Classes** — class × SAC comparison (where the workbook has class groups).
- **Student** — pick any student; see their result on every SAC vs the cohort,
  their per-question detail, and their study-design areas. The "how did Milla
  Bird go" view.
- **Skills & content** — with a study design: each SAC's questions mapped to
  areas, and a per-student × area heat matrix.
"""

from __future__ import annotations

import html as html_mod
import json
from statistics import median

from .gradebook import SAC, Gradebook, classes
from .standards_html import _BINS as _HEAT
from .studydesign import SkillsAttainment

_esc = html_mod.escape


def _heat_bin(pct: float) -> int:
    return min(len(_HEAT) - 1, int(pct / 100 * len(_HEAT)))


def _pct(aw: float, av: float) -> float | None:
    return None if not av else 100.0 * aw / av


def _difficulty(fac: float) -> str:
    return "easy" if fac >= 0.8 else "moderate" if fac >= 0.5 else "difficult"


# Professional blue chrome + green→red heat for data.
_CSS = """
:root{
  --surface:#ffffff; --page:#f4f6fb; --ink:#0f1729; --ink-2:#48566f;
  --muted:#8a95a8; --grid:#e6eaf2; --baseline:#c7cede;
  --border:rgba(15,23,41,.10); --brand:#1e63d0; --brand-2:#2f80ed;
  --brand-wash:rgba(30,99,208,.08); --empty:#eef1f7; --tip-bg:#0f1729; --tip-ink:#fff;
}
@media (prefers-color-scheme: dark){
  :root{
    --surface:#141a26; --page:#0b0f17; --ink:#eaf0fb; --ink-2:#a9b6cc;
    --muted:#6f7c93; --grid:#232c3d; --baseline:#33405a;
    --border:rgba(255,255,255,.10); --brand:#4b93ff; --brand-2:#6aa8ff;
    --brand-wash:rgba(75,147,255,.12); --empty:#232c3d; --tip-bg:#eaf0fb; --tip-ink:#0f1729;
  }
}
*{box-sizing:border-box}
body{margin:0;background:var(--page);color:var(--ink);
  font-family:system-ui,-apple-system,"Segoe UI",sans-serif;font-size:14px;line-height:1.45}
.wrap{max-width:1360px;margin:0 auto;padding:22px 22px 64px}
h1{font-size:22px;margin:0 0 2px}
h2{font-size:15px;margin:0 0 12px}
h3{font-size:14px;margin:0 0 10px}
.sub{color:var(--ink-2);margin:0 0 16px}
.tabs{display:flex;flex-wrap:wrap;gap:4px;border-bottom:1px solid var(--border);margin-bottom:20px}
.tabs button{appearance:none;background:none;border:0;border-bottom:3px solid transparent;
  color:var(--ink-2);font:inherit;font-size:13.5px;padding:9px 14px;cursor:pointer;border-radius:8px 8px 0 0}
.tabs button:hover{background:var(--brand-wash);color:var(--ink)}
.tabs button.active{color:var(--brand);border-bottom-color:var(--brand);font-weight:600}
.tab{display:none} .tab.active{display:block}
.kpis{display:grid;grid-template-columns:repeat(auto-fit,minmax(128px,1fr));gap:12px;margin-bottom:18px}
.tile{background:var(--surface);border:1px solid var(--border);border-radius:12px;padding:13px 15px}
.tile .label{color:var(--ink-2);font-size:12px;margin-bottom:4px}
.tile .value{font-weight:650;font-size:25px}
.tile .value.hero{font-size:42px;line-height:1.05;color:var(--brand)}
.tile .note{color:var(--muted);font-size:11.5px;margin-top:2px}
.card{background:var(--surface);border:1px solid var(--border);border-radius:12px;padding:18px 20px;margin-bottom:18px;
  box-shadow:0 1px 2px rgba(15,23,41,.04)}
.grid2{display:grid;grid-template-columns:1fr 1fr;gap:16px}
@media(max-width:900px){.grid2{grid-template-columns:1fr}}
.hist{display:grid;grid-template-columns:repeat(10,1fr);gap:6px;align-items:end;height:140px;border-bottom:1px solid var(--baseline);padding:0 2px}
.hist .col{position:relative;background:var(--brand);border-radius:4px 4px 0 0;min-height:2px}
.hist .col .n{position:absolute;top:-18px;width:100%;text-align:center;font-size:11px;color:var(--ink-2);font-variant-numeric:tabular-nums}
.hist-x{display:grid;grid-template-columns:repeat(10,1fr);gap:6px;padding:4px 2px 0;color:var(--muted);font-size:10.5px;text-align:center}
.mx{overflow-x:auto}
.mx table{border-collapse:separate;border-spacing:2px}
.mx th{font-weight:500;color:var(--ink-2);font-size:11.5px;padding:2px 6px;text-align:center;white-space:nowrap}
.mx th.rowh{text-align:left;position:sticky;left:0;background:var(--surface);z-index:1}
.mx td{min-width:40px;height:28px;text-align:center;border-radius:4px;font-size:11.5px;font-variant-numeric:tabular-nums}
.mx td:hover{outline:2px solid var(--ink);outline-offset:-2px}
.mx td.na{background:var(--empty);color:var(--muted)}
.mx tr.cohort td,.mx tr.cohort th{font-weight:650}
.mx td.diff{background:none;min-width:64px}
.legend{display:flex;align-items:center;gap:6px;margin-top:10px;color:var(--ink-2);font-size:12px}
.legend .sw{width:24px;height:12px;border-radius:3px;display:inline-block}
.chip{display:inline-block;border-radius:99px;padding:1px 9px;font-size:11.5px;border:1px solid var(--border);color:var(--ink-2)}
.chip.easy{border-color:#2e9647;color:#2e9647} .chip.difficult{border-color:#c23b3b;color:#c23b3b}
.chip.src-auto{border-color:var(--brand)} .chip.src-unmapped{border-color:#c23b3b;color:#c23b3b}
table.plain{border-collapse:collapse;width:100%}
table.plain th{color:var(--ink-2);font-weight:500;font-size:12px;text-align:left;border-bottom:1px solid var(--baseline);padding:6px 10px 6px 0;white-space:nowrap}
table.plain td{border-bottom:1px solid var(--grid);padding:6px 10px 6px 0}
table.plain td.num{font-variant-numeric:tabular-nums;text-align:right}
table.plain tr:hover td{background:var(--brand-wash)}
.bars .row{display:grid;grid-template-columns:230px 1fr 54px;align-items:center;gap:10px;padding:5px 0;border-radius:6px}
.bars .row:hover{background:var(--brand-wash)}
.bars .name{color:var(--ink-2);font-size:13px;text-align:right;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.bars .track{border-left:1px solid var(--baseline);height:16px}
.bars .fill{height:16px;border-radius:0 4px 4px 0;min-width:2px}
.bars .val{font-size:12.5px;font-variant-numeric:tabular-nums}
@media(max-width:700px){.bars .row{grid-template-columns:140px 1fr 48px}}
select.picker{padding:8px 12px;border-radius:9px;border:1px solid var(--border);background:var(--surface);
  color:var(--ink);font:inherit;font-size:14px;min-width:240px}
.spot-head{display:flex;flex-wrap:wrap;gap:22px;align-items:baseline;margin:14px 0 4px}
.spot-head .big{font-size:34px;font-weight:700;color:var(--brand)}
.spot-head .meta{color:var(--ink-2)}
.tag{display:inline-block;background:var(--brand-wash);color:var(--brand);border-radius:99px;padding:2px 11px;font-size:12px;font-weight:600}
.foot{color:var(--muted);font-size:12px;margin-top:26px}
#tip{position:fixed;display:none;max-width:340px;background:var(--tip-bg);color:var(--tip-ink);padding:9px 12px;border-radius:8px;font-size:13.5px;line-height:1.4;z-index:20;pointer-events:none;box-shadow:0 6px 18px rgba(0,0,0,.25)}
#tip b{display:block;margin-bottom:2px}
.highlights{border-left:4px solid var(--brand)}
.highlights h4{font-size:12.5px;color:var(--ink-2);text-transform:uppercase;letter-spacing:.04em;margin:0 0 8px}
.hi-lead{margin:0 0 14px;color:var(--ink)}
.hi-cols{display:grid;grid-template-columns:1.3fr 1fr;gap:22px}
@media(max-width:760px){.hi-cols{grid-template-columns:1fr}}
.hi-list{list-style:none;margin:0;padding:0}
.hi-list li{padding:6px 0;border-bottom:1px solid var(--grid);font-size:13.5px}
.hi-list .hpct{display:inline-block;min-width:34px;text-align:center;border-radius:5px;padding:1px 6px;font-size:12px;font-variant-numeric:tabular-nums}
.hi-list .concept{color:var(--ink-2)}
.hi-area{font-size:13.5px} .muted{color:var(--muted)}
table.clsq td.concept-cell{color:var(--ink-2);font-size:12.5px}
table.clsq td.neg{color:#c23b3b;font-weight:600} table.clsq td.pos{color:#2e9647}
table.clsq tr.flag td{background:rgba(194,59,59,.07)}
.hi-list .hpct.h0,.hi-list .hpct.h1,.hi-list .hpct.h2{color:#fff}
"""


def _heat_css() -> str:
    light = "".join(f".mx td.h{i},.hpct.h{i}{{background:{bg};color:{ink}}}" for i, (bg, ink, _, _) in enumerate(_HEAT))
    dark = "".join(f".mx td.h{i},.hpct.h{i}{{background:{bg};color:{ink}}}" for i, (_, _, bg, ink) in enumerate(_HEAT))
    fill = "".join(f".bars .fill.h{i}{{background:{bg}}}" for i, (bg, *_ ) in enumerate(_HEAT))
    fill_d = "".join(f".bars .fill.h{i}{{background:{bg}}}" for i, (_, _, bg, _) in enumerate(_HEAT))
    sw = "".join(f".hsw{i}{{background:{c}}}" for i, (c, *_ ) in enumerate(_HEAT))
    sw_d = "".join(f".hsw{i}{{background:{c}}}" for i, (_, _, c, _) in enumerate(_HEAT))
    return (light + fill + sw + "@media (prefers-color-scheme: dark){" + dark + fill_d + sw_d + "}")


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

_LEGEND = ('<div class="legend"><span>0%</span>'
           + "".join(f'<span class="sw hsw{i}"></span>' for i in range(len(_HEAT)))
           + '<span>100%</span><span style="margin-left:12px">red = at risk · green = secure · — = not assessed</span></div>')


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


def _tiles(items) -> str:
    return "".join(
        f'<div class="tile"><div class="label">{_esc(l)}</div>'
        f'<div class="value{" hero" if hero else ""}">{_esc(v)}</div>'
        + (f'<div class="note">{_esc(n)}</div>' if n else "") + "</div>"
        for l, v, n, hero in items
    )


def _histogram(vals) -> str:
    bins = [0] * 10
    for v in vals:
        bins[min(9, int(v // 10))] += 1
    peak = max(bins) or 1
    cols = "".join(
        f'<div class="col" style="height:{max(2, b / peak * 100):.0f}%" '
        f'data-tip-title="{i*10}-{i*10+9}%" data-tip="{b} student(s)">'
        + (f'<span class="n">{b}</span>' if b else "") + "</div>"
        for i, b in enumerate(bins)
    )
    return f'<div class="hist">{cols}</div><div class="hist-x">' + "".join(f"<span>{i*10}</span>" for i in range(10)) + "</div>"


def _hcell(pct: float | None, title: str, body: str) -> str:
    if pct is None:
        return f'<td class="na" data-tip-title="{_esc(title)}" data-tip="{_esc(body)}">—</td>'
    return f'<td class="h{_heat_bin(pct)}" data-tip-title="{_esc(title)}" data-tip="{_esc(body)}">{pct:.0f}</td>'


def _facility(sac: SAC, qid: str, names: set) -> float | None:
    q = next((q for q in sac.questions if q.id == qid), None)
    if q is None or not q.max_marks:
        return None
    marks = [st.marks.get(qid, 0.0) for st in sac.students if st.name in names]
    return None if not marks else sum(marks) / (q.max_marks * len(marks))


def _qmeta(skills: list[SkillsAttainment] | None) -> dict:
    """{sac_number: {qid: {"codes": [...], "area": str}}} from the study-design map."""
    out: dict = {}
    for sk in skills or []:
        out[sk.sac_number] = {
            m.question_id: {"codes": m.codes, "area": (m.areas[0] if m.areas else "")}
            for m in sk.question_maps
        }
    return out


def _short_area(area: str) -> str:
    return area.split("·", 1)[1].strip() if "·" in area else area


def _highlights_card(gb: Gradebook, skills: list[SkillsAttainment] | None, term: str) -> str:
    """Key highlights: hardest questions (with linked codes/concepts) + weakest area."""
    qmeta = _qmeta(skills)
    hardest = []  # (facility, sac, qid, meta)
    for sac in gb.sacs:
        names = {st.name for st in sac.students}
        for q in sac.questions:
            f = _facility(sac, q.id, names)
            if f is not None:
                hardest.append((f, sac, q.id, qmeta.get(sac.number, {}).get(q.id, {})))
    hardest.sort(key=lambda t: t[0])
    top = hardest[:5]

    def meta_str(m: dict) -> str:
        code = ", ".join(m.get("codes") or [])
        area = _short_area(m.get("area") or "")
        bits = " · ".join(x for x in (area, code) if x)
        return f" — {_esc(bits)}" if bits else ""

    items = "".join(
        f'<li><b>{_esc(qid)}</b> <span class="muted">({_esc(sac.topic)})</span> — '
        f'<span class="hpct h{_heat_bin(f*100)}">{f*100:.0f}%</span>'
        f'<span class="concept">{meta_str(m)}</span></li>'
        for f, sac, qid, m in top
    )

    # weakest / strongest study-design area across the cohort
    area_line = ""
    if skills:
        agg: dict[str, list[float]] = {}
        for sk in skills:
            for area, (aw, av) in sk.cohort_area.items():
                if av:
                    a = agg.setdefault(area, [0.0, 0.0])
                    a[0] += aw
                    a[1] += av
        pcts = {a: 100 * v[0] / v[1] for a, v in agg.items() if v[1]}
        if pcts:
            weak = min(pcts, key=pcts.get)
            strong = max(pcts, key=pcts.get)
            area_line = (f'<p class="hi-area">Weakest area: <b>{_esc(_short_area(weak))}</b> '
                         f'({pcts[weak]:.0f}%) · Strongest: <b>{_esc(_short_area(strong))}</b> ({pcts[strong]:.0f}%)</p>')

    all_pct = [100 * sac.total_for(st) / sac.total_marks
               for sac in gb.sacs for st in sac.students if sac.total_marks]
    avg = sum(all_pct) / len(all_pct) if all_pct else 0
    below = sum(1 for p in all_pct if p < 50)

    return f"""<div class="card highlights">
<h3>🔑 Key highlights</h3>
<p class="hi-lead">Cohort average <b>{avg:.0f}%</b> across {len(gb.sacs)} {_esc(term.lower())}(s) ·
{below} result(s) below 50% flagged for support.</p>
<div class="hi-cols">
  <div><h4>Hardest questions</h4><ul class="hi-list">{items}</ul></div>
  <div><h4>Where to focus</h4>{area_line or '<p class="muted">Add a study design to link questions to concepts/codes.</p>'}
  <p class="muted" style="margin-top:8px">Each hardest question shows its linked concept and curriculum code where mapped.</p></div>
</div></div>"""


def _classq_payload(gb: Gradebook, skills: list[SkillsAttainment] | None) -> dict:
    """Per-class, per-question facility + cohort facility + linked code/area."""
    qmeta = _qmeta(skills)
    cls = classes(gb)
    assessments = []
    by_class: dict = {c: {} for c in cls}
    for sac in gb.sacs:
        all_names = {st.name for st in sac.students}
        qlist = []
        for q in sac.questions:
            fc = _facility(sac, q.id, all_names)
            m = qmeta.get(sac.number, {}).get(q.id, {})
            qlist.append({
                "id": q.id, "max": q.max_marks,
                "cohort": None if fc is None else round(fc * 100),
                "codes": m.get("codes") or [], "area": _short_area(m.get("area") or ""),
            })
        assessments.append({"number": sac.number, "topic": sac.topic, "questions": qlist})
        for c in cls:
            names = {st.name for st in sac.students if st.class_group == c}
            by_class[c][sac.number] = {
                q.id: (lambda f: None if f is None else round(f * 100))(_facility(sac, q.id, names))
                for q in sac.questions
            }
    return {"classes": cls, "assessments": assessments, "byClass": by_class}


# --------------------------------------------------------------------------- SAC tab (lengthways)


def _sac_tab(sac: SAC, idx: int, term: str = "SAC") -> str:
    totals, pct = _sac_totals(sac)
    seg = _quartile_seg(pct)
    seg_names = [(0, "All"), (1, "Top 25%"), (2, "Middle 50%"), (3, "Bottom 25%")]
    values = sorted(pct.values())
    seg_sets = {0: set(pct), 1: {n for n in pct if seg[n] == 1}, 2: {n for n in pct if seg[n] == 2}, 3: {n for n in pct if seg[n] == 3}}

    tiles = _tiles([
        ("Class average", f"{sum(values)/len(values):.0f}%", f"of {sac.total_marks:g} marks", True),
        ("Median", f"{median(values):.0f}%", "", False),
        ("Highest", f"{max(values):.0f}%", "", False),
        ("Lowest", f"{min(values):.0f}%", "", False),
        ("At or above 70%", f"{sum(1 for v in values if v >= 70)}", f"of {len(values)}", False),
        ("Below 50%", f"{sum(1 for v in values if v < 50)}", "intervention", False),
    ])

    def facility(q, subset) -> float | None:
        marks = [st.marks.get(q.id, 0.0) for st in sac.students if st.name in subset]
        return None if not marks or not q.max_marks else sum(marks) / (q.max_marks * len(marks))

    # Questions down the rows, cohort quartiles across the columns.
    head = ('<tr><th class="rowh">Question</th>'
            + "".join(f"<th>{label}</th>" for _s, label in seg_names)
            + "<th>Difficulty</th></tr>")
    rows = ""
    for q in sac.questions:
        cells = ""
        for s, label in seg_names:
            f = facility(q, seg_sets[s])
            cells += _hcell(None if f is None else f * 100, f"{q.id} · {label}",
                            "" if f is None else f"{f*100:.0f}% of marks (max {q.max_marks:g})")
        f_all = facility(q, seg_sets[0]) or 0
        d = _difficulty(f_all)
        rows += (f'<tr><th class="rowh" data-tip-title="Question {_esc(q.id)}" '
                 f'data-tip="Max {q.max_marks:g} marks · cohort {f_all*100:.0f}%">{_esc(q.id)}</th>'
                 f'{cells}<td class="diff"><span class="chip {d}">{d}</span></td></tr>')

    return f"""<div class="tab" id="sac{idx}">
<h2>{_esc(term)} {_esc(sac.number)} — {_esc(sac.topic)}</h2>
<div class="kpis">{tiles}</div>
<div class="card"><h3>Score distribution</h3>{_histogram(values)}</div>
<div class="card"><h3>Question performance by cohort quartile</h3>
<div class="mx"><table>{head}{rows}</table></div>{_LEGEND}
<p class="foot">Each cell is the % of that question's marks earned by that group. easy ≥80% · moderate 50-79% · difficult &lt;50%.</p></div>
</div>"""


# --------------------------------------------------------------------------- overview


def _overview_tab(gb: Gradebook, term: str, highlights: str) -> str:
    sac_pct = {sac.sheet: _sac_totals(sac)[1] for sac in gb.sacs}
    all_students = sorted({n for p in sac_pct.values() for n in p})
    all_vals = [v for p in sac_pct.values() for v in p.values()]
    best = max(gb.sacs, key=lambda s: sum(sac_pct[s.sheet].values()) / len(sac_pct[s.sheet]))

    tiles = _tiles([
        ("Students", str(len(all_students)), "", True),
        (f"{term}s", str(len(gb.sacs)), "", False),
        ("Overall average", f"{sum(all_vals)/len(all_vals):.0f}%", f"across all {term.lower()}s", False),
        (f"Strongest {term.lower()}", best.topic[:16], f"{sum(sac_pct[best.sheet].values())/len(sac_pct[best.sheet]):.0f}%", False),
    ])

    bar_rows = ""
    for sac in gb.sacs:
        p = sac_pct[sac.sheet]
        avg = sum(p.values()) / len(p)
        bar_rows += (f'<div class="row" data-tip-title="{_esc(term)} {_esc(sac.number)} — {_esc(sac.topic)}" '
                     f'data-tip="Cohort average {avg:.0f}% · {len(p)} students">'
                     f'<div class="name">{_esc(term)} {_esc(sac.number)}: {_esc(sac.topic)}</div>'
                     f'<div class="track"><div class="fill h{_heat_bin(avg)}" style="width:{avg:.1f}%"></div></div>'
                     f'<div class="val">{avg:.0f}%</div></div>')

    head = ('<tr><th class="rowh">Student</th>'
            + "".join(f'<th>{_esc(term)} {_esc(s.number)}</th>' for s in gb.sacs) + "<th>Overall</th></tr>")
    rows = ""
    for name in all_students:
        vals = [sac_pct[s.sheet].get(name) for s in gb.sacs]
        present = [v for v in vals if v is not None]
        overall = sum(present) / len(present) if present else None
        cells = "".join(
            _hcell(v, f"{name} · {term} {s.number}", "" if v is None else f"{v:.0f}% — {s.topic}")
            for s, v in zip(gb.sacs, vals)
        )
        ov = _hcell(overall, f"{name} · overall", "" if overall is None else f"{overall:.0f}% across {term.lower()}s")
        rows += f'<tr><th class="rowh">{_esc(name)}</th>{cells}{ov}</tr>'

    return f"""<div class="tab active" id="overview">
<div class="kpis">{tiles}</div>
{highlights}
<div class="card"><h3>Cohort average by {_esc(term.lower())}</h3><div class="bars">{bar_rows}</div></div>
<div class="card"><h3>Every student across every {_esc(term.lower())}</h3>
<div class="mx"><table>{head}{rows}</table></div>{_LEGEND}
<p class="foot">Scaled to % of each {_esc(term.lower())}'s marks. Names for the owning teacher's local view only.</p></div>
</div>"""


# --------------------------------------------------------------------------- classes


def _classes_tab(gb: Gradebook, term: str) -> str:
    cls = classes(gb)
    if not cls:
        return ""
    head = ('<tr><th class="rowh">Class</th>'
            + "".join(f'<th>{_esc(term)} {_esc(s.number)}</th>' for s in gb.sacs)
            + "<th>Overall</th><th>Students</th></tr>")
    rows = ""
    for c in cls:
        cells = ""
        overall_vals = []
        n = 0
        for s in gb.sacs:
            _, pct = _sac_totals(s)
            members = [st.name for st in s.students if st.class_group == c]
            n = max(n, len(members))
            vals = [pct[m] for m in members if m in pct]
            if vals:
                avg = sum(vals) / len(vals)
                overall_vals.append(avg)
                cells += _hcell(avg, f"{c} · {term} {s.number}", f"{avg:.0f}% average · {len(vals)} students")
            else:
                cells += '<td class="na">—</td>'
        ov = sum(overall_vals) / len(overall_vals) if overall_vals else None
        rows += (f'<tr><th class="rowh">{_esc(c)}</th>{cells}'
                 + _hcell(ov, f"{c} · overall", "" if ov is None else f"{ov:.0f}% across {term.lower()}s")
                 + f'<td style="background:none;color:var(--ink-2)">{n}</td></tr>')

    source = "are illustrative (assigned for the demo)" if gb.mock_classes else "come from the workbook"
    return f"""<div class="tab" id="classes">
<h2>Class-by-class comparison</h2>
<div class="card"><div class="mx"><table>{head}{rows}</table></div>{_LEGEND}
<p class="foot">Average % per class per {_esc(term.lower())}. Class groups {source}.</p></div>

<div class="card">
<h3>My class — question-level analysis</h3>
<p class="sub">Pick your class to see how it performed on each question, against the whole cohort. Questions
where your class is below the cohort are flagged.</p>
<select class="picker" id="clsq-pick" onchange="renderClassQ()"></select>
<div id="clsq-body"></div>
</div>
</div>"""


# --------------------------------------------------------------------------- student spotlight


def _spotlight_payload(gb: Gradebook, skills: list[SkillsAttainment] | None) -> dict:
    sac_pct = {sac.sheet: _sac_totals(sac)[1] for sac in gb.sacs}
    cohort_avg = {sac.sheet: (sum(sac_pct[sac.sheet].values()) / len(sac_pct[sac.sheet])) for sac in gb.sacs}
    # per-student area attainment from skills
    area_by_student: dict[str, list] = {}
    if skills:
        for sk in skills:
            for (name, area), (aw, av) in sk.per_student_area.items():
                if av:
                    area_by_student.setdefault(name, []).append({"area": area, "pct": round(100 * aw / av)})

    names = sorted({st.name for sac in gb.sacs for st in sac.students})
    by_student = {}
    for name in names:
        sacs = []
        klass = ""
        overall_vals = []
        for sac in gb.sacs:
            st = next((s for s in sac.students if s.name == name), None)
            if st is None:
                continue
            klass = klass or st.class_group
            pct = sac_pct[sac.sheet].get(name)
            if pct is not None:
                overall_vals.append(pct)
            sacs.append({
                "number": sac.number, "topic": sac.topic,
                "pct": None if pct is None else round(pct),
                "cohort": round(cohort_avg[sac.sheet]),
                "questions": [{"id": q.id, "mark": st.marks.get(q.id), "max": q.max_marks} for q in sac.questions],
            })
        by_student[name] = {
            "class": klass,
            "overall": round(sum(overall_vals) / len(overall_vals)) if overall_vals else None,
            "sacs": sacs,
            "areas": sorted(area_by_student.get(name, []), key=lambda a: a["pct"]),
        }
    return {"names": names, "byStudent": by_student}


_SPOT_JS = """
function heatBin(p){return Math.min(6,Math.floor(p/100*7))}
function hcell(p,title){if(p===null||p===undefined)return '<td class="na">—</td>';
  return '<td class="h'+heatBin(p)+'" data-tip-title="'+title+'">'+Math.round(p)+'</td>'}
function renderSpot(){
  const name=document.getElementById('spot-pick').value;
  const d=SPOT.byStudent[name];const el=document.getElementById('spot-body');
  if(!d){el.innerHTML='';return}
  let h='<div class="spot-head"><div class="big">'+(d.overall==null?'—':d.overall+'%')+'</div>'+
    '<div class="meta"><b>'+name+'</b>'+(d.class?' · '+d.class:'')+' · overall across '+d.sacs.length+' '+TERM.toLowerCase()+'(s)</div></div>';
  h+='<div class="card"><h3>Result on each '+TERM.toLowerCase()+' vs cohort average</h3><div class="bars">';
  d.sacs.forEach(s=>{const p=s.pct==null?0:s.pct;
    h+='<div class="row" data-tip-title="'+TERM+' '+s.number+' — '+s.topic+'" data-tip="'+(s.pct==null?'not sat':s.pct+'% vs cohort '+s.cohort+'%')+'">'+
      '<div class="name">'+TERM+' '+s.number+': '+s.topic+'</div>'+
      '<div class="track"><div class="fill h'+heatBin(p)+'" style="width:'+p+'%"></div></div>'+
      '<div class="val">'+(s.pct==null?'—':s.pct+'%')+'<span style="color:var(--muted)"> / '+s.cohort+'</span></div></div>';});
  h+='</div><p class="foot">Green→red = this student\\'s %. The grey number is the cohort average.</p></div>';
  d.sacs.forEach(s=>{
    let head='<tr><th class="rowh">'+TERM+' '+s.number+'</th>';let row='<tr><th class="rowh">% of marks</th>';
    s.questions.forEach(q=>{head+='<th>'+q.id+'</th>';
      const p=(q.mark==null||!q.max)?null:100*q.mark/q.max;
      row+=hcell(p,name+' · '+q.id+' ('+(q.mark==null?'—':q.mark)+'/'+q.max+')');});
    head+='</tr>';row+='</tr>';
    h+='<div class="card"><h3>'+s.topic+' — question by question</h3><div class="mx"><table>'+head+row+'</table></div></div>';});
  // study-design areas
  if(d.areas && d.areas.length){
    h+='<div class="card"><h3>Study-design areas — strengths &amp; growth</h3><div class="bars">';
    d.areas.forEach(a=>{h+='<div class="row" data-tip-title="'+a.area+'" data-tip="'+a.pct+'% of marks in this area">'+
      '<div class="name">'+a.area.replace(/.*·/,'').trim()+'</div>'+
      '<div class="track"><div class="fill h'+heatBin(a.pct)+'" style="width:'+a.pct+'%"></div></div>'+
      '<div class="val">'+a.pct+'%</div></div>';});
    h+='</div><p class="foot">Sorted weakest→strongest — the top rows are where to focus support.</p></div>';}
  el.innerHTML=h;
}
"""


def _spotlight_tab(gb: Gradebook, default_name: str, term: str) -> str:
    return f"""<div class="tab" id="student">
<h2>Student spotlight</h2>
<p class="sub">Pick a student to see how they went on every {_esc(term.lower())}, question by question, and by study-design area.</p>
<select class="picker" id="spot-pick" onchange="renderSpot()"></select>
<div id="spot-body"></div>
</div>"""


# --------------------------------------------------------------------------- class question analysis (JS)

_CLASSQ_JS = """
function renderClassQ(){
  const c=document.getElementById('clsq-pick').value;const el=document.getElementById('clsq-body');
  const cd=CLASSQ.byClass[c];if(!cd){el.innerHTML='';return}
  let h='';
  CLASSQ.assessments.forEach(a=>{
    let rows='';let flagged=0;
    a.questions.forEach(q=>{
      const cp=cd[a.number]?cd[a.number][q.id]:null;
      const delta=(cp==null||q.cohort==null)?null:cp-q.cohort;
      const flag=(delta!=null&&delta<=-10);if(flag)flagged++;
      const concept=[q.area,(q.codes||[]).join(', ')].filter(Boolean).join(' · ');
      rows+='<tr'+(flag?' class="flag"':'')+'>'+
        '<td><b>'+q.id+'</b></td>'+
        hcell(cp,c+' · '+q.id)+
        '<td class="num" style="color:var(--muted)">'+(q.cohort==null?'—':q.cohort)+'</td>'+
        '<td class="num '+(delta!=null&&delta<0?'neg':'pos')+'">'+(delta==null?'—':(delta>0?'+':'')+delta)+'</td>'+
        '<td class="concept-cell">'+(concept||'<span class="muted">—</span>')+'</td></tr>';
    });
    h+='<div class="card"><h3>'+a.topic+'</h3>'+
      '<p class="sub" style="margin:0 0 10px">'+(flagged?('<b>'+flagged+'</b> question(s) where '+c+' is 10+ points below the cohort — worth reviewing.'):(c+' is at or above the cohort on every question here.'))+'</p>'+
      '<div class="mx"><table class="clsq"><tr><th class="rowh">Q</th><th>'+c+'</th><th>Cohort</th><th>Δ</th><th>Concept / code</th></tr>'+rows+'</table></div></div>';
  });
  el.innerHTML=h;
}
"""


# --------------------------------------------------------------------------- skills


def _skills_tab(skills: list[SkillsAttainment], pack_name: str, term: str) -> str:
    blocks = ""
    for sk in skills:
        areas = sorted(sk.cohort_area, key=lambda a: _pct(*sk.cohort_area[a]) or 0)
        if not areas:
            continue
        head = ('<tr><th class="rowh">Student</th>'
                + "".join(f'<th data-tip-title="{_esc(a)}" data-tip="{_esc(", ".join(sk.area_outcomes.get(a, [])))}">{_esc(_short_area(a))}</th>' for a in areas)
                + "</tr>")
        cohort = '<tr class="cohort"><th class="rowh">Cohort</th>' + "".join(
            _hcell(_pct(*sk.cohort_area[a]), f"Cohort · {a}", "") for a in areas) + "</tr>"
        rows = "".join(
            f'<tr><th class="rowh">{_esc(n)}</th>'
            + "".join(_hcell(_pct(*sk.per_student_area.get((n, a), [0.0, 0.0])), f"{n} · {a}", "") for a in areas)
            + "</tr>"
            for n in sk.students
        )
        maps = "".join(
            f'<tr><td>{_esc(m.question_id)}</td><td class="num">{m.max_marks:g}</td>'
            f"<td>{_esc(', '.join(m.codes)) or '—'}</td>"
            f'<td><span class="chip src-{m.source}">{m.source}</span></td></tr>'
            for m in sk.question_maps
        )
        blocks += (f'<div class="card"><h3>{_esc(term)} {_esc(sk.sac_number)} — {_esc(sk.sac_topic)}: attainment by study-design area</h3>'
                   f'<div class="mx"><table>{head}{cohort}{rows}</table></div>{_LEGEND}'
                   f'<details><summary>Question → study-design mapping</summary>'
                   f'<table class="plain"><tr><th>Question</th><th>Marks</th><th>Code(s)</th><th>Source</th></tr>{maps}</table></details></div>')
    caveat = (f'<p class="sub">Mapped against {_esc(pack_name)} — representative codes, confirm against the '
              "official study design/curriculum.</p>")
    return f'<div class="tab" id="skills"><h2>Skills &amp; content by student</h2>{caveat}{blocks}</div>'


# --------------------------------------------------------------------------- top level


def render_gradebook(gb: Gradebook, skills: list[SkillsAttainment] | None = None,
                     pack_name: str = "", term: str = "SAC") -> str:
    highlights = _highlights_card(gb, skills, term)
    tabs = [("overview", "Overview")]
    bodies = [_overview_tab(gb, term, highlights)]
    for i, sac in enumerate(gb.sacs):
        tabs.append((f"sac{i}", f"{term} {sac.number}"))
        bodies.append(_sac_tab(sac, i, term))
    has_classes = bool(classes(gb))
    if has_classes:
        tabs.append(("classes", "Classes"))
        bodies.append(_classes_tab(gb, term))
    payload = _spotlight_payload(gb, skills)
    default_name = payload["names"][0] if payload["names"] else ""
    tabs.append(("student", "Student"))
    bodies.append(_spotlight_tab(gb, default_name, term))
    if skills:
        tabs.append(("skills", "Skills & content"))
        bodies.append(_skills_tab(skills, pack_name, term))

    def _button(tid: str, label: str) -> str:
        active = ' class="active"' if tid == "overview" else ""
        return f'<button data-t="{tid}"{active} onclick="markTab(&#39;{tid}&#39;)">{_esc(label)}</button>'

    tab_buttons = "".join(_button(t, l) for t, l in tabs)
    spot_json = json.dumps(payload)
    classq_json = json.dumps(_classq_payload(gb, skills) if has_classes else {"classes": []})
    default_class = json.dumps(classes(gb)[0] if has_classes else "")

    return f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{_esc(term)} dashboard — {_esc(gb.source)}</title>
<style>{_CSS}{_heat_css()}</style></head>
<body><div class="wrap">
<h1>{_esc(term)} results dashboard</h1>
<p class="sub">{_esc(gb.source)} · {len(gb.sacs)} {_esc(term.lower())}s · single-file dashboard — no dev tools, works offline</p>
<div class="tabs">{tab_buttons}</div>
{''.join(bodies)}
<p class="foot">Generated by Markable · single-file dashboard — safe to email or archive ·
student names are for the owning teacher's local view and never leave this file</p>
</div>
<div id="tip"></div>
<script>const SPOT={spot_json};const CLASSQ={classq_json};const TERM={json.dumps(term)};
{_JS}
{_SPOT_JS}
{_CLASSQ_JS}
(function(){{const sel=document.getElementById('spot-pick');
SPOT.names.forEach(n=>{{const o=document.createElement('option');o.value=n;o.textContent=n;sel.appendChild(o)}});
if(SPOT.names.length){{sel.value={json.dumps(default_name)};renderSpot();}}
const cq=document.getElementById('clsq-pick');
if(cq&&CLASSQ.classes.length){{CLASSQ.classes.forEach(c=>{{const o=document.createElement('option');o.value=c;o.textContent=c;cq.appendChild(o)}});
cq.value={default_class};renderClassQ();}}}})();
</script>
</body></html>"""
