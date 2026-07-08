"""`markable studio` — the single-file Markable hub / landing page.

One self-contained HTML file (no libraries, no network) that:

- Presents Markable's tools as cards with descriptions + how-to-use instructions,
  over an inline-SVG hero (data-analysis + AI-marking motif).
- Has a left-hand navigation panel that links every sub-tool. Report files that
  Markable generates (dashboard.html, sac_dashboard.html, curriculum_report.html,
  test_analysis.html) open in the main panel via an iframe when they sit beside
  this file.
- Provides two working, **client-side** upload boxes for staff who have no dev
  tools installed:
    1. Results spreadsheet (.xlsx) → an instant multi-SAC dashboard, parsed and
       rendered entirely in the browser (ZIP inflate via the built-in
       DecompressionStream, then a JS port of the gradebook renderer).
    2. A test/assessment (.docx/.md/.txt) → an "AI-marking readiness" analysis:
       Markable detects questions, mark allocations and structure, and reports
       what to fix so the paper can be marked reliably by AI.

The upload logic is deliberately dependency-free: modern browsers ship
`DecompressionStream('deflate-raw')`, which is all that's needed to read the
DEFLATE members inside an .xlsx/.docx ZIP.
"""

from __future__ import annotations

# The electric-green ramps, mirrored from dashboard_html so the in-browser
# renderer matches the CLI output exactly.
from .dashboard_html import _GREEN_DARK, _GREEN_LIGHT
from .standards_html import _BINS as _HEAT

_HERO_SVG = """
<svg viewBox="0 0 480 220" role="img" aria-label="Markable" xmlns="http://www.w3.org/2000/svg">
  <defs>
    <linearGradient id="g" x1="0" y1="1" x2="0" y2="0">
      <stop offset="0" stop-color="#007d34"/><stop offset="1" stop-color="#12d95f"/>
    </linearGradient>
    <linearGradient id="gd" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0" stop-color="#12d95f"/><stop offset="1" stop-color="#00a344"/>
    </linearGradient>
  </defs>
  <!-- data bars -->
  <g>
    <rect x="16"  y="150" width="26" height="54"  rx="4" fill="url(#g)"/>
    <rect x="52"  y="110" width="26" height="94"  rx="4" fill="url(#g)"/>
    <rect x="88"  y="72"  width="26" height="132" rx="4" fill="url(#g)"/>
    <rect x="124" y="128" width="26" height="76"  rx="4" fill="url(#g)"/>
    <rect x="160" y="40"  width="26" height="164" rx="4" fill="url(#g)"/>
    <polyline points="29,150 65,110 101,72 137,128 173,40"
      fill="none" stroke="#0b0b0b" stroke-opacity=".28" stroke-width="2.5"
      stroke-linecap="round" stroke-linejoin="round"/>
    <circle cx="173" cy="40" r="6" fill="#0b0b0b" fill-opacity=".28"/>
  </g>
  <!-- AI marking node graph + tick -->
  <g transform="translate(250,26)" stroke="url(#gd)" stroke-width="2.5" fill="none">
    <line x1="20" y1="40" x2="90" y2="18"/><line x1="20" y1="40" x2="90" y2="70"/>
    <line x1="20" y1="120" x2="90" y2="70"/><line x1="20" y1="120" x2="90" y2="140"/>
    <line x1="90" y1="18" x2="170" y2="80"/><line x1="90" y1="70" x2="170" y2="80"/>
    <line x1="90" y1="140" x2="170" y2="80"/>
  </g>
  <g transform="translate(250,26)" fill="url(#gd)">
    <circle cx="20" cy="40" r="8"/><circle cx="20" cy="120" r="8"/>
    <circle cx="90" cy="18" r="8"/><circle cx="90" cy="70" r="8"/><circle cx="90" cy="140" r="8"/>
    <circle cx="170" cy="80" r="15"/>
  </g>
  <path transform="translate(250,26)" d="M163 80 l5 6 l10 -13" stroke="#ffffff"
    stroke-width="3" fill="none" stroke-linecap="round" stroke-linejoin="round"/>
</svg>
"""

# Tool cards: (icon-emoji, title, blurb, how-to). Ordered along the pipeline.
_TOOLS = [
    ("📝", "Ingest &amp; Build",
     "Turn a messy Word/markdown draft into a scan-friendly, machine-markable paper "
     "with unique question IDs, answer zones, a per-page QR code and a structured "
     "marking key — the prep that makes AI marking reliable.",
     "CLI: <code>markable ingest draft.md</code> then <code>markable build packages/my-test</code>. "
     "Or drop a draft in the <b>AI-marking readiness</b> box below to see what needs fixing first."),
    ("🖨️", "Scan",
     "Read scanned scripts back in any order or orientation: deskews to the page's "
     "registration marks, matches each page by QR, and crops every answer zone.",
     "CLI: <code>markable scan packages/my-test scans/*.pdf --id-map ids.yaml</code>."),
    ("🤖", "Mark",
     "AI marks per question across the whole cohort against your key, returning marks, "
     "evidence and feedback — anything uncertain goes to a human review queue.",
     "CLI: <code>markable mark packages/my-test --batch</code> (needs an API key). "
     "Nothing below the confidence threshold is auto-finalised."),
    ("📊", "Report &amp; Dashboard",
     "Scores, item analysis (facility, discrimination, distractors) and a single-file "
     "dashboard: cohort KPIs, score distribution and a question × quartile matrix.",
     "CLI: <code>markable report packages/my-test --dashboard</code> → <b>dashboard.html</b>, "
     "then open it from the menu on the left."),
    ("🎯", "Curriculum Report",
     "Standards-referenced attainment against a curriculum: a green→red outcome "
     "heatmap per student, strand rollups, misconceptions and a coverage audit.",
     "CLI: <code>markable tag …</code> then <code>markable report … --curriculum vc2-science</code> "
     "→ <b>curriculum_report.html</b>."),
    ("🔎", "Test Analysis",
     "Point Markable at a test and get a per-item map: marks, strand / concept area, "
     "VCAA/ACARA code, cognitive level (Bloom's) and the specific skill each item targets.",
     "CLI: <code>markable analyse draft.md --curriculum vc2-science</code> → <b>test_analysis.html</b>."),
    ("📈", "SAC Gradebook",
     "Already have marks in a spreadsheet? Upload a per-SAC results workbook and get an "
     "instant multi-tab dashboard — overall, per-SAC question analysis, and per-student "
     "skills mapped to the study design.",
     "Use the <b>Results spreadsheet</b> upload box below — it runs entirely in your browser."),
]

# (nav-id, label, kind, target). kind: 'view' (internal), 'file' (iframe sibling).
_REPORTS = [
    ("dashboard", "Assessment dashboard", "dashboard.html"),
    ("sac", "SAC gradebook dashboard", "sac_dashboard.html"),
    ("curriculum", "Curriculum report", "curriculum_report.html"),
    ("analysis", "Test analysis", "test_analysis.html"),
]


