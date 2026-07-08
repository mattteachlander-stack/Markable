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
      <stop offset="0" stop-color="#123a7a"/><stop offset="1" stop-color="#2f80ed"/>
    </linearGradient>
    <linearGradient id="gd" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0" stop-color="#4b93ff"/><stop offset="1" stop-color="#1e63d0"/>
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

# Tool cards: (icon, title, blurb, how-to, button-label, button-onclick).
# Every card carries a button that jumps straight to the tool that does the job.
_TOOLS = [
    ("📝", "Ingest &amp; Build",
     "Turn a messy Word/markdown draft into a scan-friendly, machine-markable paper "
     "with unique question IDs, answer zones, a per-page QR code and a structured "
     "marking key — the prep that makes AI marking reliable.",
     "CLI: <code>markable ingest draft.md</code> then <code>markable build packages/my-test</code>. "
     "Or drop a draft in the <b>AI-marking readiness</b> box below to see what needs fixing first.",
     "Prep my test", "show('home');scrollToEl('drop-doc');$('drop-doc-input').click()"),
    ("✨", "Assessment Optimiser",
     "Optimise any assessment for AI marking: unique IDs, explicit marks, typed items and "
     "tightened wording — your questions and difficulty preserved, every change logged, "
     "with a before/after readiness score.",
     "Open the <b>Assessment optimiser</b> (left menu, under AI cloud), drop your test in, "
     "and download the optimised version. CLI twin: <code>markable improve draft.docx</code>.",
     "Optimise my assessment", "show('optimise')"),
    ("🖨️", "Scan",
     "Read scanned scripts back in any order or orientation: deskews to the page's "
     "registration marks, matches each page by QR, and crops every answer zone.",
     "CLI: <code>markable scan packages/my-test scans/*.pdf --id-map ids.yaml</code>.",
     "Upload scans → AI marking", "show('aimark')"),
    ("🤖", "Mark",
     "AI marks per question across the whole cohort against your key, returning marks, "
     "evidence and feedback — anything uncertain goes to a human review queue.",
     "CLI: <code>markable mark packages/my-test --batch</code> (needs an API key). "
     "Nothing below the confidence threshold is auto-finalised.",
     "Mark with Claude", "show('aimark')"),
    ("📊", "Report &amp; Dashboard",
     "Scores, item analysis (facility, discrimination, distractors) and a single-file "
     "dashboard: cohort KPIs, score distribution and a question × quartile matrix.",
     "CLI: <code>markable report packages/my-test --dashboard</code> → <b>dashboard.html</b>, "
     "then open it from the menu on the left.",
     "Build a dashboard", "show('home');scrollToEl('drop-xlsx');$('drop-xlsx-input').click()"),
    ("🎯", "Curriculum Report",
     "Standards-referenced attainment against a curriculum: a green→red outcome "
     "heatmap per student, strand rollups, misconceptions and a coverage audit.",
     "CLI: <code>markable tag …</code> then <code>markable report … --curriculum vc2-science</code> "
     "→ <b>curriculum_report.html</b>.",
     "View curriculum report", "openReportByFile('curriculum_report.html')"),
    ("🔎", "Test Analysis",
     "Point Markable at a test and get a per-item map: marks, strand / concept area, "
     "VCAA/ACARA code, cognitive level (Bloom's) and the specific skill each item targets.",
     "CLI: <code>markable analyse draft.md --curriculum vc2-science</code> → <b>test_analysis.html</b>.",
     "View test analysis", "openReportByFile('test_analysis.html')"),
    ("📈", "SAC Gradebook",
     "Already have marks in a spreadsheet? Upload a per-SAC results workbook and get an "
     "instant multi-tab dashboard — overall, per-SAC question analysis, and per-student "
     "skills mapped to the study design.",
     "Use the <b>Results spreadsheet</b> upload box below — it runs entirely in your browser.",
     "Upload my results", "show('home');scrollToEl('drop-xlsx');$('drop-xlsx-input').click()"),
]

# (nav-id, label, kind, target). kind: 'view' (internal), 'file' (iframe sibling).
_REPORTS = [
    ("sacvce", "VCE — SAC results", "vce_sac_dashboard.html"),
    ("sac710", "Years 7–10 — results", "y7-10_dashboard.html"),
    ("dashboard", "Assessment dashboard", "dashboard.html"),
    ("curriculum", "Curriculum report", "curriculum_report.html"),
    ("analysis", "Test analysis", "test_analysis.html"),
]


def _tool_cards() -> str:
    out = []
    for icon, title, blurb, how, btn_label, btn_js in _TOOLS:
        # onclick JS goes through an HTML attribute — escape the quotes it carries.
        js = btn_js.replace('"', "&quot;")
        out.append(f"""<div class="tool">
  <div class="tool-icon">{icon}</div>
  <div class="tool-body"><h3>{title}</h3><p>{blurb}</p>
  <p class="how"><span>How</span> {how}</p>
  <button class="btn tool-go" onclick="{js}">{btn_label} →</button></div>
</div>""")
    return "".join(out)


def _guide_view() -> str:
    """The 'How to use' page — lives inside the hub so the one file explains itself."""
    return """
<div class="view" id="view-guide">
  <h1>How to use Markable</h1>
  <p class="lead">Markable has two ways in. Most staff only need the first.</p>

  <div class="guide-grid">
    <div class="guide-card">
      <div class="gc-icon">🖱️</div>
      <h2>1. No install — just this page</h2>
      <p>Everything here runs in your browser. Nothing is uploaded anywhere; your files are
      read locally on your computer.</p>
      <ol>
        <li><b>See your class results.</b> Go to <i>Home &amp; tools</i> → the
          <b>Results spreadsheet</b> box → <b>Choose spreadsheet</b> and pick your marks
          workbook (.xlsx). An instant dashboard appears: cohort overview, a tab per SAC/test
          with question analysis, and every student's trajectory.</li>
        <li><b>Map to the study design.</b> On that dashboard, pick a study design from the
          dropdown — a <i>Skills &amp; content</i> tab appears showing what each student is
          performing to. Press <b>⬇ Download this dashboard</b> to save it as its own file.</li>
        <li><b>Check a test before marking.</b> Use the <b>Test → AI-marking readiness</b>
          box → drop a test (.docx, .md or .txt). Markable reports how ready it is for
          reliable AI marking and what to fix.</li>
        <li><b>Read the reports.</b> The left menu under <i>Reports</i> opens each finished
          report (dashboards, curriculum report, test analysis) right here.</li>
      </ol>
      <p class="note">Your spreadsheet needs a row with <b>Surname</b> and one column per
      question with a <b>/N</b> mark header (the usual SAC layout). Multiple SACs = multiple
      sheets.</p>
    </div>

    <div class="guide-card">
      <div class="gc-icon">⌨️</div>
      <h2>2. Full pipeline (the tech person)</h2>
      <p>For preparing papers, scanning and AI marking, Markable runs from a command line.
      One-time setup: install <code>uv</code>, then <code>uv sync</code>.</p>
      <ol>
        <li><b>Prepare a paper:</b> <code>markable ingest draft.md</code> →
          <code>markable build packages/my-test</code> (makes a scan-friendly paper + marking key).</li>
        <li><b>After the test:</b> <code>markable scan packages/my-test scans/*.pdf</code> →
          <code>markable mark packages/my-test</code> (AI marks per question; unsure items go
          to a review queue).</li>
        <li><b>Reports:</b> <code>markable report packages/my-test --dashboard</code>,
          <code>… --curriculum vc2-science</code>, or <code>markable analyse draft.md --curriculum vc2-science</code>.</li>
        <li><b>Power BI:</b> <code>markable powerbi results.xlsx -o powerbi_export</code> cleans
          the spreadsheet into ready-to-load tables + a build guide.</li>
        <li><b>Bundle it all:</b> <code>markable studio -o markable.html --embed packages/my-test</code>
          builds this single hub with every report baked in.</li>
      </ol>
      <p class="note">Each report is one self-contained HTML file — safe to email, print, or
      archive. Full commands are on each tool card on the Home page.</p>
    </div>
  </div>

  <h2 class="section">What each report shows</h2>
  <table class="guide-table">
    <tr><th>Report</th><th>Answers</th><th>Made by</th></tr>
    <tr><td><b>Assessment dashboard</b></td><td>How did the class go? Which questions were hard? Top vs bottom quartile per question.</td><td>Upload box, or <code>report --dashboard</code></td></tr>
    <tr><td><b>SAC gradebook dashboard</b></td><td>Every student across every SAC, plus per-SAC question analysis and skills.</td><td>Upload box, or <code>gradebook</code></td></tr>
    <tr><td><b>Curriculum report</b></td><td>Attainment per outcome (green→red), strand rollups, misconceptions, coverage gaps.</td><td><code>report --curriculum</code></td></tr>
    <tr><td><b>Test analysis</b></td><td>Each item → curriculum code, cognitive level, and the specific skill it targets.</td><td><code>analyse</code></td></tr>
  </table>

  <div class="privacy-note">🔒 <b>Privacy:</b> the dashboard and readiness boxes run entirely on
  your device. The <i>AI cloud</i> features (reformat &amp; marking) are opt-in and send your
  files directly to the AI provider you chose — Claude or your workplace's Copilot endpoint —
  using your own key, with no Markable server in between. Codes in the sample curricula are
  representative — verify against the official VCAA/ACARA source before formal reporting.</div>
</div>
"""


def _report_nav() -> str:
    return "".join(
        f'<button class="nav-item" data-view="report" data-file="{target}" '
        f'onclick="openReport(this)">{label}</button>'
        for _id, label, target in _REPORTS
    )


