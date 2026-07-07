"""`analyse` — map an uploaded assessment against a curriculum (proof of concept).

A teacher points Markable at a draft (or an already-ingested package) and gets
a per-item mapping table:

    Test item · Marks · Curriculum strand / concept area · VCAA/ACARA code ·
    Cognitive level · Specific skill / data target

Science-first, but nothing science-specific lives in code — the strands, codes
and concept areas all come from the curriculum pack (brief 9.5).

Offline proof-of-concept heuristics (deterministic, no API key):
- **Code proposals** reuse the keyword-overlap scorer from `curriculum.py`;
  each row carries a confidence and the runner-up so the teacher can judge.
- **Cognitive level** is Bloom's, classified from the stem's command verbs with
  a question-type fallback (brief 9.2 says pick one taxonomy and stay
  consistent — Bloom's it is).

The Claude-assisted version (better proposals, richer skill statements) slots
in behind the same row structure later; teacher review remains the contract.
"""

from __future__ import annotations

import csv
import html as html_mod
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from .curriculum import propose_tags
from .ingest import ingest_file, load_assessment
from .models import Assessment, CurriculumPack, Question, QuestionType

# Bloom's levels, checked highest-first so "evaluate and describe" → Evaluate.
_BLOOM_VERBS: list[tuple[str, tuple[str, ...]]] = [
    ("Create", ("design", "construct a model", "propose", "formulate", "devise", "plan an investigation")),
    ("Evaluate", ("evaluate", "justify", "assess", "critique", "argue", "recommend", "discuss the merit")),
    ("Analyse", ("analyse", "analyze", "compare", "contrast", "differentiate", "examine", "interpret the data", "what pattern")),
    ("Apply", ("calculate", "solve", "apply", "use the formula", "determine the", "predict", "demonstrate", "show your working", "draw", "label")),
    ("Understand", ("explain", "describe", "outline", "summarise", "summarize", "classify", "give an example", "why")),
    ("Remember", ("state", "name", "list", "recall", "identify", "define", "what is", "which", "select")),
]

_TYPE_FALLBACK = {
    QuestionType.mcq: "Remember",
    QuestionType.short_answer: "Understand",
    QuestionType.numerical: "Apply",
    QuestionType.extended: "Analyse",
    QuestionType.diagram: "Apply",
}

_SKILL_VERB = {
    "Remember": "Recall",
    "Understand": "Explain",
    "Apply": "Apply",
    "Analyse": "Analyse",
    "Evaluate": "Evaluate",
    "Create": "Construct",
}


def cognitive_level(question: Question) -> str:
    stem = question.stem.lower()

    def hit(verb: str) -> bool:
        # Word-boundary match so "designs" (noun) doesn't trigger "design" (verb);
        # multi-word cues match as phrases.
        return re.search(rf"\b{re.escape(verb)}\b", stem) is not None

    for level, verbs in _BLOOM_VERBS:
        if any(hit(v) for v in verbs):
            return level
    return _TYPE_FALLBACK[question.type]


def _skill_statement(question: Question, level: str) -> str:
    """One-line 'specific skill / data target', e.g.
    'Recall the formula for average velocity (v = Δs/Δt)'."""
    first = re.split(r"(?<=[.?!])\s+", question.stem.strip())[0].rstrip(".?!")
    if not first:
        return f"{_SKILL_VERB[level]} — see question stem"
    # Reframe the stem's command as the skill being exercised.
    lowered = first[0].lower() + first[1:]
    return f"{_SKILL_VERB[level]}: {lowered}"


@dataclass
class AnalysisRow:
    question_id: str
    marks: int
    qtype: str
    concept_area: str  # "Science Understanding (Physical sciences: Motion)"
    code: Optional[str]
    confidence: float  # 0-1ish heuristic score, for teacher judgement
    alternative: Optional[str]
    cognitive_level: str
    skill: str