def _tool_cards() -> str:
    out = []
    for icon, title, blurb, how in _TOOLS:
        out.append(f"""<div class="tool">
  <div class="tool-icon">{icon}</div>
  <div class="tool-body"><h3>{title}</h3><p>{blurb}</p>
  <p class="how"><span>How</span> {how}</p></div>
</div>""")
    return "".join(out)


def _report_nav() -> str:
    return "".join(
        f'<button class="nav-item" data-view="report" data-file="{target}" '
        f'onclick="openReport(this)">{label}</button>'
        for _id, label, target in _REPORTS
    )


_CSS = """
:root{
  --surface:#fcfcfb; --page:#f4f6f4; --ink:#0b0b0b; --ink-2:#52514e; --muted:#898781;
  --grid:#e1e0d9; --baseline:#c3c2b7; --border:rgba(11,11,11,.10);
  --accent:#00a344; --accent-2:#12d95f; --accent-wash:rgba(0,163,68,.09);
  --nav:#0c1a12; --nav-ink:#e7f4ec; --nav-ink-2:#8fb7a1; --empty:#f0efec;
  --tip-bg:#0b0b0b; --tip-ink:#fff;
}
@media (prefers-color-scheme: dark){
  :root{
    --surface:#1a1a19; --page:#0d0d0d; --ink:#fff; --ink-2:#c3c2b7; --muted:#898781;
    --grid:#2c2c2a; --baseline:#383835; --border:rgba(255,255,255,.10);
    --accent:#12d95f; --accent-2:#5ceb8f; --accent-wash:rgba(18,217,95,.10);
    --nav:#0a140e; --nav-ink:#e7f4ec; --nav-ink-2:#8fb7a1; --empty:#383835;
    --tip-bg:#f4f4f2; --tip-ink:#0b0b0b;
  }
}
*{box-sizing:border-box}
html,body{margin:0;height:100%}
body{background:var(--page);color:var(--ink);
  font-family:system-ui,-apple-system,"Segoe UI",sans-serif;font-size:14px;line-height:1.45}
.app{display:grid;grid-template-columns:248px 1fr;min-height:100vh}
/* left nav */
.nav{background:var(--nav);color:var(--nav-ink);padding:18px 14px;position:sticky;top:0;height:100vh;overflow-y:auto}
.brand{display:flex;align-items:center;gap:9px;font-weight:700;font-size:18px;margin:2px 4px 18px;color:#fff}
.brand .dot{width:22px;height:22px;border-radius:6px;background:linear-gradient(135deg,var(--accent-2),var(--accent));
  display:inline-flex;align-items:center;justify-content:center;color:#04170c;font-size:14px}
.nav h4{color:var(--nav-ink-2);font-size:11px;text-transform:uppercase;letter-spacing:.06em;margin:16px 8px 6px}
.nav-item{display:block;width:100%;text-align:left;appearance:none;background:none;border:0;color:var(--nav-ink);
  font:inherit;font-size:13.5px;padding:8px 10px;border-radius:8px;cursor:pointer}
.nav-item:hover{background:rgba(255,255,255,.06)}
.nav-item.active{background:linear-gradient(135deg,rgba(18,217,95,.22),rgba(0,163,68,.18));font-weight:600}
.nav-foot{color:var(--nav-ink-2);font-size:11px;margin:18px 8px 0;line-height:1.5}
/* main */
.main{padding:0;overflow:hidden}
.view{display:none;padding:26px 30px 60px;max-width:1160px}
.view.active{display:block}
.iframe-wrap{display:none;height:100vh}
.iframe-wrap.active{display:block}
.iframe-wrap iframe{width:100%;height:100%;border:0;background:var(--surface)}
.iframe-missing{display:none;padding:40px;color:var(--ink-2)}
/* hero */
.hero{display:grid;grid-template-columns:1fr 480px;gap:20px;align-items:center;
  background:var(--surface);border:1px solid var(--border);border-radius:16px;padding:28px 30px;margin-bottom:22px}
.hero h1{font-size:30px;margin:0 0 8px;letter-spacing:-.01em}
.hero .tag{display:inline-block;background:var(--accent-wash);color:var(--accent);
  border-radius:99px;padding:3px 12px;font-size:12.5px;font-weight:600;margin-bottom:12px}
.hero p{color:var(--ink-2);margin:0 0 6px;max-width:52ch;font-size:15px}
.hero svg{width:100%;height:auto}
@media(max-width:920px){.hero{grid-template-columns:1fr}.app{grid-template-columns:1fr}
  .nav{position:static;height:auto}}
/* tool cards */
.cards{display:grid;grid-template-columns:repeat(auto-fill,minmax(320px,1fr));gap:14px}
.tool{display:flex;gap:14px;background:var(--surface);border:1px solid var(--border);
  border-radius:12px;padding:16px 18px}
.tool-icon{font-size:24px;line-height:1;flex:0 0 auto}
.tool-body h3{margin:0 0 4px;font-size:15px}
.tool-body p{margin:0 0 6px;color:var(--ink-2);font-size:13.5px}
.tool-body .how{color:var(--muted);font-size:12.5px}
.how span{display:inline-block;background:var(--accent-wash);color:var(--accent);
  border-radius:5px;padding:0 6px;font-weight:600;font-size:11px;margin-right:4px}
code{background:var(--empty);border-radius:5px;padding:.5px 5px;font-size:12px}
h2.section{font-size:17px;margin:26px 0 12px}
/* upload boxes */
.uploads{display:grid;grid-template-columns:1fr 1fr;gap:16px}
@media(max-width:820px){.uploads{grid-template-columns:1fr}}
.drop{background:var(--surface);border:2px dashed var(--baseline);border-radius:14px;
  padding:22px;text-align:center;transition:.12s}
.drop.drag{border-color:var(--accent);background:var(--accent-wash)}
.drop h3{margin:2px 0 4px;font-size:15px}
.drop p{color:var(--ink-2);margin:0 0 14px;font-size:13px}
.drop .big{font-size:26px;margin-bottom:6px}
.btn{appearance:none;border:0;border-radius:9px;background:linear-gradient(135deg,var(--accent-2),var(--accent));
  color:#04170c;font:inherit;font-weight:600;font-size:13.5px;padding:9px 16px;cursor:pointer}
.btn:hover{filter:brightness(1.05)}
.btn.ghost{background:none;border:1px solid var(--border);color:var(--ink)}
.hint{color:var(--muted);font-size:12px;margin-top:10px}
.status{margin-top:12px;font-size:13px;color:var(--ink-2);min-height:1.2em}
.status.err{color:#d03b3b}
/* rendered results reuse dashboard styles */
.result{margin-top:22px;display:none}
.result.active{display:block}
.kpis{display:grid;grid-template-columns:repeat(auto-fit,minmax(132px,1fr));gap:12px;margin:14px 0 18px}
.tile{background:var(--surface);border:1px solid var(--border);border-radius:10px;padding:13px 15px}
.tile .label{color:var(--ink-2);font-size:12px;margin-bottom:4px}
.tile .value{font-weight:600;font-size:24px}.tile .value.hero{font-size:40px;line-height:1.05}
.tile .note{color:var(--muted);font-size:11.5px;margin-top:2px}
.card{background:var(--surface);border:1px solid var(--border);border-radius:10px;padding:18px 20px;margin-bottom:16px}
.card h3{margin:0 0 12px;font-size:15px}
.subtabs{display:flex;flex-wrap:wrap;gap:4px;border-bottom:1px solid var(--border);margin-bottom:16px}
.subtabs button{appearance:none;background:none;border:0;border-bottom:3px solid transparent;color:var(--ink-2);
  font:inherit;font-size:13px;padding:8px 13px;cursor:pointer;border-radius:6px 6px 0 0}
.subtabs button.active{color:var(--ink);border-bottom-color:var(--accent);font-weight:600}
.subtab{display:none}.subtab.active{display:block}
.hist{display:grid;grid-template-columns:repeat(10,1fr);gap:6px;align-items:end;height:130px;
  border-bottom:1px solid var(--baseline);padding:0 2px}
.hist .col{position:relative;background:var(--accent);border-radius:4px 4px 0 0;min-height:2px}
.hist .col .n{position:absolute;top:-17px;width:100%;text-align:center;font-size:11px;color:var(--ink-2)}
.hist-x{display:grid;grid-template-columns:repeat(10,1fr);gap:6px;padding:4px 2px 0;color:var(--muted);font-size:10.5px;text-align:center}
.mx{overflow-x:auto}.mx table{border-collapse:separate;border-spacing:2px}
.mx th{font-weight:500;color:var(--ink-2);font-size:11.5px;padding:2px 6px;text-align:center;white-space:nowrap}
.mx th.rowh{text-align:left;position:sticky;left:0;background:var(--surface)}
.mx td{min-width:44px;height:26px;text-align:center;border-radius:4px;font-size:11.5px;font-variant-numeric:tabular-nums}
.mx td.na{background:var(--empty);color:var(--muted)}
.chip{display:inline-block;border-radius:99px;padding:1px 9px;font-size:11.5px;border:1px solid var(--border);color:var(--ink-2)}
.chip.easy{border-color:var(--accent)}.chip.difficult{border-color:#d03b3b;color:#d03b3b}
.chip.good{border-color:var(--accent)}.chip.warn{border-color:#e79a41;color:#a15c00}
table.plain{border-collapse:collapse;width:100%}
table.plain th{color:var(--ink-2);font-weight:500;font-size:12px;text-align:left;border-bottom:1px solid var(--baseline);padding:6px 10px 6px 0}
table.plain td{border-bottom:1px solid var(--grid);padding:6px 10px 6px 0}
.readiness{display:flex;align-items:center;gap:16px;margin-bottom:14px}
.gauge{--v:0;width:88px;height:88px;border-radius:50%;flex:0 0 auto;
  background:conic-gradient(var(--accent) calc(var(--v)*1%), var(--empty) 0);
  display:flex;align-items:center;justify-content:center}
.gauge span{width:66px;height:66px;border-radius:50%;background:var(--surface);display:flex;
  align-items:center;justify-content:center;font-weight:700;font-size:20px}
.foot{color:var(--muted);font-size:12px;margin-top:22px}
.li-good::before{content:"✓ ";color:var(--accent);font-weight:700}
.li-warn::before{content:"! ";color:#a15c00;font-weight:700}
"""