_CSS = """
:root{
  --surface:#ffffff; --page:#f4f6fb; --ink:#0f1729; --ink-2:#48566f; --muted:#8a95a8;
  --grid:#e6eaf2; --baseline:#c7cede; --border:rgba(15,23,41,.10);
  --accent:#1e63d0; --accent-2:#2f80ed; --accent-wash:rgba(30,99,208,.08);
  --nav:#0d1830; --nav-ink:#e9f0fb; --nav-ink-2:#9fb0cc; --empty:#eef1f7;
  --tip-bg:#0f1729; --tip-ink:#fff;
}
@media (prefers-color-scheme: dark){
  :root{
    --surface:#141a26; --page:#0b0f17; --ink:#eaf0fb; --ink-2:#a9b6cc; --muted:#6f7c93;
    --grid:#232c3d; --baseline:#33405a; --border:rgba(255,255,255,.10);
    --accent:#4b93ff; --accent-2:#6aa8ff; --accent-wash:rgba(75,147,255,.12);
    --nav:#0a1220; --nav-ink:#e9f0fb; --nav-ink-2:#9fb0cc; --empty:#232c3d;
    --tip-bg:#eaf0fb; --tip-ink:#0f1729;
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
/* how-to-use guide */
#view-guide h1{font-size:26px;margin:0 0 4px}
#view-guide .lead{color:var(--ink-2);font-size:15px;margin:0 0 20px}
.guide-grid{display:grid;grid-template-columns:1fr 1fr;gap:16px;margin-bottom:8px}
@media(max-width:820px){.guide-grid{grid-template-columns:1fr}}
.guide-card{background:var(--surface);border:1px solid var(--border);border-radius:14px;padding:20px 22px}
.guide-card .gc-icon{font-size:26px;margin-bottom:6px}
.guide-card h2{font-size:16px;margin:0 0 8px}
.guide-card ol{margin:10px 0 8px;padding-left:20px}
.guide-card li{margin-bottom:9px;color:var(--ink);font-size:14px}
.guide-card .note{color:var(--muted);font-size:12.5px;margin:8px 0 0;border-top:1px solid var(--grid);padding-top:8px}
.guide-table{border-collapse:collapse;width:100%;margin-bottom:18px;background:var(--surface);
  border:1px solid var(--border);border-radius:12px;overflow:hidden}
.guide-table th{text-align:left;font-size:12.5px;color:var(--ink-2);background:var(--accent-wash);padding:9px 14px}
.guide-table td{padding:10px 14px;border-top:1px solid var(--grid);font-size:13.5px;vertical-align:top}
.guide-table td:first-child{white-space:nowrap}
.privacy-note{background:var(--accent-wash);border-left:3px solid var(--accent);border-radius:0 10px 10px 0;
  padding:12px 16px;font-size:13.5px;color:var(--ink-2)}
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
.products{display:grid;grid-template-columns:1fr 1fr;gap:16px;margin-bottom:26px}
@media(max-width:820px){.products{grid-template-columns:1fr}}
.product{position:relative;border-radius:16px;padding:22px 24px;color:#fff;overflow:hidden;
  border:1px solid var(--border)}
.product.vce{background:linear-gradient(135deg,#12336e,#1e63d0)}
.product.js{background:linear-gradient(135deg,#0e3a5f,#2f80ed)}
.product .band{display:inline-block;background:rgba(255,255,255,.18);border-radius:99px;
  padding:2px 11px;font-size:12px;font-weight:600;margin-bottom:10px}
.product h2{color:#fff;font-size:20px;margin:0 0 6px}
.product p{color:rgba(255,255,255,.9);margin:0 0 14px;font-size:14px;max-width:44ch}
.product .pbtns{display:flex;gap:8px;flex-wrap:wrap}
.product .pbtn{appearance:none;border:0;border-radius:9px;padding:9px 14px;font:inherit;font-size:13.5px;
  font-weight:600;cursor:pointer;background:#fff;color:#123a7a}
.product .pbtn.ghost{background:rgba(255,255,255,.14);color:#fff;border:1px solid rgba(255,255,255,.35)}
.product .curric{margin-top:12px;font-size:12px;color:rgba(255,255,255,.75)}
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
/* AI marking studio */
.beta-chip{display:inline-block;vertical-align:middle;margin-left:8px;font-size:11px;font-weight:600;
  letter-spacing:.06em;text-transform:uppercase;color:var(--accent);border:1px solid var(--accent);
  border-radius:99px;padding:2px 10px}
.provider-card{margin:14px 0 18px}
.providers{display:grid;grid-template-columns:repeat(auto-fit,minmax(260px,1fr));gap:10px;margin-bottom:12px}
.provider{display:flex;gap:12px;align-items:center;text-align:left;cursor:pointer;font:inherit;
  background:var(--page);border:2px solid var(--border);border-radius:12px;padding:12px 14px;color:var(--ink)}
.provider svg{width:34px;height:34px;flex:0 0 auto;color:var(--muted)}
.provider div{display:flex;flex-direction:column;gap:2px}
.provider span{color:var(--ink-2);font-size:12px}
.provider.on{border-color:var(--accent);background:var(--accent-wash)}
.provider.on svg{color:var(--accent)}
.keyfield{display:flex;gap:8px;align-items:center;flex-wrap:wrap}
.keyfield input{padding:8px 10px;border-radius:8px;border:1px solid var(--border);
  background:var(--page);color:var(--ink);font:inherit;width:260px}
.nav-item.sub{padding-left:26px;font-size:12.5px;opacity:.85}
/* assessment optimiser */
.opt-flow{display:flex;gap:10px;align-items:center;flex-wrap:wrap;margin:16px 0 18px}
.opt-step{background:var(--surface);border:1px solid var(--border);border-radius:99px;
  padding:8px 16px 8px 8px;display:flex;gap:8px;align-items:center;font-size:13px;color:var(--ink-2)}
.opt-n{width:24px;height:24px;border-radius:50%;background:var(--accent);color:#fff;font-weight:700;
  font-size:13px;display:flex;align-items:center;justify-content:center}
.opt-arrow{color:var(--muted)}
.beforeafter{display:flex;gap:26px;align-items:center;flex-wrap:wrap;margin:6px 0 14px}
.beforeafter .ba{display:flex;gap:12px;align-items:center}
.beforeafter .ba .lbl{color:var(--ink-2);font-size:12px;text-transform:uppercase;letter-spacing:.05em}
.ba-arrow{font-size:26px;color:var(--accent)}
.aim-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(240px,1fr));gap:14px}
.aim-step{position:relative}
.aim-step .stepnum{position:absolute;top:10px;left:12px;width:24px;height:24px;border-radius:50%;
  background:var(--accent);color:#fff;font-weight:700;font-size:13px;display:flex;align-items:center;justify-content:center}
.aim-step.ok{border-color:var(--accent);border-style:solid}
.aim-actions{display:flex;gap:10px;flex-wrap:wrap;margin:16px 0}
.tool-go{margin-top:10px;padding:7px 14px;font-size:13px}
.mark-total{font-size:26px;font-weight:700}
.chip.review{border-color:#e79a41;color:#a15c00}
table.marks{border-collapse:collapse;width:100%;font-size:13px}
table.marks th{color:var(--ink-2);font-weight:500;text-align:left;border-bottom:1px solid var(--baseline);padding:6px 8px 6px 0}
table.marks td{border-bottom:1px solid var(--grid);padding:6px 8px 6px 0;vertical-align:top}
table.marks td.num{font-variant-numeric:tabular-nums;white-space:nowrap}
.changes li{margin-bottom:6px}
.spin{display:inline-block;width:14px;height:14px;border:2px solid var(--accent);border-top-color:transparent;
  border-radius:50%;animation:spin .8s linear infinite;vertical-align:-2px;margin-right:6px}
@keyframes spin{to{transform:rotate(360deg)}}
.tab-h{font-size:18px;margin:4px 0 12px}
.muted{color:var(--muted)}
.picker{padding:7px 10px;border-radius:8px;border:1px solid var(--border);background:var(--surface);
  color:var(--ink);font:inherit;margin-bottom:12px;max-width:340px}
.card h4{margin:0 0 8px;font-size:13px;color:var(--ink-2);text-transform:uppercase;letter-spacing:.04em}
.highlights{border-left:3px solid var(--accent)}
.hi-lead{margin:0 0 14px;color:var(--ink-2)}
.hi-cols{display:grid;grid-template-columns:1fr 1fr;gap:24px}
@media(max-width:640px){.hi-cols{grid-template-columns:1fr}}
.hi-list{list-style:none;margin:0;padding:0;line-height:1.9}
.hi-list li{border-bottom:1px solid var(--grid);padding:3px 0}
.hi-area{margin:0}
.hpct{display:inline-block;min-width:38px;text-align:center;border-radius:4px;padding:0 6px;
  font-variant-numeric:tabular-nums;font-size:12px}
.concept{color:var(--ink-2);font-size:12.5px}
.bars{display:flex;flex-direction:column;gap:6px}
.bars .row{display:grid;grid-template-columns:230px 1fr 96px;gap:10px;align-items:center}
@media(max-width:640px){.bars .row{grid-template-columns:130px 1fr 76px}}
.bars .name{color:var(--ink-2);font-size:13px;text-align:right;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.bars .track{border-left:1px solid var(--baseline);height:16px}
.bars .fill{height:16px;border-radius:0 4px 4px 0}
.bars .val{font-variant-numeric:tabular-nums;font-size:13px}
.spot-head{display:flex;align-items:center;gap:16px;margin:6px 0 16px}
.spot-head .big{font-size:40px;font-weight:700;line-height:1}
.spot-head .meta{color:var(--ink-2)}
table.clsq{border-collapse:separate;border-spacing:2px;width:100%}
table.clsq th{font-weight:500;color:var(--ink-2);font-size:11.5px;padding:2px 8px;text-align:center}
table.clsq th.rowh{text-align:left}
table.clsq td{height:26px;text-align:center;border-radius:4px;font-size:12px;padding:0 8px;font-variant-numeric:tabular-nums}
table.clsq td.num{background:none}
table.clsq td.neg{color:#c0392b}table.clsq td.pos{color:#1f7a44}
table.clsq td.concept-cell{background:none;text-align:left;color:var(--ink-2);font-size:12px}
table.clsq tr.flag td{background:rgba(208,59,59,.08)}
table.clsq tr.flag td.num.neg{font-weight:700}
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
    for pid in ("vce-biology-u34", "ac9-science", "vc2-science"):
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
    from .improve import IMPROVE_SCHEMA, INSTRUCTION_PACK

    ramp_js = (
        "const RAMPS=" + json.dumps(ramps) + ";\n"
        + "const PACKS=" + json.dumps(_packs_payload()) + ";\n"
        + "const STUDIO_CSS=" + json.dumps(_CSS) + ";\n"
        # The CLI (`markable improve`) and the in-browser upgrader send the
        # identical instruction package — one source of truth in improve.py.
        + "const IMPROVE_PACK=" + json.dumps(INSTRUCTION_PACK) + ";\n"
        + "const IMPROVE_SCHEMA=" + json.dumps(IMPROVE_SCHEMA) + ";"
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

  <h2 class="section">Choose your level</h2>
  <div class="products">
    <div class="product vce">
      <span class="band">Senior · VCE Units 1–4</span>
      <h2>VCE</h2>
      <p>SAC results into a landscape dashboard: cohort, per-SAC question analysis,
      class-by-class comparison, and an individual student spotlight — mapped to the
      VCE study design.</p>
      <div class="pbtns">
        <button class="pbtn" onclick="document.getElementById('drop-xlsx-input').click()">Upload SAC results</button>
        <button class="pbtn ghost" onclick="openReportByFile('vce_sac_dashboard.html')">View VCE demo</button>
      </div>
      <div class="curric">Curriculum: VCE study designs (e.g. Biology Units 3 &amp; 4)</div>
    </div>
    <div class="product js">
      <span class="band">Junior · Years 7–10</span>
      <h2>Years 7–10</h2>
      <p>Test results into the same dashboard with per-student and class breakdowns,
      plus test analysis and AI-marking prep — mapped to the Australian Curriculum (v9).</p>
      <div class="pbtns">
        <button class="pbtn" onclick="document.getElementById('drop-xlsx-input').click()">Upload class results</button>
        <button class="pbtn ghost" onclick="openReportByFile('y7-10_dashboard.html')">View Years 7–10 demo</button>
      </div>
      <div class="curric">Curriculum: Australian Curriculum v9 Science (AC9 codes)</div>
    </div>
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

    aimark = """