def analyse_assessment(assessment: Assessment, pack: CurriculumPack) -> list[AnalysisRow]:
    outcomes = {o.code: o for o in pack.outcomes}
    dim_names = {d.id: (d.name or d.id) for d in pack.dimensions}
    rows = []
    for q in assessment.questions:
        # A teacher-confirmed tag (from `markable tag`) always beats a proposal.
        confirmed = [c for c in q.outcome_codes if c in outcomes]
        proposals = propose_tags(q, pack, top_n=2)
        if confirmed:
            code, conf, alt = confirmed[0], 1.0, (confirmed[1] if len(confirmed) > 1 else None)
        elif proposals:
            code = proposals[0].code
            conf = min(0.95, proposals[0].score)
            alt = proposals[1].code if len(proposals) > 1 else None
        else:
            code, conf, alt = None, 0.0, None

        if code:
            o = outcomes[code]
            dim = dim_names.get(o.dimension, o.dimension)
            concept = f"{dim} ({o.strand}" + (f": {o.topic})" if o.topic else ")")
        else:
            concept = "— no confident match"

        level = cognitive_level(q)
        rows.append(
            AnalysisRow(
                question_id=q.id,
                marks=q.marks,
                qtype=q.type.value,
                concept_area=concept,
                code=code,
                confidence=round(conf, 2),
                alternative=alt,
                cognitive_level=level,
                skill=_skill_statement(q, level),
            )
        )
    return rows


def run_analyse(source: Path, pack: CurriculumPack, out_dir: Optional[Path] = None) -> dict:
    """Analyse a draft file or an existing package directory."""
    if source.is_dir():
        assessment = load_assessment(source / "assessment.yaml")
        out_dir = out_dir or source
    else:
        assessment = ingest_file(source, assume_yes=True)
        out_dir = out_dir or source.parent
    out_dir.mkdir(parents=True, exist_ok=True)

    rows = analyse_assessment(assessment, pack)

    csv_path = out_dir / "test_analysis.csv"
    with csv_path.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["test_item", "marks", "type", "curriculum_strand_concept_area",
                    "code", "confidence", "alternative_code", "cognitive_level",
                    "specific_skill"])
        for r in rows:
            w.writerow([r.question_id, r.marks, r.qtype, r.concept_area, r.code or "",
                        r.confidence, r.alternative or "", r.cognitive_level, r.skill])

    html_path = out_dir / "test_analysis.html"
    html_path.write_text(render_analysis(assessment, pack, rows), encoding="utf-8")

    return {
        "rows": rows,
        "mapped": sum(1 for r in rows if r.code),
        "csv": csv_path,
        "html": html_path,
    }


# ---------------------------------------------------------------------------
# Single-file HTML (clean UI, electric-green accents, no libraries/network)
# ---------------------------------------------------------------------------

_ACCENT_LIGHT = "#00a344"  # validated electric-green step for the light surface
_ACCENT_DARK = "#12d95f"  # brighter step selected for the dark surface

_ANALYSIS_CSS = f"""
:root{{
  --surface:#fcfcfb; --page:#f9f9f7; --ink:#0b0b0b; --ink-2:#52514e;
  --muted:#898781; --grid:#e1e0d9; --baseline:#c3c2b7;
  --border:rgba(11,11,11,.10); --accent:{_ACCENT_LIGHT};
  --accent-wash:rgba(0,163,68,.09); --tip-bg:#0b0b0b; --tip-ink:#fff;
}}
@media (prefers-color-scheme: dark){{
  :root{{
    --surface:#1a1a19; --page:#0d0d0d; --ink:#fff; --ink-2:#c3c2b7;
    --muted:#898781; --grid:#2c2c2a; --baseline:#383835;
    --border:rgba(255,255,255,.10); --accent:{_ACCENT_DARK};
    --accent-wash:rgba(18,217,95,.10); --tip-bg:#f4f4f2; --tip-ink:#0b0b0b;
  }}
}}
*{{box-sizing:border-box}}
body{{margin:0;background:var(--page);color:var(--ink);
  font-family:system-ui,-apple-system,"Segoe UI",sans-serif;font-size:14px;line-height:1.5}}
.wrap{{max-width:1100px;margin:0 auto;padding:28px 20px 64px}}
h1{{font-size:21px;margin:0 0 2px}}
.sub{{color:var(--ink-2);margin:0 0 18px}}
.rule{{height:3px;width:64px;background:var(--accent);border-radius:2px;margin:0 0 22px}}
.card{{background:var(--surface);border:1px solid var(--border);border-radius:10px;
  padding:18px 20px;margin-bottom:18px;overflow-x:auto}}
table{{border-collapse:collapse;width:100%;min-width:840px}}
th{{color:var(--ink-2);font-weight:500;font-size:12.5px;text-align:left;
  border-bottom:1px solid var(--baseline);padding:8px 12px 8px 0;white-space:nowrap}}
td{{border-bottom:1px solid var(--grid);padding:9px 12px 9px 0;vertical-align:top}}
tr:hover td{{background:var(--accent-wash)}}
td.num{{font-variant-numeric:tabular-nums}}
.code{{font-weight:600;white-space:nowrap}}
.code .alt{{display:block;font-weight:400;color:var(--muted);font-size:12px}}
.chip{{display:inline-block;border-radius:99px;padding:1px 10px;font-size:12px;
  border:1px solid var(--border);color:var(--ink-2);white-space:nowrap}}
.chip.hi{{border-color:var(--accent);color:var(--ink)}}
.conf{{display:inline-block;width:44px;height:6px;border-radius:3px;
  background:var(--grid);vertical-align:middle;margin-left:6px}}
.conf i{{display:block;height:6px;border-radius:3px;background:var(--accent)}}
.note{{color:var(--muted);font-size:12.5px}}
.caveat{{border-left:3px solid var(--accent);padding:8px 12px;background:var(--accent-wash);
  border-radius:0 8px 8px 0;font-size:13px;color:var(--ink-2);margin-bottom:18px}}
#tip{{position:fixed;display:none;max-width:320px;background:var(--tip-bg);color:var(--tip-ink);
  padding:9px 12px;border-radius:8px;font-size:13.5px;line-height:1.4;z-index:10;
  pointer-events:none;box-shadow:0 4px 14px rgba(0,0,0,.25)}}
#tip b{{display:block;margin-bottom:2px}}
.foot{{color:var(--muted);font-size:12px;margin-top:26px}}
"""