def _packs_payload() -> dict:
    """Compact {id: {name, areas:[{strand, terms}]}} for the in-browser skills
    auto-mapper, built from the science study-design fixtures so it stays in
    step with the CLI packs."""
    from pathlib import Path

    import yaml

    from .curriculum import _terms

    root = Path(__file__).resolve().parents[2] / "fixtures" / "curricula"
    out: dict = {}
    for pid in ("vce-biology-u34", "vc2-science"):
        pack_file = root / pid / "pack.yaml"
        if not pack_file.exists():
            continue
        data = yaml.safe_load(pack_file.read_text(encoding="utf-8"))
        dim_names = {d["id"]: d.get("name", d["id"]) for d in data.get("dimensions", [])}
        outcomes = []
        for o in data["outcomes"]:
            dim = dim_names.get(o["dimension"], o["dimension"])
            terms = sorted(_terms(" ".join(
                [o.get("topic", ""), o["strand"], *(o.get("elaborations", []))]
            )))
            outcomes.append({
                "area": f"{dim} — {o['strand']}",
                "terms": terms,
            })
        out[pid] = {"name": f"{data['curriculum']} v{data['version']}", "outcomes": outcomes}
    return out


def collect_reports(paths: list) -> dict:
    """Find known report files under the given dirs/files → {filename: html}."""
    from pathlib import Path

    names = {target for _id, _label, target in _REPORTS}
    found: dict[str, str] = {}
    for p in paths:
        p = Path(p)
        if p.is_dir():
            for name in names:
                f = p / name
                if f.exists():
                    found[name] = f.read_text(encoding="utf-8")
        elif p.is_file() and p.name in names:
            found[p.name] = p.read_text(encoding="utf-8")
    return found