<div class="view" id="view-aimark">
  <h1>🤖 AI marking studio <span class="beta-chip">cloud</span></h1>
  <p class="lead">Upload your test, your answer key, and the scanned scripts — your chosen AI
  marks them in the cloud and returns per-question marks, evidence and feedback. Uncertain
  items are flagged for your review; you stay the marker of record.</p>

  <div class="card provider-card">
    <h3 style="margin:0 0 10px">Choose your AI &amp; add its key <span class="hint">— one key powers everything here: the test upgrade and the marking.</span></h3>
    <div class="providers">
      <button class="provider" id="prov-claude" onclick="setProvider('claude')">
        <svg viewBox="0 0 48 48" aria-hidden="true"><g fill="currentColor">
          <path d="M24 4l3.2 12.6L40 20l-12.8 3.4L24 36l-3.2-12.6L8 20l12.8-3.4z"/>
          <circle cx="38" cy="9" r="3"/><circle cx="10" cy="38" r="3"/></g></svg>
        <div><b>Claude</b><span>Anthropic · recommended — reads scans &amp; PDFs directly from this page</span></div>
      </button>
      <button class="provider" id="prov-copilot" onclick="setProvider('copilot')">
        <svg viewBox="0 0 48 48" aria-hidden="true"><g fill="none" stroke="currentColor" stroke-width="4" stroke-linecap="round">
          <path d="M14 30a10 10 0 1 1 10-10"/><path d="M34 18a10 10 0 1 1-10 10"/></g></svg>
        <div><b>Copilot / Azure OpenAI</b><span>your workplace's endpoint — images only; some corporate endpoints block browser calls (ask IT)</span></div>
      </button>
    </div>
    <div class="keyfield" id="keys-claude">
      <input id="api-key" type="password" placeholder="sk-ant-…  (console.anthropic.com)" autocomplete="off">
      <button class="btn ghost" onclick="saveKey()">Save</button>
      <span class="status" id="key-status"></span>
    </div>
    <div class="keyfield" id="keys-copilot" style="display:none">
      <input id="cp-endpoint" type="text" placeholder="paste your chat-completions endpoint URL (Azure OpenAI / gateway)" autocomplete="off" style="width:420px;max-width:100%">
      <input id="cp-key" type="password" placeholder="API key" autocomplete="off">
      <button class="btn ghost" onclick="saveKey()">Save</button>
      <span class="status" id="key-status2"></span>
    </div>
    <p class="hint" style="margin:8px 0 0">Keys are stored only in this browser and sent only to the provider you picked.</p>
  </div>

  <div class="aim-grid">
    <div class="drop aim-step" id="drop-aim-test">
      <div class="stepnum">1</div><div class="big">📄</div>
      <h3>The test</h3>
      <p>The question paper (.docx, .md or .txt).</p>
      <button class="btn" onclick="$('aim-test-input').click()">Choose test</button>
      <input id="aim-test-input" type="file" accept=".docx,.md,.txt,.markdown" hidden>
      <div class="status" id="aim-test-status"></div>
    </div>
    <div class="drop aim-step" id="drop-aim-key">
      <div class="stepnum">2</div><div class="big">🔑</div>
      <h3>The answer key</h3>
      <p>Marking scheme / answers / rubric (.docx, .md, .txt or .yaml).</p>
      <button class="btn" onclick="$('aim-key-input').click()">Choose answer key</button>
      <input id="aim-key-input" type="file" accept=".docx,.md,.txt,.markdown,.yaml,.yml" hidden>
      <div class="status" id="aim-key-status"></div>
    </div>
    <div class="drop aim-step" id="drop-aim-scans">
      <div class="stepnum">3</div><div class="big">🖨️</div>
      <h3>The scanned scripts</h3>
      <p>Student scripts as images or PDFs — one file per student works best.</p>
      <button class="btn" onclick="$('aim-scans-input').click()">Choose scans</button>
      <input id="aim-scans-input" type="file" accept=".png,.jpg,.jpeg,.webp,.gif,.pdf" multiple hidden>
      <div class="status" id="aim-scans-status"></div>
    </div>
  </div>

  <div class="aim-actions">
    <button class="btn" id="aim-mark-btn" onclick="markScans()">🤖 Mark the scripts</button>
    <button class="btn ghost" onclick="show('optimise')">✨ Optimise the test first (no scans needed)</button>
  </div>

  <div class="result" id="aim-result"></div>

  <div class="privacy-note">🔒 Files go directly from this browser to the AI provider you chose,
  over HTTPS — there is no Markable server in between.</div>
</div>
"""

    optimise = """