_TIP_JS_MIN = """
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


def render_analysis(assessment: Assessment, pack: CurriculumPack, rows: list[AnalysisRow]) -> str:
    esc = html_mod.escape
    outcomes = {o.code: o for o in pack.outcomes}

    def row_html(r: AnalysisRow) -> str:
        if r.code:
            desc = outcomes[r.code].description
            code_cell = (
                f'<span class="code" data-tip-title="{esc(r.code)}" data-tip="{esc(desc)}">{esc(r.code)}'
                f'<span class="conf" data-tip-title="Match confidence" '
                f'data-tip="Offline keyword match — confirm or edit with `markable tag`">'
                f'<i style="width:{max(8, r.confidence * 100):.0f}%"></i></span>'
                + (f'<span class="alt">alt: {esc(r.alternative)}</span>' if r.alternative else "")
                + "</span>"
            )
        else:
            code_cell = '<span class="note">no confident match — tag manually</span>'
        chip_cls = "chip hi" if r.cognitive_level in ("Analyse", "Evaluate", "Create") else "chip"
        return (
            f"<tr><td><strong>{esc(r.question_id)}</strong><br>"
            f'<span class="note">{esc(r.qtype)}</span></td>'
            f'<td class="num">{r.marks}</td>'
            f"<td>{esc(r.concept_area)}</td>"
            f"<td>{code_cell}</td>"
            f'<td><span class="{chip_cls}">{esc(r.cognitive_level)}</span></td>'
            f"<td>{esc(r.skill)}</td></tr>"
        )

    mapped = sum(1 for r in rows if r.code)
    total_marks = sum(r.marks for r in rows)
    bloom_counts: dict[str, int] = {}
    for r in rows:
        bloom_counts[r.cognitive_level] = bloom_counts.get(r.cognitive_level, 0) + 1
    bloom_line = " · ".join(f"{k} ×{v}" for k, v in bloom_counts.items())

    return f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Test analysis — {esc(assessment.test_id)}</title>
<style>{_ANALYSIS_CSS}</style></head>
<body><div class="wrap">
<h1>Test analysis — {esc(assessment.title or assessment.test_id)}</h1>
<p class="sub">{esc(assessment.test_id)} · {len(rows)} items · {total_marks} marks ·
mapped against {esc(pack.curriculum)} v{esc(pack.version)} · cognitive spread: {esc(bloom_line)}</p>
<div class="rule"></div>
<div class="caveat">Proof of concept — codes are proposed by offline keyword matching
and Bloom's verb analysis. Hover a code for the full content description; confirm or
correct with <code>markable tag</code> before official use. Verify pack codes against
the official VCAA/ACARA source.</div>
<div class="card">
<table>
<tr><th>Test item</th><th>Marks</th><th>Curriculum strand / concept area</th>
<th>VCAA / ACARA code</th><th>Cognitive level</th><th>Specific skill / data target</th></tr>
{''.join(row_html(r) for r in rows)}
</table>
</div>
<p class="note">{mapped}/{len(rows)} items mapped automatically. Codes carry a
confidence bar; the runner-up code is shown where the match was close.</p>
<p class="foot">Generated by Markable · single-file analysis — safe to email or archive</p>
</div>
<div id="tip"></div>
<script>{_TIP_JS_MIN}</script>
</body></html>"""