def render_studio(embedded: dict | None = None) -> str:
    import json

    ramps = {
        "greenLight": _GREEN_LIGHT,
        "greenDark": _GREEN_DARK,
        "heatLight": [b[0] for b in _HEAT],
        "heatDark": [b[2] for b in _HEAT],
    }
    ramp_js = (
        "const RAMPS=" + json.dumps(ramps) + ";\n"
        + "const PACKS=" + json.dumps(_packs_payload()) + ";\n"
        + "const STUDIO_CSS=" + json.dumps(_CSS) + ";"
    )

    landing = f"""
<div class="view active" id="view-home">
  <div class="hero">
    <div>
      <span class="tag">Assessment · AI marking · Curriculum intelligence</span>
      <h1>Markable</h1>
      <p>Prepare paper assessments for reliable AI marking, then turn the results into
      clear, standards-referenced insight — all as single files that open in any browser,
      with no software to install.</p>
      <p style="margin-top:14px">
        <button class="btn" onclick="document.getElementById('drop-xlsx-input').click()">Upload results → dashboard</button>
        <button class="btn ghost" onclick="show('uploads');document.getElementById('drop-doc-input').click()">Analyse a test</button>
      </p>
    </div>
    {_HERO_SVG}
  </div>

  <h2 class="section">What Markable does</h2>
  <div class="cards">{_tool_cards()}</div>

  <h2 class="section" id="uploads">Upload &amp; go — runs in your browser</h2>
  <div class="uploads">
    <div class="drop" id="drop-xlsx">
      <div class="big">📈</div>
      <h3>Results spreadsheet → dashboard</h3>
      <p>Drop a per-SAC / per-test marks workbook (.xlsx). Markable builds an instant
      dashboard — cohort overview, per-assessment question analysis and every student's trajectory.</p>
      <button class="btn" onclick="document.getElementById('drop-xlsx-input').click()">Choose spreadsheet</button>
      <input id="drop-xlsx-input" type="file" accept=".xlsx" hidden>
      <div class="hint">Nothing is uploaded anywhere — the file is read locally in this page.</div>
      <div class="status" id="xlsx-status"></div>
    </div>

    <div class="drop" id="drop-doc">
      <div class="big">📝</div>
      <h3>Test / assessment → AI-marking readiness</h3>
      <p>Drop a test (.docx, .md or .txt). Markable analyses its structure and reports how
      ready it is for reliable AI marking — and exactly what to fix.</p>
      <button class="btn" onclick="document.getElementById('drop-doc-input').click()">Choose test</button>
      <input id="drop-doc-input" type="file" accept=".docx,.md,.txt,.markdown" hidden>
      <div class="hint">Detects questions, marks and answer structure — locally, in your browser.</div>
      <div class="status" id="doc-status"></div>
    </div>
  </div>

  <div class="result" id="xlsx-result"></div>
  <div class="result" id="doc-result"></div>

  <p class="foot">Markable · every output is a single self-contained file. Reports generated by the
  command-line tool (dashboard.html, curriculum_report.html, …) appear in the left menu when kept
  beside this page.</p>
</div>
"""

    import html as _html

    embedded = embedded or {}

    def _frame(tid: str, label: str, target: str) -> str:
        if target in embedded:
            # Inline the whole report via srcdoc — its own CSS stays isolated in
            # the iframe, so the hub becomes one portable file with no siblings.
            doc = _html.escape(embedded[target], quote=True)
            return (f'<div class="iframe-wrap" id="frame-{tid}">'
                    f'<iframe data-file="{target}" srcdoc="{doc}" title="{label}"></iframe></div>')
        return (f'<div class="iframe-wrap" id="frame-{tid}">'
                f'<iframe data-file="{target}" data-src="{target}" title="{label}"></iframe></div>')

    report_frames = "".join(_frame(tid, label, target) for tid, label, target in _REPORTS)
    nav_foot = (
        "Reports are embedded in this file — everything opens from the menu, nothing else needed."
        if embedded else
        "Report links open files saved beside this page. Generate them with the Markable CLI, "
        "or use the upload boxes above."
    )

    return f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Markable Studio</title>
<style>{_CSS}</style></head>
<body>
<div class="app">
  <nav class="nav">
    <div class="brand"><span class="dot">✓</span> Markable</div>
    <button class="nav-item active" data-view="home" onclick="show('home',this)">🏠 Home &amp; tools</button>
    <h4>Upload</h4>
    <button class="nav-item" onclick="show('home');document.getElementById('drop-xlsx-input').click()">📈 Results → dashboard</button>
    <button class="nav-item" onclick="show('home');document.getElementById('drop-doc-input').click()">📝 Test → AI-marking prep</button>
    <h4>Reports</h4>
    {_report_nav()}
    <div class="nav-foot">{nav_foot}</div>
  </nav>
  <main class="main">
    {landing}
    {report_frames}
    <div class="iframe-wrap" id="frame-missing"><div class="iframe-missing" style="display:block">
      <h2>Not found beside this page</h2>
      <p>This report opens a file (e.g. <code>dashboard.html</code>) saved in the same folder as
      Markable Studio. Generate it with the Markable command-line tool, then keep it next to this
      file and reopen.</p></div></div>
  </main>
</div>
<div id="tip" style="position:fixed;display:none"></div>
<script>{ramp_js}
{_JS}</script>
</body></html>"""


# --- Client-side engine: ZIP inflate, XLSX/DOCX parse, dashboard + readiness ---
_JS = r"""
function $(id){return document.getElementById(id)}
function show(view, btn){
  document.querySelectorAll('.view').forEach(v=>v.classList.toggle('active', v.id==='view-'+view));
  document.querySelectorAll('.iframe-wrap').forEach(f=>f.classList.remove('active'));
  document.querySelectorAll('.nav-item').forEach(b=>b.classList.remove('active'));
  if(btn) btn.classList.add('active');
  else if(view==='home') document.querySelector('.nav-item[data-view=home]').classList.add('active');
}
function openReport(btn){
  document.querySelectorAll('.view').forEach(v=>v.classList.remove('active'));
  document.querySelectorAll('.nav-item').forEach(b=>b.classList.remove('active'));
  btn.classList.add('active');
  const file=btn.dataset.file;
  // pick the matching frame by data-file; embedded frames carry srcdoc already,
  // linked frames lazy-load their sibling file on first open.
  let shown=null;
  document.querySelectorAll('.iframe-wrap iframe').forEach(fr=>{
    if(fr.dataset.file===file){const w=fr.closest('.iframe-wrap');w.classList.add('active');
      if(!fr.getAttribute('srcdoc') && fr.dataset.src && !fr.src) fr.src=fr.dataset.src;
      shown=w;}
  });
  document.querySelectorAll('.iframe-wrap').forEach(w=>{if(w!==shown)w.classList.remove('active')});
}

/* ---------- ZIP (store + deflate-raw) reader, no libraries ---------- */
async function inflateRaw(bytes){
  if(bytes.length===0) return new Uint8Array();
  const ds=new DecompressionStream('deflate-raw');
  const stream=new Blob([bytes]).stream().pipeThrough(ds);
  return new Uint8Array(await new Response(stream).arrayBuffer());
}
async function readZip(buf){
  const dv=new DataView(buf), u8=new Uint8Array(buf);
  // find End Of Central Directory
  let eocd=-1;
  for(let i=u8.length-22;i>=0;i--){if(dv.getUint32(i,true)===0x06054b50){eocd=i;break}}
  if(eocd<0) throw new Error('not a valid .xlsx/.docx (no ZIP directory)');
  let n=dv.getUint16(eocd+10,true), off=dv.getUint32(eocd+16,true);
  const entries={};
  for(let e=0;e<n;e++){
    if(dv.getUint32(off,true)!==0x02014b50) break;
    const method=dv.getUint16(off+10,true);
    const compSize=dv.getUint32(off+20,true);
    const fnLen=dv.getUint16(off+28,true), exLen=dv.getUint16(off+30,true), cmLen=dv.getUint16(off+32,true);
    const lho=dv.getUint32(off+42,true);
    const name=new TextDecoder().decode(u8.subarray(off+46,off+46+fnLen));
    // local header to locate data
    const lfn=dv.getUint16(lho+26,true), lex=dv.getUint16(lho+28,true);
    const start=lho+30+lfn+lex;
    const comp=u8.subarray(start,start+compSize);
    entries[name]={method,comp};
    off+=46+fnLen+exLen+cmLen;
  }
  return {
    async text(name){const en=entries[name];if(!en)return null;
      const raw=en.method===0?en.comp:await inflateRaw(en.comp);
      return new TextDecoder().decode(raw);}
  };
}

