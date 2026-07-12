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
    ("📝", "Ingest &amp; Build <span class=\"mode-chip cli\">CLI</span>",
     "Turn a messy Word/markdown draft into a scan-friendly, machine-markable paper "
     "with unique question IDs, answer zones, a per-page QR code and a structured "
     "marking key — the prep that makes AI marking reliable.",
     "CLI: <code>markable ingest draft.md</code> then <code>markable build packages/my-test</code>. "
     "Or drop a draft in the <b>AI-marking readiness</b> box below to see what needs fixing first.",
     "Prep my test", "show('home');scrollToEl('drop-doc');$('drop-doc-input').click()"),
    ("📐", "Rubric Builder",
     "AI-drafts the complete marking key from your test: criteria with marks, accept/reject "
     "lists, MCQ answers with distractor notes, and banded rubrics for extended responses — "
     "editable on the page, exported as key.yaml or a printable rubric.",
     "Open the <b>Rubric builder</b> (left menu, under AI cloud). CLI twin: "
     "<code>markable rubric draft.md</code> → <b>key.yaml</b>.",
     "Build my rubric", "show('rubric')"),
    ("✨", "Assessment Optimiser",
     "Optimise any assessment for AI marking: unique IDs, explicit marks, typed items and "
     "tightened wording — your questions and difficulty preserved, every change logged, "
     "with a before/after readiness score.",
     "Open the <b>Assessment optimiser</b> (left menu, under AI cloud), drop your test in, "
     "and download the optimised version. CLI twin: <code>markable improve draft.docx</code>.",
     "Optimise my assessment", "show('optimise')"),
    ("🖨️", "Scan <span class=\"mode-chip cli\">CLI</span>",
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

# (nav-id, label, target). Files open in an iframe when they sit beside the hub
# (or are baked in via --embed).
_REPORTS = [
    ("sacvce", "VCE — SAC results", "vce_sac_dashboard.html"),
    ("sac710", "Years 7–10 — results", "y7-10_dashboard.html"),
    ("dashboard", "Assessment dashboard", "dashboard.html"),
    ("curriculum", "Curriculum report", "curriculum_report.html"),
    ("analysis", "Test analysis", "test_analysis.html"),
    ("review", "Review queue", "review.html"),
    ("feedback", "Feedback slips", "feedback_slips.html"),
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
      <p>The dashboard and readiness boxes run in your browser — those files are read locally and never leave your computer. Anything under <b>AI cloud</b> is different: it sends content to your chosen AI provider, and always asks you first.</p>
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

/* P0 hardening: chips, consent, warnings, review controls, a11y */
.mode-chip{display:inline-block;vertical-align:middle;font-size:10.5px;font-weight:700;
  letter-spacing:.05em;border-radius:99px;padding:2px 9px;margin-left:6px}
.mode-chip.local{color:#1f7a44;border:1px solid #1f7a44}
.mode-chip.cloud{color:#a15c00;border:1px solid #e79a41}
.mode-chip.cli{color:var(--ink-2);border:1px solid var(--border)}
#consent-overlay{position:fixed;inset:0;background:rgba(8,12,22,.55);z-index:50;
  display:flex;align-items:center;justify-content:center;padding:18px}
.consent{background:var(--surface);color:var(--ink);border-radius:14px;max-width:34rem;
  padding:22px 26px;border:1px solid var(--border);max-height:80vh;overflow:auto}
.consent h3{margin:0 0 8px}
.consent ul{margin:8px 0;padding-left:20px;max-height:180px;overflow:auto}
.consent-warn{background:var(--accent-wash);border-radius:8px;padding:10px 12px;font-size:12.5px}
.warn-banner{background:rgba(231,154,65,.12);border:1px solid #e79a41;border-radius:10px;
  padding:12px 16px;margin-bottom:12px}
.warn-banner ul{margin:6px 0 0;padding-left:20px}
.rev-ctl{display:flex;gap:6px;align-items:center;flex-wrap:wrap;margin-top:6px}
.rev-ctl input[type=number]{width:70px}
.rev-ctl input{padding:6px 8px;border-radius:6px;border:1px solid var(--border);
  background:var(--page);color:var(--ink);font:inherit}
table.marks tr.flag td{background:rgba(231,154,65,.08)}
button:focus-visible,input:focus-visible,select:focus-visible,textarea:focus-visible,a:focus-visible{
  outline:2px solid var(--accent);outline-offset:2px}
#nav-toggle{display:none;position:fixed;top:10px;left:10px;z-index:40;background:var(--nav);
  color:var(--nav-ink);border:1px solid var(--border);border-radius:8px;padding:8px 12px;font:inherit;cursor:pointer}
@media(max-width:880px){
  .app{grid-template-columns:1fr}
  .nav{position:fixed;left:0;top:0;bottom:0;width:min(78vw,280px);transform:translateX(-100%);
    transition:transform .2s;z-index:30}
  .nav.open{transform:none;box-shadow:0 0 40px rgba(0,0,0,.4)}
  #nav-toggle{display:block}
  .main{padding-top:52px}
}
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
.workspaces{display:grid;grid-template-columns:repeat(auto-fit,minmax(240px,1fr));gap:12px;margin:6px 0 8px}
.ws{display:flex;flex-direction:column;gap:4px;text-align:left;cursor:pointer;font:inherit;
  background:var(--surface);border:1px solid var(--border);border-radius:12px;padding:14px 16px;color:var(--ink)}
.ws:hover{border-color:var(--accent)}
.ws span{color:var(--ink-2);font-size:12.5px}
.ws-n{width:24px;height:24px;border-radius:50%;background:var(--accent);color:#fff;font-weight:700;
  font-size:13px;display:flex;align-items:center;justify-content:center}
.scan-list{margin-top:8px;text-align:left}
.scan-item{display:flex;justify-content:space-between;gap:8px;align-items:center;
  border:1px solid var(--border);border-radius:8px;padding:5px 10px;margin-bottom:5px;font-size:12.5px}
.filters button{appearance:none;border:1px solid var(--border);background:var(--surface);color:var(--ink-2);
  border-radius:99px;padding:5px 13px;font:inherit;font-size:12.5px;cursor:pointer;margin-right:4px}
.filters button.on{border-color:var(--accent);color:var(--accent);font-weight:600}
/* assessment optimiser */
.opt-flow{display:flex;gap:10px;align-items:center;flex-wrap:wrap;margin:16px 0 18px}
.opt-step{background:var(--surface);border:1px solid var(--border);border-radius:99px;
  padding:8px 16px 8px 8px;display:flex;gap:8px;align-items:center;font-size:13px;color:var(--ink-2)}
.opt-n{width:24px;height:24px;border-radius:50%;background:var(--accent);color:#fff;font-weight:700;
  font-size:13px;display:flex;align-items:center;justify-content:center}
.opt-arrow{color:var(--muted)}
/* rubric editor */
.rq .sublbl{display:block;margin:10px 0 6px;font-size:12px;color:var(--ink-2);text-transform:uppercase;letter-spacing:.05em}
.crit-row,.band-row{display:flex;gap:8px;margin-bottom:6px;align-items:center}
.crit-row input,.band-row input,.kv-edit input{padding:7px 10px;border-radius:8px;border:1px solid var(--border);
  background:var(--page);color:var(--ink);font:inherit}
.crit-point,.band-desc,.dn-note{flex:1}
.crit-marks{width:64px}
.mini{appearance:none;border:1px solid var(--border);background:var(--surface);color:var(--ink-2);
  border-radius:8px;padding:5px 10px;font:inherit;font-size:12px;cursor:pointer}
.mini.add{margin-top:2px;color:var(--accent);border-color:var(--accent)}
.kv-edit{display:flex;gap:10px;align-items:center;flex-wrap:wrap;margin:8px 0}
.kv-edit label{color:var(--ink-2);font-size:12.5px}
.kv-edit input{flex:1;min-width:140px}
.sum-chip{font-size:12px;font-weight:600;border-radius:99px;padding:2px 10px;margin-left:6px}
.sum-chip.ok{color:var(--accent);border:1px solid var(--accent)}
.sum-chip.bad{color:#a15c00;border:1px solid #e79a41}
.optways{display:grid;grid-template-columns:repeat(auto-fit,minmax(300px,1fr));gap:12px}
.optway{background:var(--page);border:1px solid var(--border);border-radius:12px;padding:14px 16px}
.optway h4{margin:0 0 4px;font-size:14px}
a.btn{text-decoration:none;display:inline-block}
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


def _version() -> str:
    from datetime import date

    try:
        from importlib.metadata import version
        v = version("markable")
    except Exception:
        v = "dev"
    return f"v{v} · built {date.today().isoformat()}"


def render_studio(embedded: dict | None = None) -> str:
    import json

    ramps = {
        "greenLight": _GREEN_LIGHT,
        "greenDark": _GREEN_DARK,
        "heatLight": [b[0] for b in _HEAT],
        "heatDark": [b[2] for b in _HEAT],
    }
    from .improve import IMPROVE_SCHEMA, INSTRUCTION_PACK
    from .rubric import RUBRIC_PACK, RUBRIC_SCHEMA

    ramp_js = (
        "const AI_MODELS={claude:'claude-opus-4-8'};\n"  # model ids in one place
        + "const RAMPS=" + json.dumps(ramps) + ";\n"
        + "const PACKS=" + json.dumps(_packs_payload()) + ";\n"
        + "const STUDIO_CSS=" + json.dumps(_CSS) + ";\n"
        # The CLI (`markable improve` / `markable rubric`) and the in-browser
        # tools send identical instruction packages — one source of truth each.
        + "const IMPROVE_PACK=" + json.dumps(INSTRUCTION_PACK) + ";\n"
        + "const IMPROVE_SCHEMA=" + json.dumps(IMPROVE_SCHEMA) + ";\n"
        + "const RUBRIC_PACK=" + json.dumps(RUBRIC_PACK) + ";\n"
        + "const RUBRIC_SCHEMA=" + json.dumps(RUBRIC_SCHEMA) + ";"
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

  <h2 class="section">Three ways to work</h2>
  <div class="workspaces">
    <button class="ws" onclick="scrollToEl('uploads')">
      <span class="ws-n">1</span><b>Analyse locally</b>
      <span>Marks workbook → dashboards; test → readiness. <span class="mode-chip local">LOCAL</span></span></button>
    <button class="ws" onclick="show('optimise')">
      <span class="ws-n">2</span><b>Build an assessment</b>
      <span>Optimise the paper, draft the marking key. <span class="mode-chip cloud">CLOUD</span></span></button>
    <button class="ws" onclick="show('aimark')">
      <span class="ws-n">3</span><b>Mark &amp; review</b>
      <span>AI proposals → your review → finalised export. <span class="mode-chip cloud">CLOUD</span></span></button>
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
      <h3>Results spreadsheet → dashboard <span class="mode-chip local">LOCAL</span></h3>
      <p>Drop a per-SAC / per-test marks workbook (.xlsx). Markable builds an instant
      dashboard — cohort overview, per-assessment question analysis and every student's trajectory.</p>
      <button class="btn" onclick="document.getElementById('drop-xlsx-input').click()">Choose spreadsheet</button>
      <input id="drop-xlsx-input" type="file" accept=".xlsx" hidden>
      <div class="hint">This box is local: the file is read on your computer and never leaves this page.</div>
      <div class="status" role="status" aria-live="polite" id="xlsx-status"></div>
    </div>

    <div class="drop" id="drop-doc">
      <div class="big">📝</div>
      <h3>Test / assessment → AI-marking readiness <span class="mode-chip local">LOCAL</span></h3>
      <p>Drop a test (.docx, .md or .txt). Markable analyses its structure and reports how
      ready it is for reliable AI marking — and exactly what to fix.</p>
      <button class="btn" onclick="document.getElementById('drop-doc-input').click()">Choose test</button>
      <input id="drop-doc-input" type="file" accept=".docx,.md,.txt,.markdown" hidden>
      <div class="hint">This check is local — the file never leaves this page. (The optional "Reformat with AI" step afterwards is a cloud feature and asks first.)</div>
      <div class="status" role="status" aria-live="polite" id="doc-status"></div>
    </div>
  </div>

  <div class="result" id="xlsx-result"></div>
  <div class="result" id="doc-result"></div>

  <p class="foot">Markable {_version()} · every output is a single self-contained file. Reports generated by the
  command-line tool (dashboard.html, curriculum_report.html, …) appear in the left menu when kept
  beside this page.</p>
</div>
"""

    aimark = """
<div class="view" id="view-aimark">
  <h1>🤖 AI marking studio <span class="mode-chip cloud">CLOUD — sends to your AI provider</span></h1>
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
      <span class="status" id="key-status" role="status" aria-live="polite"></span>
    </div>
    <div class="keyfield" id="keys-copilot" style="display:none">
      <input id="cp-endpoint" type="text" placeholder="paste your chat-completions endpoint URL (Azure OpenAI / gateway)" autocomplete="off" style="width:420px;max-width:100%">
      <input id="cp-key" type="password" placeholder="API key" autocomplete="off">
      <button class="btn ghost" onclick="saveKey()">Save</button>
      <span class="status" id="key-status2" role="status" aria-live="polite"></span>
    </div>
    <div class="keyfield" style="margin-top:8px">
      <label class="hint" style="display:flex;gap:6px;align-items:center;cursor:pointer">
        <input type="checkbox" id="remember-creds"> Remember keys on this device
        (otherwise they last this session only and vanish when the tab closes)</label>
      <button class="btn ghost" onclick="clearCreds()">🗑 Clear keys from this browser</button>
    </div>
    <p class="hint" style="margin:8px 0 0">Keys are sent only to the provider you picked, are never
    written into any exported file, and can be cleared at any time. Custom endpoints must be HTTPS
    and are checked against an allowlist; the destination hostname is shown before anything is sent.</p>
  </div>

  <div class="aim-grid">
    <div class="drop aim-step" id="drop-aim-test">
      <div class="stepnum">1</div><div class="big">📄</div>
      <h3>The test</h3>
      <p>The question paper (.docx, .md or .txt).</p>
      <button class="btn" onclick="$('aim-test-input').click()">Choose test</button>
      <input id="aim-test-input" type="file" accept=".docx,.md,.txt,.markdown" hidden>
      <div class="status" role="status" aria-live="polite" id="aim-test-status"></div>
    </div>
    <div class="drop aim-step" id="drop-aim-key">
      <div class="stepnum">2</div><div class="big">🔑</div>
      <h3>The answer key</h3>
      <p>Marking scheme / answers / rubric (.docx, .md, .txt or .yaml).</p>
      <button class="btn" onclick="$('aim-key-input').click()">Choose answer key</button>
      <input id="aim-key-input" type="file" accept=".docx,.md,.txt,.markdown,.yaml,.yml" hidden>
      <div class="status" role="status" aria-live="polite" id="aim-key-status"></div>
    </div>
    <div class="drop aim-step" id="drop-aim-scans">
      <div class="stepnum">3</div><div class="big">🖨️</div>
      <h3>The scanned scripts</h3>
      <p>Student scripts as images or PDFs — one file per student works best.</p>
      <button class="btn" onclick="$('aim-scans-input').click()">Choose scans</button>
      <input id="aim-scans-input" type="file" accept=".png,.jpg,.jpeg,.webp,.gif,.pdf" multiple hidden>
      <div id="aim-scans-list" class="scan-list"></div>
      <div class="status" role="status" aria-live="polite" id="aim-scans-status"></div>
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
  <h1>✨ Assessment optimiser <span class="mode-chip cloud">CLOUD — sends to your AI provider</span></h1>
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
      <div class="status" role="status" aria-live="polite" id="opt-status"></div>
    </div>
  </div>

  <div class="result" id="opt-result"></div>

  <div class="privacy-note">🔒 The readiness check runs locally. Optimising sends the test
  directly from this browser to the AI provider you chose — nothing in between.</div>
</div>
"""

    rubric_view = """
<div class="view" id="view-rubric">
  <h1>📐 Rubric builder <span class="mode-chip cloud">CLOUD — sends to your AI provider</span></h1>
  <p class="lead">Drop in a test and get back a complete draft marking key: criteria with
  marks for every question, accept/reject lists, MCQ answers with distractor notes, and
  banded rubrics for extended responses. Edit it right here, then export
  <code>key.yaml</code> for the marking pipeline — or a printable rubric for colleagues.</p>

  <div class="uploads" style="grid-template-columns:1fr">
    <div class="drop" id="drop-rub">
      <div class="big">📐</div>
      <h3>Test → draft marking key</h3>
      <p>Drop the test (.docx, .md or .txt). Then generate the key with
      <span class="prov-name">Claude</span>, or get a prompt for your own AI.</p>
      <button class="btn" onclick="$('drop-rub-input').click()">Choose test</button>
      <input id="drop-rub-input" type="file" accept=".docx,.md,.txt,.markdown" hidden>
      <div class="hint">AI setup lives under
        <a href="#" onclick="show('aimark');scrollToEl('prov-claude');return false">Claude / Copilot setup</a>.</div>
      <div class="status" role="status" aria-live="polite" id="rub-status"></div>
    </div>
  </div>

  <div class="result" id="rub-result"></div>

  <div class="privacy-note">🔒 Generating a key sends the test directly from this browser to
  the AI you chose. Every inference is listed for you to verify — you own the final key.</div>
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
<button id="nav-toggle" aria-label="Open menu" aria-expanded="false" onclick="navToggle()">☰ Menu</button>
<div class="app">
  <nav class="nav">
    <div class="brand"><span class="dot">✓</span> Markable</div>
    <button class="nav-item active" data-view="home" onclick="show('home',this)">🏠 Home &amp; tools</button>
    <button class="nav-item" data-view="guide" onclick="show('guide',this)">📘 How to use</button>
    <h4>1 · Analyse (local)</h4>
    <button class="nav-item" onclick="show('home');document.getElementById('drop-xlsx-input').click()">📈 Results → dashboard</button>
    <button class="nav-item" onclick="show('home');document.getElementById('drop-doc-input').click()">📝 Test → AI-marking prep</button>
    <h4>2–3 · Build &amp; mark (AI cloud)</h4>
    <button class="nav-item" data-view="optimise" onclick="show('optimise',this)">✨ Assessment optimiser</button>
    <button class="nav-item" data-view="rubric" onclick="show('rubric',this)">📐 Rubric builder</button>
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
    {rubric_view}
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


# --- Client-side engine: modular source in webapp/*.js, concatenated at build into ONE <script> so declaration hoisting behaves exactly as before. ---
from pathlib import Path as _Path

_WEBAPP = _Path(__file__).parent / "webapp"
_JS_ORDER = [
    "00-pure.js",
    "01-core.js",
    "02-dashboard.js",
    "03-readiness.js",
    "04-cloud.js",
    "05-upgrade.js",
    "06-marking.js",
    "07-exporters.js",
    "08-optimiser.js",
    "09-rubric.js",
    "10-init.js",
]

_JS = "\n".join((_WEBAPP / _n).read_text(encoding="utf-8") for _n in _JS_ORDER)