<div class="view" id="view-optimise">
  <h1>✨ Assessment optimiser <span class="beta-chip">cloud</span></h1>
  <p class="lead">Drop in any test or assessment and get back a version optimised for reliable
  AI marking — unique question IDs, explicit marks, typed items, tightened wording — with a
  change log and a before/after readiness score. Your questions, difficulty and topics are
  preserved: it restructures, it never rewrites your assessment.</p>

  <div class="opt-flow">
    <div class="opt-step"><span class="opt-n">1</span> Upload your assessment</div>
    <div class="opt-arrow">→</div>
    <div class="opt-step"><span class="opt-n">2</span> Markable checks AI-readiness</div>
    <div class="opt-arrow">→</div>
    <div class="opt-step"><span class="opt-n">3</span> AI optimises it</div>
    <div class="opt-arrow">→</div>
    <div class="opt-step"><span class="opt-n">4</span> Review changes &amp; download</div>
  </div>

  <div class="uploads" style="grid-template-columns:1fr">
    <div class="drop" id="drop-opt">
      <div class="big">✨</div>
      <h3>Assessment → AI-optimised assessment</h3>
      <p>Drop your test (.docx, .md or .txt). You'll see its readiness score first,
      then one click optimises it with <span class="prov-name">Claude</span>.</p>
      <button class="btn" onclick="$('drop-opt-input').click()">Choose assessment</button>
      <input id="drop-opt-input" type="file" accept=".docx,.md,.txt,.markdown" hidden>
      <div class="hint">Powered by your own AI key — set up under
        <a href="#" onclick="show('aimark');scrollToEl('prov-claude');return false">Claude / Copilot setup</a>.</div>
      <div class="status" id="opt-status"></div>
    </div>
  </div>

  <div class="result" id="opt-result"></div>

  <div class="privacy-note">🔒 The readiness check runs locally. Optimising sends the test
  directly from this browser to the AI provider you chose — nothing in between.</div>
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
    <button class="nav-item" data-view="guide" onclick="show('guide',this)">📘 How to use</button>
    <h4>Upload</h4>
    <button class="nav-item" onclick="show('home');document.getElementById('drop-xlsx-input').click()">📈 Results → dashboard</button>
    <button class="nav-item" onclick="show('home');document.getElementById('drop-doc-input').click()">📝 Test → AI-marking prep</button>
    <h4>AI cloud</h4>
    <button class="nav-item" data-view="optimise" onclick="show('optimise',this)">✨ Assessment optimiser</button>
    <button class="nav-item" data-view="aimark" onclick="show('aimark',this)">🤖 AI marking studio</button>
    <button class="nav-item sub" onclick="show('aimark');scrollToEl('drop-aim-scans')">↳ Mark scanned scripts</button>
    <button class="nav-item sub" onclick="show('aimark');scrollToEl('prov-claude')">↳ Claude / Copilot setup</button>
    <h4>Reports</h4>
    {_report_nav()}
    <div class="nav-foot">{nav_foot}</div>
  </nav>
  <main class="main">
    {landing}
    {optimise}
    {aimark}
    {_guide_view()}
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
function openReportByFile(file){
  const btn=document.querySelector('.nav-item[data-file="'+file+'"]');
  if(btn){btn.scrollIntoView({block:'nearest'});openReport(btn);}
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
    let tgt=relMap[rid]||'';
    if(tgt.startsWith('/')) tgt=tgt.slice(1);          // absolute (openpyxl): /xl/worksheets/… → xl/worksheets/…
    else if(tgt && !tgt.startsWith('xl/')) tgt='xl/'+tgt; // relative to xl/
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
    if(['surname','first name','id','vcaa number','class','form','class group'].includes(k))cols[k]=c;}
  if(cols['surname']===undefined) return null;
  const classCol=cols['class']!==undefined?cols['class']:(cols['class group']!==undefined?cols['class group']:cols['form']);
  const qs=[];
  for(let c=0;c<120;c++){const mm=String(cell(g,h,c)||'').trim().match(/^\/\s*(\d+(?:\.\d+)?)$/);
    if(!mm)continue; let lab=cell(g,h-1,c); lab=(lab===null||lab==='')?String(c):String(lab).trim();
    if(lab.toUpperCase()==='TOTAL')continue; qs.push({id:lab,max:parseFloat(mm[1]),col:c});}
  if(!qs.length) return null;
  const students=[];
  for(let r=h+1;r<200;r++){const sn=cell(g,r,cols['surname']); if(sn===null||sn==='')continue;
    const fn=cell(g,r,cols['first name']!==undefined?cols['first name']:cols['surname']);
    const cl=classCol!==undefined?String(cell(g,r,classCol)||'').trim():'';
    const st={name:(String(sn).trim()+', '+String(fn||'').trim()).replace(/, $/,''), cls:cl, marks:{}};
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
  RAMPS.heatLight.forEach((c,i)=>s+='.mx td.h'+i+',.hpct.h'+i+',.bars .fill.h'+i+'{background:'+c+'}');
  s+='@media (prefers-color-scheme:dark){';
  RAMPS.greenDark.forEach((c,i)=>s+='.mx td.g'+i+'{background:'+c+'}');
  RAMPS.heatDark.forEach((c,i)=>s+='.mx td.h'+i+',.hpct.h'+i+',.bars .fill.h'+i+'{background:'+c+'}');
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
function hcell(p,title){if(p===null||p===undefined)return '<td class="na">—</td>';
  return '<td class="h'+heatBin(p)+'" title="'+esc(title||'')+'">'+Math.round(p)+'</td>'}
function shortA(a){return a.includes('—')?a.split('—')[1].trim():a}
function facSet(sac,q,set){const m=sac.students.filter(s=>set.has(s.name)).map(s=>s.marks[q.id]||0);
  return (!m.length||!q.max)?null:m.reduce((a,b)=>a+b,0)/(q.max*m.length)}
function classList(sacs){const seen=[];sacs.forEach(sac=>sac.students.forEach(st=>{
  if(st.cls&&!seen.includes(st.cls))seen.push(st.cls)}));return seen.sort()}
/* {sacNumber:{qid:area}} from the auto-mapper — the studio packs carry areas, not codes */
function qmetaFor(sacs,packId){const out={};if(!packId||!PACKS[packId])return out;
  const pack=PACKS[packId];sacs.forEach(sac=>{const m={};sac.questions.forEach(q=>{const a=autoArea(q.id,pack);if(a)m[q.id]=a});out[sac.number]=m});return out}

function highlightsCard(sacs,packId,term){
  const qmeta=qmetaFor(sacs,packId);
  let hardest=[];
  sacs.forEach(sac=>{const names=new Set(sac.students.map(s=>s.name));
    sac.questions.forEach(q=>{const f=facSet(sac,q,names);
      if(f!==null)hardest.push({f,sac,qid:q.id,area:(qmeta[sac.number]||{})[q.id]||''})})});
  hardest.sort((a,b)=>a.f-b.f);const top=hardest.slice(0,5);
  const items=top.map(t=>{const concept=t.area?' <span class="concept">— '+esc(shortA(t.area))+'</span>':'';
    const p=Math.round(t.f*100);
    return '<li><b>'+esc(t.qid)+'</b> <span class="muted">('+esc(t.sac.topic)+')</span> — '+
      '<span class="hpct h'+heatBin(p)+'">'+p+'%</span>'+concept+'</li>'}).join('');
  // weakest / strongest area across cohort
  let areaLine='';
  if(packId&&PACKS[packId]){const agg={};
    sacs.forEach(sac=>{const qm=qmeta[sac.number]||{};const names=new Set(sac.students.map(s=>s.name));
      sac.questions.forEach(q=>{const a=qm[q.id];if(!a)return;
        const aw=sac.students.reduce((s,st)=>s+(st.marks[q.id]||0),0);
        agg[a]=agg[a]||[0,0];agg[a][0]+=aw;agg[a][1]+=q.max*names.size})});
    const pcts={};Object.keys(agg).forEach(a=>{if(agg[a][1])pcts[a]=100*agg[a][0]/agg[a][1]});
    const ks=Object.keys(pcts);
    if(ks.length){const weak=ks.reduce((m,a)=>pcts[a]<pcts[m]?a:m),strong=ks.reduce((m,a)=>pcts[a]>pcts[m]?a:m);
      areaLine='<p class="hi-area">Weakest area: <b>'+esc(shortA(weak))+'</b> ('+Math.round(pcts[weak])+
        '%) · Strongest: <b>'+esc(shortA(strong))+'</b> ('+Math.round(pcts[strong])+'%)</p>'}}
  const allPct=[];sacs.forEach(sac=>sac.students.forEach(st=>{if(sac.total)allPct.push(100*totalFor(sac,st)/sac.total)}));
  const avg=allPct.length?allPct.reduce((a,b)=>a+b,0)/allPct.length:0;
  const below=allPct.filter(p=>p<50).length;
  return '<div class="card highlights"><h3>🔑 Key highlights</h3>'+
    '<p class="hi-lead">Cohort average <b>'+Math.round(avg)+'%</b> across '+sacs.length+' '+esc(term.toLowerCase())+'(s) · '+
    below+' result(s) below 50% flagged for support.</p>'+
    '<div class="hi-cols"><div><h4>Hardest questions</h4><ul class="hi-list">'+items+'</ul></div>'+
    '<div><h4>Where to focus</h4>'+(areaLine||'<p class="muted">Add a study design to link questions to concepts.</p>')+
    '<p class="muted" style="margin-top:8px">Each hardest question shows its linked concept where mapped.</p></div></div></div>';
}

function sacTab(sac,idx,term){
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
  return '<div class="subtab" id="st'+idx+'"><h3 class="tab-h">'+esc(term)+' '+esc(sac.number)+' — '+esc(sac.topic)+'</h3>'+
    '<div class="kpis">'+kt+'</div>'+
    '<div class="card"><h3>Score distribution</h3>'+histogram(vals)+'</div>'+
    '<div class="card"><h3>Question performance by cohort quartile</h3><div class="mx"><table>'+head+rows+'</table></div>'+
    '<p class="foot">easy ≥80% · moderate 50–79% · difficult &lt;50%</p></div></div>';
}
function overviewTab(sacs,term,highlights){
  const lo=term.toLowerCase();
  const sacPct=sacs.map(sac=>{const p={};sac.students.forEach(st=>{if(sac.total)p[st.name]=100*totalFor(sac,st)/sac.total});return p});
  const students=[...new Set(sacs.flatMap((s,i)=>Object.keys(sacPct[i])))].sort();
  const allVals=sacPct.flatMap(p=>Object.values(p));
  const kt=tiles([['Students',students.length,'',true],[term+'s',sacs.length,'',false],
    ['Overall average',Math.round(allVals.reduce((a,b)=>a+b,0)/allVals.length)+'%','across all '+lo+'s',false]]);
  const bars=sacs.map((sac,i)=>{const p=sacPct[i],avg=Object.values(p).reduce((a,b)=>a+b,0)/Object.values(p).length;
    return '<div style="display:grid;grid-template-columns:220px 1fr 48px;gap:10px;align-items:center;padding:5px 0">'+
      '<div style="color:var(--ink-2);font-size:13px;text-align:right;overflow:hidden;text-overflow:ellipsis;white-space:nowrap">'+esc(term)+' '+esc(sac.number)+': '+esc(sac.topic)+'</div>'+
      '<div style="border-left:1px solid var(--baseline);height:16px"><div class="fill h'+heatBin(avg)+'" style="height:16px;border-radius:0 4px 4px 0;width:'+avg.toFixed(1)+'%"></div></div>'+
      '<div style="font-variant-numeric:tabular-nums">'+Math.round(avg)+'%</div></div>'}).join('');
  const head='<tr><th class="rowh">Student</th>'+sacs.map(s=>'<th>'+esc(term)+' '+esc(s.number)+'</th>').join('')+'<th>Overall</th></tr>';
  const rows=students.map(nm=>{const vals=sacs.map((s,i)=>sacPct[i][nm]);
    const present=vals.filter(v=>v!==undefined);const ov=present.length?present.reduce((a,b)=>a+b,0)/present.length:null;
    const cells=vals.map(v=>v===undefined?'<td class="na">—</td>':'<td class="h'+heatBin(v)+'">'+Math.round(v)+'</td>').join('');
    return '<tr><th class="rowh">'+esc(nm)+'</th>'+cells+(ov===null?'<td class="na">—</td>':'<td class="h'+heatBin(ov)+'">'+Math.round(ov)+'</td>')+'</tr>'}).join('');
  return '<div class="subtab active" id="st-ov"><div class="kpis">'+kt+'</div>'+(highlights||'')+
    '<div class="card"><h3>Cohort average by '+esc(lo)+'</h3>'+bars+'</div>'+
    '<div class="card"><h3>Every student across every '+esc(lo)+'</h3><div class="mx"><table>'+head+rows+'</table></div>'+
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
function skillsTab(sacs,packId,term){
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
    blocks+='<div class="card"><h3>'+esc(term)+' '+esc(sac.number)+' — '+esc(sac.topic)+': attainment by study-design area</h3>'+
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

/* ---------- classes: class×assessment + my-class question analysis ---------- */
function classesTab(sacs,term){
  const cls=classList(sacs);if(!cls.length)return '';
  const lo=term.toLowerCase();
  const pct=sacs.map(sac=>{const p={};sac.students.forEach(st=>{if(sac.total)p[st.name]=100*totalFor(sac,st)/sac.total});return p});
  const head='<tr><th class="rowh">Class</th>'+sacs.map(s=>'<th>'+esc(term)+' '+esc(s.number)+'</th>').join('')+'<th>Overall</th><th>Students</th></tr>';
  const rows=cls.map(c=>{let cells='',ov=[],n=0;
    sacs.forEach((s,i)=>{const members=s.students.filter(st=>st.cls===c).map(st=>st.name);n=Math.max(n,members.length);
      const vals=members.map(m=>pct[i][m]).filter(v=>v!==undefined);
      if(vals.length){const avg=vals.reduce((a,b)=>a+b,0)/vals.length;ov.push(avg);cells+=hcell(avg,c+' · '+term+' '+s.number)}
      else cells+='<td class="na">—</td>'});
    const o=ov.length?ov.reduce((a,b)=>a+b,0)/ov.length:null;
    return '<tr><th class="rowh">'+esc(c)+'</th>'+cells+hcell(o,c+' · overall')+
      '<td style="background:none;color:var(--ink-2)">'+n+'</td></tr>'}).join('');
  const opts=cls.map((c,i)=>'<option value="'+esc(c)+'"'+(i===0?' selected':'')+'>'+esc(c)+'</option>').join('');
  return '<div class="subtab" id="st-cls"><h3 class="tab-h">Class-by-class comparison</h3>'+
    '<div class="card"><div class="mx"><table>'+head+rows+'</table></div>'+
    '<p class="foot">Average % per class per '+esc(lo)+'.</p></div>'+
    '<div class="card"><h3>My class — question-level analysis</h3>'+
    '<p class="foot" style="margin-top:0">Pick your class to see how it went on each question, against the whole cohort. '+
    'Questions where your class is 10+ points below the cohort are flagged.</p>'+
    '<select class="picker" id="clsq-pick" onchange="renderClassQ()">'+opts+'</select><div id="clsq-body"></div></div></div>';
}
function renderClassQ(){
  const el=document.getElementById('clsq-body');if(!el)return;
  const c=document.getElementById('clsq-pick').value;
  const sacs=LAST_SACS,qmeta=qmetaFor(sacs,LAST_PACK),term=LAST_TERM;let h='';
  sacs.forEach(sac=>{const all=new Set(sac.students.map(s=>s.name));
    const mine=new Set(sac.students.filter(s=>s.cls===c).map(s=>s.name));let rows='',flagged=0;
    sac.questions.forEach(q=>{const cf=facSet(sac,q,mine),coh=facSet(sac,q,all);
      const cp=cf===null?null:Math.round(cf*100),chp=coh===null?null:Math.round(coh*100);
      const delta=(cp===null||chp===null)?null:cp-chp;const flag=(delta!==null&&delta<=-10);if(flag)flagged++;
      const area=(qmeta[sac.number]||{})[q.id]||'';const concept=area?esc(shortA(area)):'<span class="muted">—</span>';
      rows+='<tr'+(flag?' class="flag"':'')+'><td><b>'+esc(q.id)+'</b></td>'+hcell(cp,c+' · '+q.id)+
        '<td class="num" style="color:var(--ink-2)">'+(chp===null?'—':chp)+'</td>'+
        '<td class="num '+(delta!==null&&delta<0?'neg':'pos')+'">'+(delta===null?'—':(delta>0?'+':'')+delta)+'</td>'+
        '<td class="concept-cell">'+concept+'</td></tr>'});
    h+='<div class="card"><h3>'+esc(term)+' '+esc(sac.number)+' — '+esc(sac.topic)+'</h3>'+
      '<p class="foot" style="margin:0 0 10px">'+(flagged?('<b>'+flagged+'</b> question(s) where '+esc(c)+' is 10+ points below the cohort — worth reviewing.'):(esc(c)+' is at or above the cohort on every question here.'))+'</p>'+
      '<div class="mx"><table class="clsq"><tr><th class="rowh">Q</th><th>'+esc(c)+'</th><th>Cohort</th><th>Δ</th><th>Concept</th></tr>'+rows+'</table></div></div>'});
  el.innerHTML=h;
}
/* ---------- student spotlight ---------- */
function studentTab(sacs,term){
  const names=[...new Set(sacs.flatMap(s=>s.students.map(st=>st.name)))].sort();
  const opts=names.map((n,i)=>'<option value="'+esc(n)+'"'+(i===0?' selected':'')+'>'+esc(n)+'</option>').join('');
  return '<div class="subtab" id="st-student"><h3 class="tab-h">Student spotlight</h3>'+
    '<p class="foot" style="margin-top:0">Pick a student to see how they went on every '+esc(term.toLowerCase())+', question by question.</p>'+
    '<select class="picker" id="spot-pick" onchange="renderSpot()">'+opts+'</select><div id="spot-body"></div></div>';
}
function renderSpot(){
  const el=document.getElementById('spot-body');if(!el)return;
  const name=document.getElementById('spot-pick').value;const sacs=LAST_SACS,term=LAST_TERM,lo=term.toLowerCase();
  const qmeta=qmetaFor(sacs,LAST_PACK);
  const pct=sacs.map(sac=>{const p={};sac.students.forEach(st=>{if(sac.total)p[st.name]=100*totalFor(sac,st)/sac.total});return p});
  const coh=sacs.map((sac,i)=>{const v=Object.values(pct[i]);return v.length?v.reduce((a,b)=>a+b,0)/v.length:0});
  let mine=[],cls='';const ov=[];
  sacs.forEach((sac,i)=>{const st=sac.students.find(s=>s.name===name);if(!st)return;cls=cls||st.cls;
    const p=pct[i][name];if(p!==undefined)ov.push(p);
    mine.push({sac,i,st,p:p===undefined?null:p})});
  const overall=ov.length?Math.round(ov.reduce((a,b)=>a+b,0)/ov.length):null;
  let h='<div class="spot-head"><div class="big">'+(overall==null?'—':overall+'%')+'</div>'+
    '<div class="meta"><b>'+esc(name)+'</b>'+(cls?' · '+esc(cls):'')+' · overall across '+mine.length+' '+esc(lo)+'(s)</div></div>';
  h+='<div class="card"><h3>Result on each '+esc(lo)+' vs cohort average</h3><div class="bars">';
  mine.forEach(m=>{const p=m.p==null?0:m.p,cavg=Math.round(coh[m.i]);
    h+='<div class="row"><div class="name">'+esc(term)+' '+esc(m.sac.number)+': '+esc(m.sac.topic)+'</div>'+
      '<div class="track"><div class="fill h'+heatBin(p)+'" style="width:'+p+'%"></div></div>'+
      '<div class="val">'+(m.p==null?'—':Math.round(m.p)+'%')+'<span style="color:var(--ink-2)"> / '+cavg+'</span></div></div>'});
  h+='</div><p class="foot">Green→red = this student\'s %. The grey number is the cohort average.</p></div>';
  mine.forEach(m=>{let head='<tr><th class="rowh">'+esc(term)+' '+esc(m.sac.number)+'</th>',row='<tr><th class="rowh">% of marks</th>';
    m.sac.questions.forEach(q=>{head+='<th>'+esc(q.id)+'</th>';const mk=m.st.marks[q.id];
      const p=(mk==null||!q.max)?null:100*mk/q.max;row+=hcell(p,name+' · '+q.id+' ('+(mk==null?'—':mk)+'/'+q.max+')')});
    head+='</tr>';row+='</tr>';
    h+='<div class="card"><h3>'+esc(m.sac.topic)+' — question by question</h3><div class="mx"><table>'+head+row+'</table></div></div>'});
  // study-design areas
  if(LAST_PACK&&PACKS[LAST_PACK]){const agg={};
    sacs.forEach((sac,i)=>{const st=sac.students.find(s=>s.name===name);if(!st)return;const qm=qmeta[sac.number]||{};
      sac.questions.forEach(q=>{const a=qm[q.id];if(!a)return;agg[a]=agg[a]||[0,0];agg[a][0]+=(st.marks[q.id]||0);agg[a][1]+=q.max})});
    const areas=Object.keys(agg).filter(a=>agg[a][1]).map(a=>({area:a,pct:Math.round(100*agg[a][0]/agg[a][1])})).sort((x,y)=>x.pct-y.pct);
    if(areas.length){h+='<div class="card"><h3>Study-design areas — strengths &amp; growth</h3><div class="bars">';
      areas.forEach(a=>{h+='<div class="row"><div class="name">'+esc(shortA(a.area))+'</div>'+
        '<div class="track"><div class="fill h'+heatBin(a.pct)+'" style="width:'+a.pct+'%"></div></div>'+
        '<div class="val">'+a.pct+'%</div></div>'});
      h+='</div><p class="foot">Sorted weakest→strongest — the top rows are where to focus support.</p></div>'}}
  el.innerHTML=h;
}

let LAST_SACS=null, LAST_TITLE='', LAST_PACK='', LAST_TERM='SAC';
function packOptions(sel){return '<option value="">Study design: none</option>'+
  Object.keys(PACKS).map(id=>'<option value="'+id+'"'+(id===sel?' selected':'')+'>'+esc(PACKS[id].name)+'</option>').join('')}
const SELCSS='padding:7px 10px;border-radius:8px;border:1px solid var(--border);background:var(--surface);color:var(--ink);font:inherit';
function renderDashboard(sacs,packId,term){
  term=term||'SAC';
  const hasCls=classList(sacs).length>0;
  const levelSel='<select onchange="LAST_TERM=this.value;reRenderDash()" style="'+SELCSS+'" title="Level / terminology">'+
    ['SAC','Assessment'].map(t=>'<option value="'+t+'"'+(t===term?' selected':'')+'>'+
      (t==='SAC'?'VCE (SACs)':'Years 7–10 (Assessments)')+'</option>').join('')+'</select>';
  const toolbar='<div style="display:flex;gap:10px;align-items:center;flex-wrap:wrap;margin-bottom:12px">'+
    levelSel+
    '<select onchange="LAST_PACK=this.value;reRenderDash()" style="'+SELCSS+'">'+packOptions(packId)+'</select>'+
    '<button class="btn ghost" onclick="downloadDash()">⬇ Download this dashboard</button></div>';
  const highlights=highlightsCard(sacs,packId,term);
  const tabs=['<button class="active" onclick="pickSub(this,\'st-ov\')">Overview</button>']
    .concat(sacs.map((s,i)=>'<button onclick="pickSub(this,\'st'+i+'\')">'+esc(term)+' '+esc(s.number)+'</button>'));
  if(hasCls) tabs.push('<button onclick="pickSub(this,\'st-cls\')">Classes</button>');
  tabs.push('<button onclick="pickSub(this,\'st-student\')">Student</button>');
  if(packId) tabs.push('<button onclick="pickSub(this,\'st-skills\')">Skills &amp; content</button>');
  let bodies=overviewTab(sacs,term,highlights)+sacs.map((s,i)=>sacTab(s,i,term)).join('');
  if(hasCls) bodies+=classesTab(sacs,term);
  bodies+=studentTab(sacs,term);
  if(packId) bodies+=skillsTab(sacs,packId,term);
  return rampCss()+toolbar+'<div class="subtabs">'+tabs.join('')+'</div>'+bodies;
}
function mountDash(){
  $('xlsx-result').innerHTML='<h2 class="section" id="dash-title">Dashboard — '+esc(LAST_TITLE)+'</h2>'+
    renderDashboard(LAST_SACS,LAST_PACK,LAST_TERM);
  if(classList(LAST_SACS).length)renderClassQ();
  renderSpot();
}
function reRenderDash(){ if(LAST_SACS) mountDash(); }
function downloadDash(){
  const fns=[esc,med,totalFor,greenBin,heatBin,hcell,shortA,facSet,classList,qmetaFor,tiles,histogram,
    quartSeg,rampCss,highlightsCard,sacTab,overviewTab,terms,autoArea,skillsTab,classesTab,renderClassQ,
    studentTab,renderSpot,packOptions,renderDashboard,mountDash,reRenderDash,downloadDash,pickSub];
  const runtime='var STOP=new Set('+JSON.stringify([...STOP])+');\n'+
    'var RAMPS='+JSON.stringify(RAMPS)+';\nvar PACKS='+JSON.stringify(PACKS)+';\n'+
    'var STUDIO_CSS='+JSON.stringify(STUDIO_CSS)+';\n'+
    'var SELCSS='+JSON.stringify(SELCSS)+';\n'+
    'var LAST_SACS='+JSON.stringify(LAST_SACS)+';\nvar LAST_TITLE='+JSON.stringify(LAST_TITLE)+';\n'+
    'var LAST_PACK='+JSON.stringify(LAST_PACK)+';\nvar LAST_TERM='+JSON.stringify(LAST_TERM)+';\n'+
    'function $(id){return document.getElementById(id)}\n'+
    fns.map(f=>f.toString()).join('\n')+'\n'+
    'document.addEventListener("DOMContentLoaded",function(){reRenderDash()});';
  const doc='<!DOCTYPE html><html lang="en"><head><meta charset="utf-8">'+
    '<meta name="viewport" content="width=device-width,initial-scale=1">'+
    '<title>'+esc(LAST_TITLE)+' — Markable dashboard</title><style>'+STUDIO_CSS+
    'body{padding:24px 30px}</style></head><body><div class="result active" id="xlsx-result"></div>'+
    '<script>'+runtime+'<\/script></body></html>';
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
    '<div class="aim-actions" style="margin:14px 0 4px">'+
    '<button class="btn" onclick="upgradeTest(\'doc-result\')">🪄 Reformat with '+(PROVIDER==='copilot'?'Copilot':'Claude')+'</button>'+
    '<button class="btn ghost" onclick="show(\'aimark\');scrollToEl(\'prov-claude\')">Switch AI (Claude / Copilot)</button>'+
    '<span class="hint" style="align-self:center">Sends the test + Markable\'s upgrade instructions to your chosen AI; you get back a restructured, AI-marking-ready version with a change log.</span></div>'+
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
    LAST_SACS=sacs; LAST_TITLE=file.name; LAST_PACK=''; LAST_TERM='SAC';
    mountDash();
    $('xlsx-result').classList.add('active');
    const hasCls=classList(sacs).length;
    st.textContent='✓ '+sacs.length+' assessment(s), '+sacs[0].students.length+' students'+(hasCls?', '+classList(sacs).length+' classes':'')+'.';
    $('xlsx-result').scrollIntoView({behavior:'smooth'});
  }catch(err){st.className='status err';st.textContent='Could not read that file: '+err.message}
});
wireDrop('drop-doc','drop-doc-input',async file=>{
  const st=$('doc-status');st.className='status';st.textContent='Analysing '+file.name+' …';
  try{
    const text=await docText(file.name,await file.arrayBuffer());
    if(!text.trim())throw new Error('No readable text found in that document.');
    LAST_DOC={name:file.name,text};
    const rep=analyseReadiness(text);
    $('doc-result').innerHTML='<h2 class="section">Readiness</h2>'+renderReadiness(file.name,rep);
    $('doc-result').classList.add('active');
    st.textContent='✓ Analysed — readiness '+rep.score+'%.';
    $('doc-result').scrollIntoView({behavior:'smooth'});
  }catch(err){st.className='status err';st.textContent='Could not analyse that file: '+err.message}
});

/* ================= AI cloud: provider, keys, transport, upgrade, marking ================= */
function scrollToEl(id){const el=$(id);if(el)el.scrollIntoView({behavior:'smooth',block:'center'})}
const KEY_STORE='markable_api_key';           // Anthropic key
const CP_EP_STORE='markable_cp_endpoint';     // Copilot / Azure OpenAI endpoint + key
const CP_KEY_STORE='markable_cp_key';
const PROV_STORE='markable_provider';
let PROVIDER=localStorage.getItem(PROV_STORE)||'claude';
function setProvider(p){
  PROVIDER=p;localStorage.setItem(PROV_STORE,p);
  const c=$('prov-claude'),o=$('prov-copilot');
  if(c){c.classList.toggle('on',p==='claude');o.classList.toggle('on',p==='copilot');
    $('keys-claude').style.display=p==='claude'?'flex':'none';
    $('keys-copilot').style.display=p==='copilot'?'flex':'none';}
  document.querySelectorAll('.prov-name').forEach(e=>e.textContent=p==='copilot'?'Copilot':'Claude');
}
function getKey(){return (localStorage.getItem(KEY_STORE)||'').trim()}
function getCp(){return {endpoint:(localStorage.getItem(CP_EP_STORE)||'').trim(),
  key:(localStorage.getItem(CP_KEY_STORE)||'').trim()}}
function saveKey(){
  if(PROVIDER==='claude'){
    localStorage.setItem(KEY_STORE,$('api-key').value.trim());
    const s=$('key-status');s.className='status';s.textContent=getKey()?'✓ Saved in this browser.':'Cleared.';
  }else{
    localStorage.setItem(CP_EP_STORE,$('cp-endpoint').value.trim());
    localStorage.setItem(CP_KEY_STORE,$('cp-key').value.trim());
    const s=$('key-status2');s.className='status';
    s.textContent=(getCp().endpoint&&getCp().key)?'✓ Saved in this browser.':'Cleared.';
  }
}
function haveCreds(){return PROVIDER==='claude'?!!getKey():!!(getCp().endpoint&&getCp().key)}
function needKey(){
  if(haveCreds())return true;
  show('aimark');scrollToEl('prov-claude');
  const s=$(PROVIDER==='claude'?'key-status':'key-status2');s.className='status err';
  s.textContent=PROVIDER==='claude'
    ?'Add your Anthropic API key first — the cloud steps need it.'
    :'Add your Copilot/Azure OpenAI endpoint URL and key first.';
  return false;
}
/* ---- transport: one entry point, two providers ---- */
async function callAI(opts){  // {system, schema, content(anthropic blocks)}
  if(PROVIDER==='claude')return callClaude(opts);
  return callOpenAI(opts);
}
async function callClaude(opts){
  // Direct browser → Anthropic; the CORS opt-in header acknowledges the key
  // lives client-side (it is the teacher's own key, stored only locally).
  const res=await fetch('https://api.anthropic.com/v1/messages',{
    method:'POST',
    headers:{'content-type':'application/json','x-api-key':getKey(),
      'anthropic-version':'2023-06-01','anthropic-dangerous-direct-browser-access':'true'},
    body:JSON.stringify({model:'claude-opus-4-8',max_tokens:16000,thinking:{type:'adaptive'},
      system:[{type:'text',text:opts.system,cache_control:{type:'ephemeral'}}],
      output_config:{format:{type:'json_schema',schema:opts.schema}},
      messages:[{role:'user',content:opts.content}]})});
  const data=await res.json().catch(()=>({}));
  if(!res.ok){throw new Error((data.error&&data.error.message)||('API error '+res.status))}
  if(data.stop_reason==='refusal')throw new Error('the model declined to process this document');
  const block=(data.content||[]).find(b=>b.type==='text');
  if(!block)throw new Error('no text in the response');
  return JSON.parse(block.text);
}
async function callOpenAI(opts){
  // OpenAI-compatible chat-completions endpoint (Azure OpenAI / a workplace
  // Copilot gateway). Anthropic content blocks are converted; JSON is enforced
  // via json_object mode + the schema inlined in the prompt.
  const cp=getCp();
  const content=[];
  for(const b of opts.content){
    if(b.type==='text')content.push({type:'text',text:b.text});
    else if(b.type==='image')content.push({type:'image_url',
      image_url:{url:'data:'+b.source.media_type+';base64,'+b.source.data}});
    else if(b.type==='document')
      throw new Error('PDF scans need Claude — with Copilot/Azure OpenAI, upload scans as images (PNG/JPG), or switch provider.');
  }
  const headers={'content-type':'application/json'};
  if(/azure|\bapi-key\b/i.test(cp.endpoint))headers['api-key']=cp.key;
  else headers['authorization']='Bearer '+cp.key;
  const res=await fetch(cp.endpoint,{method:'POST',headers,body:JSON.stringify({
    messages:[{role:'system',content:opts.system+'\n\nRespond ONLY with a JSON object matching this schema:\n'+JSON.stringify(opts.schema)},
      {role:'user',content}],
    response_format:{type:'json_object'},max_tokens:8000})});
  const data=await res.json().catch(()=>({}));
  if(!res.ok){throw new Error((data.error&&data.error.message)||('endpoint error '+res.status+
    ' — if this is a CORS/network error, your workplace endpoint may not allow browser calls; ask IT or use Claude'))}
  const text=data.choices&&data.choices[0]&&data.choices[0].message&&data.choices[0].message.content;
  if(!text)throw new Error('no content in the response');
  return JSON.parse(text);
}
function busy(el,msg){el.innerHTML='<div class="card"><p><span class="spin"></span>'+esc(msg)+
  ' <span class="muted">(can take a minute — Claude is thinking)</span></p></div>';el.classList.add('active')}
function dlButton(label,content,fname,mime){
  const id='dl'+Math.random().toString(36).slice(2,8);
  setTimeout(()=>{const b=$(id);if(b)b.onclick=()=>{
    const a=document.createElement('a');
    a.href=URL.createObjectURL(new Blob([content],{type:mime||'text/plain'}));
    a.download=fname;a.click();setTimeout(()=>URL.revokeObjectURL(a.href),2000)}},0);
  return '<button class="btn" id="'+id+'">'+esc(label)+'</button>';
}

/* ---------- upgrade: test + instruction pack → improved test ---------- */
let LAST_DOC=null;
function provName(){return PROVIDER==='copilot'?'Copilot':'Claude'}
async function upgradeTest(resultId){
  if(!LAST_DOC){show('home');scrollToEl('drop-doc');return}
  if(!needKey())return;
  const el=$(resultId);busy(el,'Reformatting “'+LAST_DOC.name+'” with '+provName()+'…');
  try{
    const out=await callAI({system:IMPROVE_PACK,schema:IMPROVE_SCHEMA,
      content:[{type:'text',text:'Upgrade this draft test:\n\n'+LAST_DOC.text}]});
    const changes=(out.changes||[]).map(c=>'<li><b>'+esc(c.question_id)+'</b> — '+esc(c.change)+
      ' <span class="muted">('+esc(c.reason)+')</span></li>').join('');
    const fname=LAST_DOC.name.replace(/\.[^.]+$/,'')+'.improved.md';
    el.innerHTML='<h2 class="section">✨ Upgraded test</h2>'+
      '<div class="card"><p style="margin-top:0">'+esc(out.summary||'')+'</p>'+
      '<div class="aim-actions">'+dlButton('⬇ Download '+fname,out.improved_markdown,fname,'text/markdown')+
      '</div>'+
      '<h3>What changed <span class="muted">(verify anything inferred)</span></h3>'+
      '<ul class="changes">'+changes+'</ul>'+
      '<h3>Preview</h3><pre style="white-space:pre-wrap;background:var(--page);border:1px solid var(--border);border-radius:8px;padding:12px;max-height:420px;overflow:auto">'+
      esc(out.improved_markdown)+'</pre>'+
      '<p class="foot">Review the changes, then run <code>markable ingest</code> → <code>markable build</code> on the downloaded file for a scan-ready paper + marking key.</p></div>';
    el.classList.add('active');el.scrollIntoView({behavior:'smooth'});
  }catch(err){el.innerHTML='<div class="card"><p class="status err" style="display:block">Upgrade failed: '+esc(err.message)+'</p></div>'}
}
function upgradeFromAim(){
  if(AIM.test){LAST_DOC=AIM.test;upgradeTest('aim-result')}
  else if(LAST_DOC){upgradeTest('aim-result')}
  else{const s=$('aim-test-status');s.className='status err';s.textContent='Add the test first (step 1).'}
}

/* ---------- cloud marking: test + key + scans → judgements ---------- */
const AIM={test:null,key:null,scans:[]};
const MARK_SCHEMA={type:'object',properties:{
  student_label:{type:'string'},
  judgements:{type:'array',items:{type:'object',properties:{
    question:{type:'string'},marks_awarded:{type:'number'},marks_available:{type:'number'},
    transcription:{type:'string'},evidence:{type:'string'},feedback:{type:'string'},
    confidence:{type:'number'},needs_review:{type:'boolean'},review_reason:{type:['string','null']}},
    required:['question','marks_awarded','marks_available','transcription','evidence','feedback','confidence','needs_review','review_reason'],
    additionalProperties:false}}},
  required:['student_label','judgements'],additionalProperties:false};
function aimOk(id){$(id.replace('-input','')).classList.add('ok')}
function b64(buf){let s='';const u=new Uint8Array(buf);
  for(let i=0;i<u.length;i+=32768)s+=String.fromCharCode.apply(null,u.subarray(i,i+32768));
  return btoa(s)}
async function fileBlock(f){
  const data=b64(await f.arrayBuffer());
  if(/\.pdf$/i.test(f.name))
    return {type:'document',source:{type:'base64',media_type:'application/pdf',data}};
  const mt=/\.png$/i.test(f.name)?'image/png':/\.webp$/i.test(f.name)?'image/webp':
    /\.gif$/i.test(f.name)?'image/gif':'image/jpeg';
  return {type:'image',source:{type:'base64',media_type:mt,data}};
}
wireDrop('drop-aim-test','aim-test-input',async f=>{
  const s=$('aim-test-status');
  try{AIM.test={name:f.name,text:await docText(f.name,await f.arrayBuffer())};
    if(!AIM.test.text.trim())throw new Error('no readable text');
    s.className='status';s.textContent='✓ '+f.name;aimOk('drop-aim-test');
  }catch(e){AIM.test=null;s.className='status err';s.textContent=e.message}
});
wireDrop('drop-aim-key','aim-key-input',async f=>{
  const s=$('aim-key-status');
  try{AIM.key={name:f.name,text:await docText(f.name,await f.arrayBuffer())};
    if(!AIM.key.text.trim())throw new Error('no readable text');
    s.className='status';s.textContent='✓ '+f.name;aimOk('drop-aim-key');
  }catch(e){AIM.key=null;s.className='status err';s.textContent=e.message}
});
(function(){
  // scans box takes multiple files, so it gets its own wiring
  const input=$('aim-scans-input'),drop=$('drop-aim-scans');
  if(!input)return;
  function add(files){
    for(const f of files)AIM.scans.push(f);
    const s=$('aim-scans-status');s.className='status';
    s.textContent='✓ '+AIM.scans.length+' script(s) ready.';
    if(AIM.scans.length)aimOk('drop-aim-scans');
  }
  input.addEventListener('change',e=>add(e.target.files));
  ['dragover','dragenter'].forEach(ev=>drop.addEventListener(ev,e=>{e.preventDefault();drop.classList.add('drag')}));
  ['dragleave','dragend','drop'].forEach(ev=>drop.addEventListener(ev,e=>{e.preventDefault();drop.classList.remove('drag')}));
  drop.addEventListener('drop',e=>add(e.dataTransfer.files));
})();
const MARK_SYS_PREFIX='You are marking scanned student scripts for a paper-based school assessment.\n'+
  'You will see one student\'s scanned script (images or a PDF). Mark EVERY question strictly\n'+
  'against the answer key below. Transcribe what the student wrote so transcription errors are\n'+
  'visible, cite evidence for the marks you award, and write one sentence of warm, specific\n'+
  'feedback per question. If a response is illegible, blank, or ambiguous, set needs_review=true\n'+
  'and award conservatively — never guess. If the script shows a student name or ID, report it\n'+
  'as student_label; otherwise use the filename.\n\n';
async function markScans(){
  const el=$('aim-result');
  if(!AIM.test||!AIM.key||!AIM.scans.length){
    el.innerHTML='<div class="card"><p class="status err" style="display:block">Add all three: the test (1), the answer key (2) and at least one scanned script (3).</p></div>';
    el.classList.add('active');return}
  if(!needKey())return;
  const sys=MARK_SYS_PREFIX+'=== THE TEST ===\n'+AIM.test.text+'\n\n=== THE ANSWER KEY ===\n'+AIM.key.text;
  const results=[];
  for(let i=0;i<AIM.scans.length;i++){
    const f=AIM.scans[i];
    busy(el,'Marking script '+(i+1)+' of '+AIM.scans.length+' with '+provName()+' — '+f.name+' …');
    try{
      const out=await callAI({system:sys,schema:MARK_SCHEMA,
        content:[await fileBlock(f),{type:'text',text:'Mark this script. Filename: '+f.name}]});
      out._file=f.name;results.push(out);
    }catch(err){results.push({student_label:f.name,_file:f.name,_error:err.message,judgements:[]})}
  }
  renderMarks(el,results);
}
function renderMarks(el,results){
  let csv='student,question,marks_awarded,marks_available,confidence,needs_review,feedback\n';
  let cards='';
  results.forEach(r=>{
    if(r._error){cards+='<div class="card"><h3>'+esc(r.student_label)+'</h3>'+
      '<p class="status err" style="display:block">Failed: '+esc(r._error)+'</p></div>';return}
    let aw=0,av=0,review=0,rows='';
    r.judgements.forEach(j=>{
      aw+=j.marks_awarded;av+=j.marks_available;if(j.needs_review)review++;
      csv+=[JSON.stringify(r.student_label),JSON.stringify(j.question),j.marks_awarded,j.marks_available,
        j.confidence,j.needs_review,JSON.stringify(j.feedback||'')].join(',')+'\n';
      rows+='<tr><td><b>'+esc(j.question)+'</b>'+(j.needs_review?' <span class="chip review" title="'+esc(j.review_reason||'')+'">review</span>':'')+'</td>'+
        '<td class="num">'+j.marks_awarded+' / '+j.marks_available+'</td>'+
        '<td class="num">'+Math.round(j.confidence*100)+'%</td>'+
        '<td>'+esc(j.transcription||'')+'</td><td>'+esc(j.feedback||'')+'</td></tr>';
    });
    const pct=av?Math.round(100*aw/av):0;
    cards+='<div class="card"><h3>'+esc(r.student_label)+' <span class="muted">('+esc(r._file)+')</span></h3>'+
      '<p><span class="mark-total">'+aw+' / '+av+'</span> <span class="muted">('+pct+'%)</span>'+
      (review?' · <span class="chip review">'+review+' item(s) for your review</span>':'')+'</p>'+
      '<div class="mx"><table class="marks"><tr><th>Q</th><th>Marks</th><th>Conf.</th><th>Transcription</th><th>Feedback</th></tr>'+
      rows+'</table></div></div>';
  });
  el.innerHTML='<h2 class="section">Marking results</h2>'+
    '<div class="aim-actions">'+dlButton('⬇ Download marks (.csv)',csv,'marks.csv','text/csv')+'</div>'+cards+
    '<p class="foot">AI-proposed marks — items flagged “review” need your judgement. You remain the marker of record.</p>';
  el.classList.add('active');el.scrollIntoView({behavior:'smooth'});
}
/* ---------- client-side exporters: markdown → .docx / .pdf (no libraries) ---------- */
const CRC_T=(()=>{const t=new Uint32Array(256);for(let n=0;n<256;n++){let c=n;
  for(let k=0;k<8;k++)c=c&1?0xEDB88320^(c>>>1):c>>>1;t[n]=c}return t})();
function crc32(u8){let c=0xFFFFFFFF;for(let i=0;i<u8.length;i++)c=CRC_T[(c^u8[i])&255]^(c>>>8);
  return (c^0xFFFFFFFF)>>>0}
function makeZip(files){ // [[name, Uint8Array], …] → stored (method 0) ZIP
  const enc=new TextEncoder();const parts=[];const cd=[];let off=0;
  function u16(v){return [v&255,(v>>8)&255]} function u32(v){return [v&255,(v>>8)&255,(v>>16)&255,(v>>>24)&255]}
  for(const [name,data] of files){
    const n=enc.encode(name),crc=crc32(data);
    const lh=new Uint8Array([0x50,0x4b,3,4,...u16(20),...u16(0),...u16(0),...u16(0),...u16(0),
      ...u32(crc),...u32(data.length),...u32(data.length),...u16(n.length),...u16(0)]);
    parts.push(lh,n,data);
    cd.push({n,crc,size:data.length,off});
    off+=lh.length+n.length+data.length;
  }
  const cdParts=[];let cdLen=0;
  for(const e of cd){
    const h=new Uint8Array([0x50,0x4b,1,2,...u16(20),...u16(20),...u16(0),...u16(0),...u16(0),...u16(0),
      ...u32(e.crc),...u32(e.size),...u32(e.size),...u16(e.n.length),...u16(0),...u16(0),
      ...u16(0),...u16(0),...u32(0),...u32(e.off)]);
    cdParts.push(h,e.n);cdLen+=h.length+e.n.length;
  }
  const eocd=new Uint8Array([0x50,0x4b,5,6,...u16(0),...u16(0),...u16(cd.length),...u16(cd.length),
    ...u32(cdLen),...u32(off),...u16(0)]);
  const total=[...parts,...cdParts,eocd];
  const out=new Uint8Array(total.reduce((a,p)=>a+p.length,0));
  let p=0;for(const part of total){out.set(part,p);p+=part.length}
  return out;
}
function xmlEsc(s){return s.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;')}
function mdToDocx(md){ // one paragraph per line; #/## headings bold + larger
  const paras=md.split('\n').map(line=>{
    const h1=/^#\s+/.test(line),h2=/^##\s+/.test(line);
    const text=xmlEsc(line.replace(/^#{1,3}\s+/,''));
    const rpr=h1?'<w:rPr><w:b/><w:sz w:val="36"/></w:rPr>':h2?'<w:rPr><w:b/><w:sz w:val="28"/></w:rPr>':'';
    return '<w:p><w:r>'+rpr+'<w:t xml:space="preserve">'+text+'</w:t></w:r></w:p>';
  }).join('');
  const doc='<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'+
    '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'+
    '<w:body>'+paras+'</w:body></w:document>';
  const ct='<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'+
    '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'+
    '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'+
    '<Default Extension="xml" ContentType="application/xml"/>'+
    '<Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/></Types>';
  const rels='<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'+
    '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'+
    '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/></Relationships>';
  const enc=new TextEncoder();
  return makeZip([['[Content_Types].xml',enc.encode(ct)],['_rels/.rels',enc.encode(rels)],
    ['word/document.xml',enc.encode(doc)]]);
}
function pdfSan(s){ // standard-font safe: swap common unicode for ASCII, escape PDF specials
  return s.replace(/[—–]/g,'-').replace(/[’‘]/g,"'").replace(/[“”]/g,'"').replace(/[→]/g,'->')
    .replace(/[×]/g,'x').replace(/[≥]/g,'>=').replace(/[≤]/g,'<=').replace(/[·•]/g,'*')
    .replace(/[^\x20-\x7e]/g,'?').replace(/\\/g,'\\\\').replace(/\(/g,'\\(').replace(/\)/g,'\\)');
}
function mdToPdf(md){ // minimal text PDF: A4, Helvetica, bold headings, wrapped lines
  const raw=[];
  md.split('\n').forEach(line=>{
    const head=/^#{1,3}\s+/.test(line);
    let t=line.replace(/^#{1,3}\s+/,'');
    if(!t){raw.push({t:'',head:false});return}
    while(t.length>92){let cut=t.lastIndexOf(' ',92);if(cut<40)cut=92;
      raw.push({t:t.slice(0,cut),head});t=t.slice(cut).replace(/^ /,'')}
    raw.push({t,head});
  });
  const perPage=46;const pages=[];
  for(let i=0;i<raw.length;i+=perPage)pages.push(raw.slice(i,i+perPage));
  if(!pages.length)pages.push([{t:'',head:false}]);
  const objs=[];  // 1:catalog 2:pages 3:F1 4:F2 then per page: page,content
  const pageIds=pages.map((_,i)=>5+i*2);
  objs[1]='<< /Type /Catalog /Pages 2 0 R >>';
  objs[2]='<< /Type /Pages /Kids ['+pageIds.map(i=>i+' 0 R').join(' ')+'] /Count '+pages.length+' >>';
  objs[3]='<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>';
  objs[4]='<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica-Bold >>';
  pages.forEach((pl,i)=>{
    let s='BT /F1 10 Tf 14 TL 56 800 Td\n';let bold=false;
    pl.forEach(l=>{
      if(l.head!==bold){s+=l.head?'/F2 13 Tf\n':'/F1 10 Tf\n';bold=l.head}
      s+='('+pdfSan(l.t)+') Tj T*\n';
    });
    s+='ET';
    objs[5+i*2]='<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] '+
      '/Resources << /Font << /F1 3 0 R /F2 4 0 R >> >> /Contents '+(6+i*2)+' 0 R >>';
    objs[6+i*2]='<< /Length '+s.length+' >>\nstream\n'+s+'\nendstream';
  });
  let out='%PDF-1.4\n';const xref=[0];
  for(let i=1;i<objs.length;i++){xref[i]=out.length;out+=i+' 0 obj\n'+objs[i]+'\nendobj\n'}
  const startx=out.length;
  out+='xref\n0 '+objs.length+'\n0000000000 65535 f \n';
  for(let i=1;i<objs.length;i++)out+=String(xref[i]).padStart(10,'0')+' 00000 n \n';
  out+='trailer\n<< /Size '+objs.length+' /Root 1 0 R >>\nstartxref\n'+startx+'\n%%EOF';
  return new TextEncoder().encode(out);
}

/* ---------- assessment optimiser: readiness → optimise → before/after ---------- */
let OPT_DOC=null,OPT_OUT=null;
const OPT_FMTS={md:['Markdown (.md) — ready for markable ingest','text/markdown','.md'],
  docx:['Word (.docx)','application/vnd.openxmlformats-officedocument.wordprocessingml.document','.docx'],
  pdf:['PDF (.pdf)','application/pdf','.pdf']};
function fmtSelector(){return '<select id="opt-fmt" class="picker" style="margin:0">'+
  Object.keys(OPT_FMTS).map(k=>'<option value="'+k+'">'+esc(OPT_FMTS[k][0])+'</option>').join('')+'</select>'}
function downloadOpt(){
  if(!OPT_OUT)return;
  const fmt=($('opt-fmt')&&$('opt-fmt').value)||'md';
  const [_,mime,ext]=OPT_FMTS[fmt];
  const data=fmt==='docx'?mdToDocx(OPT_OUT.md):fmt==='pdf'?mdToPdf(OPT_OUT.md):OPT_OUT.md;
  const a=document.createElement('a');
  a.href=URL.createObjectURL(new Blob([data],{type:mime}));
  a.download=OPT_OUT.base+ext;a.click();setTimeout(()=>URL.revokeObjectURL(a.href),2000);
}
function gauge(score){return '<div class="gauge" style="--v:'+score+'"><span>'+score+'%</span></div>'}
wireDrop('drop-opt','drop-opt-input',async file=>{
  const st=$('opt-status');st.className='status';st.textContent='Checking '+file.name+' …';
  try{
    const text=await docText(file.name,await file.arrayBuffer());
    if(!text.trim())throw new Error('No readable text found in that document.');
    OPT_DOC={name:file.name,text};
    const rep=analyseReadiness(text);
    OPT_DOC.before=rep.score;
    const items=rep.checks.map(c=>'<li class="'+(c[1]?'li-good':'li-warn')+'">'+
      '<b>'+esc(c[0])+'</b> — '+esc(c[1]?c[2]:c[3])+'</li>').join('');
    $('opt-result').innerHTML='<h2 class="section">Step 2 — readiness check</h2>'+
      '<div class="card"><div class="readiness">'+gauge(rep.score)+
      '<div><p style="margin:0 0 6px"><b>'+esc(file.name)+'</b> — '+rep.questions+' questions found, '+
      rep.withMarks+' with marks allocated.</p>'+
      '<p style="margin:0;color:var(--ink-2);font-size:13px">The optimiser fixes the items below while preserving your questions, difficulty and topics.</p></div></div>'+
      '<ul style="margin:0 0 14px;padding-left:2px;list-style:none;line-height:1.9">'+items+'</ul>'+
      '<div class="aim-actions"><button class="btn" onclick="optimiseNow()">✨ Optimise with <span class="prov-name">'+esc(provName())+'</span></button>'+
      '<button class="btn ghost" onclick="show(\'aimark\');scrollToEl(\'prov-claude\')">Switch AI (Claude / Copilot)</button></div></div>';
    $('opt-result').classList.add('active');
    st.textContent='✓ Readiness '+rep.score+'% — ready to optimise.';
    $('opt-result').scrollIntoView({behavior:'smooth'});
  }catch(err){st.className='status err';st.textContent='Could not read that file: '+err.message}
});
async function optimiseNow(){
  if(!OPT_DOC){scrollToEl('drop-opt');return}
  if(!needKey()){show('aimark');return}
  const el=$('opt-result');busy(el,'Optimising “'+OPT_DOC.name+'” with '+provName()+'…');
  try{
    const out=await callAI({system:IMPROVE_PACK,schema:IMPROVE_SCHEMA,
      content:[{type:'text',text:'Upgrade this draft test:\n\n'+OPT_DOC.text}]});
    const after=analyseReadiness(out.improved_markdown).score;
    const changes=(out.changes||[]).map(c=>'<li><b>'+esc(c.question_id)+'</b> — '+esc(c.change)+
      ' <span class="muted">('+esc(c.reason)+')</span></li>').join('');
    OPT_OUT={md:out.improved_markdown,base:OPT_DOC.name.replace(/\.[^.]+$/,'')+'.optimised'};
    el.innerHTML='<h2 class="section">Step 4 — optimised assessment</h2>'+
      '<div class="card">'+
      '<div class="beforeafter"><div class="ba"><span class="lbl">Before</span>'+gauge(OPT_DOC.before)+'</div>'+
      '<span class="ba-arrow">→</span>'+
      '<div class="ba"><span class="lbl">After</span>'+gauge(after)+'</div>'+
      '<p style="margin:0;max-width:420px">'+esc(out.summary||'')+'</p></div>'+
      '<div class="aim-actions">'+fmtSelector()+
      '<button class="btn" onclick="downloadOpt()">⬇ Download optimised test</button>'+
      '<button class="btn ghost" onclick="show(\'aimark\')">Next: mark scripts against it →</button></div>'+
      '<h3>Every change, logged <span class="muted">(verify anything inferred)</span></h3>'+
      '<ul class="changes">'+changes+'</ul>'+
      '<h3>Preview</h3><pre style="white-space:pre-wrap;background:var(--page);border:1px solid var(--border);border-radius:8px;padding:12px;max-height:420px;overflow:auto">'+
      esc(out.improved_markdown)+'</pre>'+
      '<p class="foot">The after-score is Markable\'s own readiness check re-run on the optimised version. '+
      'For the full pipeline, run <code>markable ingest</code> → <code>markable build</code> on the downloaded file.</p></div>';
    el.classList.add('active');el.scrollIntoView({behavior:'smooth'});
  }catch(err){el.innerHTML='<div class="card"><p class="status err" style="display:block">Optimisation failed: '+esc(err.message)+'</p></div>'}
}
(function(){
  const k=$('api-key');if(k&&getKey())k.value=getKey();
  const ep=$('cp-endpoint'),ck=$('cp-key');
  if(ep)ep.value=getCp().endpoint; if(ck)ck.value=getCp().key;
  setProvider(PROVIDER);
  document.querySelectorAll('.prov-name').forEach(e=>e.textContent=provName());
})();
"""