/* ---------- XLSX → sheets of 2D cell grids ---------- */
function colToIdx(ref){let s=ref.replace(/[0-9]/g,''),n=0;for(const ch of s)n=n*26+(ch.charCodeAt(0)-64);return n-1}
async function parseXlsx(buf){
  const zip=await readZip(buf);
  const P=new DOMParser();
  const ss=[]; const sst=await zip.text('xl/sharedStrings.xml');
  if(ss!==null && sst){const d=P.parseFromString(sst,'application/xml');
    d.querySelectorAll('si').forEach(si=>{ let t='';si.querySelectorAll('t').forEach(x=>t+=x.textContent);ss.push(t)});}
  const rels=await zip.text('xl/_rels/workbook.xml.rels');
  const relMap={}; if(rels){const d=P.parseFromString(rels,'application/xml');
    d.querySelectorAll('Relationship').forEach(r=>relMap[r.getAttribute('Id')]=r.getAttribute('Target'));}
  const wbx=await zip.text('xl/workbook.xml');
  const sheets=[]; const d=P.parseFromString(wbx,'application/xml');
  d.querySelectorAll('sheets > sheet').forEach(sh=>{
    const rid=sh.getAttribute('r:id')||sh.getAttributeNS('http://schemas.openxmlformats.org/officeDocument/2006/relationships','id');
    let tgt=relMap[rid]||''; if(tgt && !tgt.startsWith('xl/')) tgt='xl/'+tgt.replace(/^\/?/,'');
    sheets.push({name:sh.getAttribute('name'), path:tgt});
  });
  const out=[];
  for(const s of sheets){
    const xml=await zip.text(s.path); if(!xml) continue;
    const sd=P.parseFromString(xml,'application/xml'); const grid={};
    sd.querySelectorAll('sheetData > row').forEach(row=>{
      const r=parseInt(row.getAttribute('r'));
      row.querySelectorAll('c').forEach(c=>{
        const ref=c.getAttribute('r'); const t=c.getAttribute('t');
        let v=null; const vEl=c.querySelector('v'); const isEl=c.querySelector('is');
        if(t==='s' && vEl){v=ss[parseInt(vEl.textContent)]}
        else if(t==='inlineStr'&&isEl){v='';isEl.querySelectorAll('t').forEach(x=>v+=x.textContent)}
        else if(vEl){const num=parseFloat(vEl.textContent);v=isNaN(num)?vEl.textContent:num}
        if(v!==null){(grid[r]=grid[r]||{})[colToIdx(ref)]=v}
      });
    });
    out.push({name:s.name, grid});
  }
  return out;
}

/* ---------- SAC detection (mirrors gradebook.py) ---------- */
function cell(g,r,c){return (g[r]&&g[r][c]!==undefined)?g[r][c]:null}
function detectSac(sheet){
  const g=sheet.grid;
  let h=null;
  for(let r=1;r<=40 && !h;r++) for(let c=0;c<8;c++){
    if(String(cell(g,r,c)).trim().toLowerCase()==='surname'){h=r;break}}
  if(!h) return null;
  const cols={};
  for(let c=0;c<80;c++){const k=String(cell(g,h,c)||'').trim().toLowerCase();
    if(['surname','first name','id','vcaa number'].includes(k))cols[k]=c;}
  if(cols['surname']===undefined) return null;
  const qs=[];
  for(let c=0;c<120;c++){const mm=String(cell(g,h,c)||'').trim().match(/^\/\s*(\d+(?:\.\d+)?)$/);
    if(!mm)continue; let lab=cell(g,h-1,c); lab=(lab===null||lab==='')?String(c):String(lab).trim();
    if(lab.toUpperCase()==='TOTAL')continue; qs.push({id:lab,max:parseFloat(mm[1]),col:c});}
  if(!qs.length) return null;
  const students=[];
  for(let r=h+1;r<200;r++){const sn=cell(g,r,cols['surname']); if(sn===null||sn==='')continue;
    const fn=cell(g,r,cols['first name']!==undefined?cols['first name']:cols['surname']);
    const st={name:(String(sn).trim()+', '+String(fn||'').trim()).replace(/, $/,''), marks:{}};
    let any=false; for(const q of qs){const v=cell(g,r,q.col);
      if(typeof v==='number'){st.marks[q.id]=v;any=true}else if(v!==null&&!isNaN(parseFloat(v))){st.marks[q.id]=parseFloat(v);any=true}}
    if(any)students.push(st);}
  if(!students.length) return null;
  // topic/total from labelled cells near top
  function labelled(label){const t=label.toLowerCase();
    for(let r=1;r<=8;r++)for(let c=0;c<6;c++){const cc=String(cell(g,r,c)||'').trim().toLowerCase().replace(/:$/,'');
      if(cc===t){for(let cc2=c+1;cc2<c+5;cc2++){const v=cell(g,r,cc2);if(v!==null&&v!=='')return String(v).trim()}}}return null}
  const total=parseFloat(labelled('total marks'))||qs.reduce((a,q)=>a+q.max,0);
  return {number:labelled('sac #')||sheet.name, topic:labelled('topic')||sheet.name,
    total, questions:qs, students};
}

/* ---------- render dashboard (port of gradebook_html) ---------- */
function greenBin(p){return Math.min(6,Math.floor(p/100*7))}
function heatBin(p){return Math.min(6,Math.floor(p/100*7))}
function esc(s){return String(s).replace(/[&<>"]/g,m=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[m]))}
function med(a){const s=[...a].sort((x,y)=>x-y),n=s.length;return n?(n%2?s[(n-1)/2]:(s[n/2-1]+s[n/2])/2):0}
function totalFor(sac,st){return sac.questions.reduce((a,q)=>a+(st.marks[q.id]||0),0)}
function rampCss(){
  let s='<style>';
  RAMPS.greenLight.forEach((c,i)=>s+='.mx td.g'+i+'{background:'+c+'}');
  RAMPS.heatLight.forEach((c,i)=>s+='.mx td.h'+i+'{background:'+c+'}');
  s+='@media (prefers-color-scheme:dark){';
  RAMPS.greenDark.forEach((c,i)=>s+='.mx td.g'+i+'{background:'+c+'}');
  RAMPS.heatDark.forEach((c,i)=>s+='.mx td.h'+i+'{background:'+c+'}');
  s+='}</style>'; return s;
}
function tiles(items){return items.map(([l,v,n,hero])=>
  '<div class="tile"><div class="label">'+esc(l)+'</div><div class="value'+(hero?' hero':'')+'">'+esc(v)+'</div>'+
  (n?'<div class="note">'+esc(n)+'</div>':'')+'</div>').join('')}
function histogram(vals){let b=Array(10).fill(0);vals.forEach(v=>b[Math.min(9,Math.floor(v/10))]++);
  const peak=Math.max(...b)||1;
  return '<div class="hist">'+b.map((x,i)=>'<div class="col" style="height:'+Math.max(2,x/peak*100)+'%">'+
    (x?'<span class="n">'+x+'</span>':'')+'</div>').join('')+'</div>'+
    '<div class="hist-x">'+b.map((x,i)=>'<span>'+(i*10)+'</span>').join('')+'</div>'}
function quartSeg(pct){const names=Object.keys(pct).sort((a,b)=>pct[b]-pct[a]),n=names.length,o={};
  names.forEach((nm,i)=>{const q=n?Math.min(4,1+Math.floor(i*4/n)):1;o[nm]=q===1?1:q===4?3:2});return o}

function sacTab(sac,idx){
  const totals={},pct={}; sac.students.forEach(st=>{totals[st.name]=totalFor(sac,st);
    if(sac.total)pct[st.name]=100*totals[st.name]/sac.total});
  const seg=quartSeg(pct), vals=Object.values(pct).sort((a,b)=>a-b);
  const segName={0:'All',1:'Top 25%',2:'Middle 50%',3:'Bottom 25%'};
  const segSets={0:new Set(Object.keys(pct)),1:new Set(),2:new Set(),3:new Set()};
  Object.keys(pct).forEach(nm=>segSets[seg[nm]].add(nm));
  const kt=tiles([['Class average',Math.round(vals.reduce((a,b)=>a+b,0)/vals.length)+'%','of '+sac.total+' marks',true],
    ['Median',Math.round(med(vals))+'%','',false],['Highest',Math.round(Math.max(...vals))+'%','',false],
    ['Lowest',Math.round(Math.min(...vals))+'%','',false],
    ['At/above 70%',vals.filter(v=>v>=70).length,'of '+vals.length,false],
    ['Below 50%',vals.filter(v=>v<50).length,'intervention',false]]);
  function fac(q,set){const m=sac.students.filter(s=>set.has(s.name)).map(s=>s.marks[q.id]||0);
    return (!m.length||!q.max)?null:m.reduce((a,b)=>a+b,0)/(q.max*m.length)}
  function cellHtml(q,s){const f=fac(q,segSets[s]); if(f===null)return '<td class="na">—</td>';
    const p=f*100;return '<td class="g'+greenBin(p)+'">'+Math.round(p)+'</td>'}
  const rows=sac.questions.map(q=>{const f=fac(q,segSets[0])||0,d=f>=.8?'easy':f>=.5?'moderate':'difficult';
    return '<tr><th class="rowh">'+esc(q.id)+'</th>'+[0,1,2,3].map(s=>cellHtml(q,s)).join('')+
      '<td style="background:none"><span class="chip '+d+'">'+d+'</span></td></tr>'}).join('');
  const head='<tr><th class="rowh">Question</th>'+[0,1,2,3].map(s=>'<th>'+segName[s]+'</th>').join('')+'<th>Difficulty</th></tr>';
  return '<div class="subtab" id="st'+idx+'"><div class="kpis">'+kt+'</div>'+
    '<div class="card"><h3>Score distribution</h3>'+histogram(vals)+'</div>'+
    '<div class="card"><h3>Question performance by cohort quartile</h3><div class="mx"><table>'+head+rows+'</table></div>'+
    '<p class="foot">easy ≥80% · moderate 50–79% · difficult &lt;50%</p></div></div>';
}
function overviewTab(sacs){
  const sacPct=sacs.map(sac=>{const p={};sac.students.forEach(st=>{if(sac.total)p[st.name]=100*totalFor(sac,st)/sac.total});return p});
  const students=[...new Set(sacs.flatMap((s,i)=>Object.keys(sacPct[i])))].sort();
  const allVals=sacPct.flatMap(p=>Object.values(p));
  const kt=tiles([['Students',students.length,'',true],['Assessments',sacs.length,'',false],
    ['Overall average',Math.round(allVals.reduce((a,b)=>a+b,0)/allVals.length)+'%','across all',false]]);
  const bars=sacs.map((sac,i)=>{const p=sacPct[i],avg=Object.values(p).reduce((a,b)=>a+b,0)/Object.values(p).length;
    return '<div style="display:grid;grid-template-columns:220px 1fr 48px;gap:10px;align-items:center;padding:5px 0">'+
      '<div style="color:var(--ink-2);font-size:13px;text-align:right;overflow:hidden;text-overflow:ellipsis;white-space:nowrap">'+esc(sac.number)+': '+esc(sac.topic)+'</div>'+
      '<div style="border-left:1px solid var(--baseline);height:16px"><div style="height:16px;background:var(--accent);border-radius:0 4px 4px 0;width:'+avg.toFixed(1)+'%"></div></div>'+
      '<div style="font-variant-numeric:tabular-nums">'+Math.round(avg)+'%</div></div>'}).join('');
  const head='<tr><th class="rowh">Student</th>'+sacs.map(s=>'<th>'+esc(s.number)+'</th>').join('')+'<th>Overall</th></tr>';
  const rows=students.map(nm=>{const vals=sacs.map((s,i)=>sacPct[i][nm]);
    const present=vals.filter(v=>v!==undefined);const ov=present.length?present.reduce((a,b)=>a+b,0)/present.length:null;
    const cells=vals.map(v=>v===undefined?'<td class="na">—</td>':'<td class="h'+heatBin(v)+'">'+Math.round(v)+'</td>').join('');
    return '<tr><th class="rowh">'+esc(nm)+'</th>'+cells+(ov===null?'<td class="na">—</td>':'<td class="h'+heatBin(ov)+'">'+Math.round(ov)+'</td>')+'</tr>'}).join('');
  return '<div class="subtab active" id="st-ov"><div class="kpis">'+kt+'</div>'+
    '<div class="card"><h3>Cohort average by assessment</h3>'+bars+'</div>'+
    '<div class="card"><h3>Every student across every assessment</h3><div class="mx"><table>'+head+rows+'</table></div>'+
    '<p class="foot">Coloured by percentage · red = at risk · green = secure · names shown locally only.</p></div></div>';
}
/* ---- study-design auto-mapping (mirrors studydesign.py, keyword overlap) ---- */
const STOP=new Set(('the a an and or of to in on for with your is are how what which that this its it be by '+
  'using use used their them when each one two give show state describe explain identify draw label should '+
  'answer question marks mark simple').split(' '));
function terms(s){const out=new Set();(String(s).toLowerCase().match(/[a-z]{3,}/g)||[]).forEach(w=>{
  if(STOP.has(w))return;out.add(w.endsWith('s')?w.slice(0,-1):w)});return out}
function autoArea(label,pack){const q=terms(label);let best=null,bestN=0;
  pack.outcomes.forEach(o=>{let n=0;o.terms.forEach(t=>{if(q.has(t.endsWith('s')?t.slice(0,-1):t))n++});
    if(n>bestN){bestN=n;best=o.area}});return bestN>0?best:null}
function skillsTab(sacs,packId){
  const pack=PACKS[packId];
  let blocks='';
  sacs.forEach(sac=>{
    const qArea={},areas=new Set();
    sac.questions.forEach(q=>{const a=autoArea(q.id,pack);if(a){qArea[q.id]=a;areas.add(a)}});
    if(!areas.size)return;
    const areaList=[...areas];
    const per={},coh={};
    sac.students.forEach(st=>{areaList.forEach(a=>{per[st.name+'|'+a]=[0,0]});});
    areaList.forEach(a=>coh[a]=[0,0]);
    sac.students.forEach(st=>{sac.questions.forEach(q=>{const a=qArea[q.id];if(!a)return;
      const aw=st.marks[q.id]||0;per[st.name+'|'+a][0]+=aw;per[st.name+'|'+a][1]+=q.max;
      coh[a][0]+=aw;coh[a][1]+=q.max})});
    const shortA=a=>a.includes('—')?a.split('—')[1].trim():a;
    const head='<tr><th class="rowh">Student</th>'+areaList.map(a=>'<th>'+esc(shortA(a))+'</th>').join('')+'</tr>';
    const pc=(p)=>p[1]?Math.round(100*p[0]/p[1]):null;
    const cell=v=>v===null?'<td class="na">—</td>':'<td class="h'+heatBin(v)+'">'+v+'</td>';
    const cohRow='<tr style="font-weight:600"><th class="rowh">Cohort</th>'+areaList.map(a=>cell(pc(coh[a]))).join('')+'</tr>';
    const rows=sac.students.map(st=>'<tr><th class="rowh">'+esc(st.name)+'</th>'+
      areaList.map(a=>cell(pc(per[st.name+'|'+a]))).join('')+'</tr>').join('');
    const mapped=Object.keys(qArea).length,tot=sac.questions.length;
    blocks+='<div class="card"><h3>'+esc(sac.number)+' — '+esc(sac.topic)+': attainment by study-design area</h3>'+
      '<div class="mx"><table>'+head+cohRow+rows+'</table></div>'+
      '<p class="foot">'+mapped+'/'+tot+' items auto-mapped from their labels. Content items that are just '+
      'numbered (1, 2, 3a) need a teacher map via the CLI — criterion-named items (prac skills) map here directly.</p></div>';
  });
  if(!blocks) blocks='<div class="card"><p>No items could be auto-mapped from their labels for '+
    esc(pack.name)+'. Named criteria (e.g. a prac SAC\'s skill columns) map automatically; '+
    'numbered content questions need a teacher map via <code>markable gradebook --map</code>.</p></div>';
  return '<div class="subtab" id="st-skills"><p class="foot" style="margin-top:0">Mapped against '+esc(pack.name)+
    ' — representative codes, confirm against the official study design.</p>'+blocks+'</div>';
}

let LAST_SACS=null, LAST_TITLE='';
function packOptions(sel){return '<option value="">Study design: none</option>'+
  Object.keys(PACKS).map(id=>'<option value="'+id+'"'+(id===sel?' selected':'')+'>'+esc(PACKS[id].name)+'</option>').join('')}
function renderDashboard(sacs,packId){
  const toolbar='<div style="display:flex;gap:10px;align-items:center;flex-wrap:wrap;margin-bottom:12px">'+
    '<select onchange="reRender(this.value)" style="padding:7px 10px;border-radius:8px;border:1px solid var(--border);background:var(--surface);color:var(--ink);font:inherit">'+
    packOptions(packId)+'</select>'+
    '<button class="btn ghost" onclick="downloadDash()">⬇ Download this dashboard</button></div>';
  const tabs=['<button class="active" onclick="pickSub(this,\'st-ov\')">Overview</button>']
    .concat(sacs.map((s,i)=>'<button onclick="pickSub(this,\'st'+i+'\')">'+esc(s.number)+'</button>'));
  if(packId) tabs.push('<button onclick="pickSub(this,\'st-skills\')">Skills &amp; content</button>');
  let bodies=overviewTab(sacs)+sacs.map((s,i)=>sacTab(s,i)).join('');
  if(packId) bodies+=skillsTab(sacs,packId);
  return rampCss()+toolbar+'<div class="subtabs">'+tabs.join('')+'</div>'+bodies;
}
function reRender(packId){
  if(!LAST_SACS)return;
  $('xlsx-result').innerHTML='<h2 class="section" id="dash-title">Dashboard — '+esc(LAST_TITLE)+'</h2>'+renderDashboard(LAST_SACS,packId);
}
function downloadDash(){
  const content=$('xlsx-result').innerHTML;
  const doc='<!DOCTYPE html><html lang="en"><head><meta charset="utf-8">'+
    '<meta name="viewport" content="width=device-width,initial-scale=1">'+
    '<title>'+esc(LAST_TITLE)+' — Markable dashboard</title><style>'+STUDIO_CSS+
    'body{padding:24px 30px}</style></head><body>'+content+
    '<script>function pickSub(b,id){const r=document;r.querySelectorAll(".subtabs button").forEach(x=>x.classList.toggle("active",x===b));r.querySelectorAll(".subtab").forEach(t=>t.classList.toggle("active",t.id===id))}<\/script>'+
    '</body></html>';
  const blob=new Blob([doc],{type:'text/html'});
  const a=document.createElement('a');a.href=URL.createObjectURL(blob);
  a.download=(LAST_TITLE.replace(/\.[^.]+$/,'')||'markable')+'-dashboard.html';a.click();
  setTimeout(()=>URL.revokeObjectURL(a.href),2000);
}
function pickSub(btn,id){
  const root=btn.closest('.result')||document;
  root.querySelectorAll('.subtabs button').forEach(b=>b.classList.toggle('active',b===btn));
  root.querySelectorAll('.subtab').forEach(t=>t.classList.toggle('active',t.id===id));
}

/* ---------- DOCX / markdown → AI-marking readiness ---------- */
async function docText(name,buf){
  if(/\.(md|markdown|txt)$/i.test(name)) return new TextDecoder().decode(new Uint8Array(buf));
  const zip=await readZip(buf); const xml=await zip.text('word/document.xml'); if(!xml)return '';
  const d=new DOMParser().parseFromString(xml,'application/xml'); let out=[];
  d.querySelectorAll('p').forEach(p=>{let t='';p.querySelectorAll('t').forEach(x=>t+=x.textContent);
    if(t.trim())out.push(t.trim())}); return out.join('\n');
}
function analyseReadiness(text){
  // strip markdown heading hashes and list bullets so "## Q1 …" / "- Q1 …" count
  const lines=text.split(/\n+/).map(l=>l.trim().replace(/^#+\s*/,'').replace(/^[-*]\s+/,'')).filter(Boolean);
  // question detection: lines starting Q1 / 1. / 1) / a) etc.
  const qRe=/^(?:Q\s?\d+|[0-9]{1,2}[.)]|\([0-9]{1,2}\)|[a-h][.)])/i;
  const questions=lines.filter(l=>qRe.test(l));
  // marks: "(2 marks)", "[3 marks]", "/4", or Markable's "[mcq, 2]" / "[extended, 6]"
  const markRe=/(\(|\[)\s*\d+\s*(mark|marks|m)\s*(\)|\])|\/\s?\d+\b|\[[a-z_]+,\s*\d+\s*\]/i;
  const withMarks=questions.filter(l=>markRe.test(l));
  const mcqish=lines.filter(l=>/^[A-D][.)]\s/.test(l)).length;
  const hasIds=questions.filter(l=>/^Q\s?\d+/i.test(l)).length;
  const checks=[
    ['Questions detected', questions.length>0, questions.length+' question-like items found',
      'No clear question markers — number each question (Q1, Q2 …) so every item is uniquely identified.'],
    ['Unique question IDs', hasIds>=Math.max(1,questions.length*0.5),
      hasIds+' items use explicit IDs (Q1, Q2 …)',
      'Few explicit IDs — Markable assigns stable IDs (Q07a) so a cropped answer is self-identifying.'],
    ['Marks allocated', withMarks.length>=Math.max(1,questions.length*0.5),
      withMarks.length+'/'+questions.length+' questions state their marks',
      'Many questions have no mark allocation — add e.g. "(2 marks)" so the key and analysis are complete.'],
    ['Answer space / structure', /answer|working|space|box|lines/i.test(text) || mcqish>0,
      'Response structure present (options / answer prompts)',
      'No explicit answer zones — Markable’s build step adds bordered response boxes, working frames and a separated final-answer cell.'],
    ['Machine-readable key', false, '',
      'A structured marking key (key.yaml) is generated at build time — criteria, accept/reject, rubric bands — the single biggest driver of reliable AI marking.'],
  ];
  const auto=checks.filter(c=>c[1]).length;
  const score=Math.round((auto/ (checks.length-1))*100); // last item is always a build-time step
  return {questions:questions.length, withMarks:withMarks.length, checks, score};
}
function renderReadiness(name,rep){
  const items=rep.checks.map(c=>'<li class="'+(c[1]?'li-good':'li-warn')+'">'+
    '<b>'+esc(c[0])+'</b> — '+esc(c[1]?c[2]:c[3])+'</li>').join('');
  const grade=rep.score>=70?'good':'warn';
  return '<div class="card"><h3>AI-marking readiness — '+esc(name)+'</h3>'+
    '<div class="readiness"><div class="gauge" style="--v:'+rep.score+'"><span>'+rep.score+'%</span></div>'+
    '<div><p style="margin:0 0 6px">Markable found <b>'+rep.questions+'</b> questions, <b>'+rep.withMarks+
    '</b> with marks allocated. <span class="chip '+grade+'">'+(rep.score>=70?'Close — minor prep':'Needs structuring')+'</span></p>'+
    '<p style="margin:0;color:var(--ink-2);font-size:13px">Run <code>markable ingest</code> then <code>markable build</code> to auto-apply the fixes below and produce a scan-ready paper + marking key.</p></div></div>'+
    '<ul style="margin:0;padding-left:2px;list-style:none;line-height:1.9">'+items+'</ul>'+
    '<p class="foot">This readiness check runs locally. The build step (unique IDs, answer zones, QR codes, a structured key) is what makes AI marking reliable and auditable.</p></div>';
}

/* ---------- wiring: drag/drop + file pickers ---------- */
function wireDrop(dropId,inputId,handler){
  const drop=$(dropId),input=$(inputId);
  input.addEventListener('change',e=>{if(e.target.files[0])handler(e.target.files[0])});
  ['dragover','dragenter'].forEach(ev=>drop.addEventListener(ev,e=>{e.preventDefault();drop.classList.add('drag')}));
  ['dragleave','dragend','drop'].forEach(ev=>drop.addEventListener(ev,e=>{e.preventDefault();drop.classList.remove('drag')}));
  drop.addEventListener('drop',e=>{if(e.dataTransfer.files[0])handler(e.dataTransfer.files[0])});
}
wireDrop('drop-xlsx','drop-xlsx-input',async file=>{
  const st=$('xlsx-status');st.className='status';st.textContent='Reading '+file.name+' …';
  try{
    const sheets=await parseXlsx(await file.arrayBuffer());
    const sacs=sheets.map(detectSac).filter(Boolean);
    if(!sacs.length)throw new Error('No results grid found. Expected a sheet with a "Surname" header row and "/N" mark columns.');
    LAST_SACS=sacs; LAST_TITLE=file.name;
    $('xlsx-result').innerHTML='<h2 class="section" id="dash-title">Dashboard — '+esc(file.name)+'</h2>'+renderDashboard(sacs,'');
    $('xlsx-result').classList.add('active');
    st.textContent='✓ '+sacs.length+' assessment(s), '+sacs[0].students.length+' students.';
    $('xlsx-result').scrollIntoView({behavior:'smooth'});
  }catch(err){st.className='status err';st.textContent='Could not read that file: '+err.message}
});
wireDrop('drop-doc','drop-doc-input',async file=>{
  const st=$('doc-status');st.className='status';st.textContent='Analysing '+file.name+' …';
  try{
    const text=await docText(file.name,await file.arrayBuffer());
    if(!text.trim())throw new Error('No readable text found in that document.');
    const rep=analyseReadiness(text);
    $('doc-result').innerHTML='<h2 class="section">Readiness</h2>'+renderReadiness(file.name,rep);
    $('doc-result').classList.add('active');
    st.textContent='✓ Analysed — readiness '+rep.score+'%.';
    $('doc-result').scrollIntoView({behavior:'smooth'});
  }catch(err){st.className='status err';st.textContent='Could not analyse that file: '+err.message}
});
"""
