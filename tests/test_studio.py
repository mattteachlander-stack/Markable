"""Studio hub template tests — structure + self-containment (offline).

The client-side upload behaviour is verified separately by driving the page with
a browser; here we guard the template's shape so regressions surface in CI.
"""

from markable.studio_html import render_studio


def test_self_contained_and_structured():
    html = render_studio()
    assert html.startswith("<!DOCTYPE html>")
    # no external resources — everything inline
    assert "<script src" not in html and "<link" not in html
    # the ONLY permitted remote hosts: Anthropic's API (teacher-opt-in cloud
    # features) and plain links to the chat AIs for the no-key prompt path.
    # No CDN scripts, fonts, or trackers.
    import re
    hosts = set(re.findall(r"https://([a-z0-9.-]+)", html.split("</title>", 1)[1]))
    assert hosts <= {"api.anthropic.com", "claude.ai", "chatgpt.com",
                     "copilot.microsoft.com"}, hosts


def test_has_nav_landing_and_tools():
    html = render_studio()
    # left nav + landing hero
    assert 'class="nav"' in html and "Home &amp; tools" in html
    assert "<svg" in html  # hero graphic
    # every tool card title present
    for title in ("Ingest &amp; Build", "Scan", "Mark", "Report &amp; Dashboard",
                  "Curriculum Report", "Test Analysis", "SAC Gradebook"):
        assert title in html, title
    # report links to the sibling CLI output files (results/feedback are live in-browser)
    for f in ("dashboard.html", "curriculum_report.html", "test_analysis.html", "review.html"):
        assert f in html, f


def test_has_working_upload_boxes():
    html = render_studio()
    # two file inputs + drop zones
    assert 'id="drop-xlsx-input"' in html and 'accept=".xlsx"' in html
    assert 'id="drop-doc-input"' in html
    # the client-side engine: zip inflate, xlsx + docx parse, dashboard + readiness
    for fn in ("DecompressionStream", "parseXlsx", "detectSac", "renderDashboard",
               "analyseReadiness", "docText"):
        assert fn in html, fn
    # ramps embedded for the in-browser renderer
    assert "const RAMPS=" in html


def test_tool_cards_have_action_buttons():
    """Every function card carries a button that jumps to the tool doing the job."""
    html = render_studio()
    assert html.count("tool-go") >= 7  # one per tool card
    for js in ("drop-doc-input", "drop-xlsx-input", "show('aimark')",
               "openReportByFile('curriculum_report.html')",
               "openReportByFile('test_analysis.html')"):
        assert js in html, js


def test_ai_cloud_features_present():
    """Upgrade-with-AI + the AI marking studio page (test/key/scans workflow)."""
    html = render_studio()
    # the readiness card offers the AI upgrade; the pack is shared with the CLI
    from markable.improve import INSTRUCTION_PACK
    assert "upgradeTest" in html
    assert "UNIQUE STABLE IDS" in INSTRUCTION_PACK and "IMPROVE_PACK" in html
    # AI marking studio: three-step workflow + key management + direct API calls
    assert 'id="view-aimark"' in html
    for el in ("aim-test-input", "aim-key-input", "aim-scans-input",
               "markScans", "MARK_SCHEMA", "api.anthropic.com",
               "anthropic-dangerous-direct-browser-access"):
        assert el in html, el
    # scans can be images or PDFs (PDF → document block)
    assert "application/pdf" in html
    # provider choice: Claude or the workplace's Copilot/Azure OpenAI endpoint,
    # with logo buttons, per-provider credentials, and an OpenAI-compatible transport
    for el in ("prov-claude", "prov-copilot", "setProvider", "cp-endpoint",
               "callOpenAI", "image_url", "json_object"):
        assert el in html, el


def test_assessment_optimiser_page():
    """A dedicated optimiser tool: upload → local readiness → AI optimise →
    before/after score + change log + download."""
    html = render_studio()
    assert 'id="view-optimise"' in html
    for el in ("drop-opt-input", "optimiseNow", "OPT_DOC", "beforeafter",
               "Assessment optimiser", "Assessment Optimiser"):  # page + tool card
        assert el in html, el
    # it re-scores the optimised output locally for the after-gauge
    assert "analyseReadiness(md).score" in html and "renderOptimised" in html
    # export format selector: markdown, Word or PDF — generated client-side
    for el in ("opt-fmt", "downloadOpt", "mdToDocx", "mdToPdf", "makeZip", "crc32",
               "wordprocessingml.document", "application/pdf"):
        assert el in html, el
    # Option B: no API key — Markable packages a prompt for the teacher's own
    # AI (Claude / ChatGPT / Copilot dropdown), then re-scores the pasted result
    for el in ("chat-ai", "genPrompt", "buildChatPrompt", "copyPrompt", "pasteBack",
               "claude.ai", "chatgpt.com", "copilot.microsoft.com",
               "THE DRAFT TEST", "paste-back"):
        assert el in html, el


def test_p0_credential_safety():
    """Keys default to session-only storage; custom endpoints are HTTPS +
    allowlist validated; clear-credential control exists; destination shown."""
    html = render_studio()
    for el in ("sessionStorage", "credStore", "rememberOn", "migrateLegacyCreds",
               "clearCreds", "remember-creds", "validateEndpoint",
               "Endpoint must use HTTPS", "DEFAULT_HOST_SUFFIXES", "endpointHost"):
        assert el in html, el


def test_p0_consent_and_transport():
    """Every cloud send is gated by an explicit consent dialog naming the
    destination host; transport retries once on rate-limit/5xx."""
    html = render_studio()
    for el in ("cloudConsent", "consent-overlay", "cloudDestination",
               "Nothing is sent until you confirm", "CLOUD_CANCEL", "AI_MODELS"):
        assert el in html, el
    # all three cloud actions are gated
    assert html.count("await cloudConsent(") >= 3


def test_p0_marking_validation_and_review():
    """Deterministic validation independent of the model's flags, plus a
    review→finalise workflow that gates the export."""
    html = render_studio()
    for el in ("validateResult", "REVIEW_CONF", "clamped", "j._review",
               "mAccept", "mOverride", "override_reason", "paintMarks",
               "exportMarks", "proposed_marks,final_marks", "MAX_SCAN_MB"):
        assert el in html, el


def test_p0_answer_leak_protection():
    """Student exports strip answer markers and are blocked if leaks remain;
    teacher master is labelled."""
    html = render_studio()
    for el in ("stripAnswerMarkers", "detectAnswerLeaks", "leak-box",
               "STUDENT COPY", "TEACHER MASTER", "opt-aud",
               "Student download blocked"):
        assert el in html, el


def test_p0_data_identity_and_import_warnings():
    """Dynamic sheet bounds, ID-based identity, duplicate detection, marks
    range checks — all surfaced in a visible banner, never silent."""
    html = render_studio()
    for el in ("gridExtents", "warn-banner", "Duplicate student ID",
               "kept separate using their IDs", "exceeds the /",
               "No ID column found", "Duplicate question label"):
        assert el in html, el
    # DOCX honest-extraction warnings
    for el in ("DOC_WARNS", "NOT extracted", "docWarnSuffix"):
        assert el in html, el


def test_p0_labelling_and_a11y():
    """LOCAL/CLOUD/CLI chips, scoped privacy copy, aria-live statuses,
    focus-visible, mobile nav."""
    html = render_studio()
    assert html.count("mode-chip") >= 6
    assert "Nothing is uploaded anywhere" not in html  # replaced by scoped copy
    assert 'role="status" aria-live="polite"' in html
    assert "focus-visible" in html and "nav-toggle" in html and "aria-expanded" in html
    assert "SUGGESTED MAPPING" in html  # curriculum mappings labelled as proposals


def test_p1_pilot_quality_features():
    """P1: structured-key reconciliation, mapping states, review filters +
    bulk accept, scans list management, modal keys, small-n caveat,
    three-workspace IA, version stamp, modular JS source."""
    html = render_studio()
    for el in ("parseKeyYaml", "AIM.structKey", "reconciliation",
               "missing from the AI response", "not in the marking key",
               "useKeyInMarking",                       # rubric → marking hand-off
               "autoAreaScored", "ambiguous",           # mapping states
               "setMFilter", "mAcceptAll",              # review filters + bulk
               "aim-scans-list", "rmScan",              # scans management
               "Escape",                                # modal esc
               "small cohort n=",                       # small-n caveat
               "workspaces", "Analyse locally", "Mark &amp; review",
               "built 20"):                             # version stamp
        assert el in html, el


def test_live_results_and_feedback_views():
    """The results dashboards (VCE SACs / Years 7-10) and feedback slips render
    live in-browser — the standalone hub must not depend on sibling report
    files for them, and the demo data must be labelled as fictional."""
    html = render_studio()
    # live views + entry points
    for el in ('id="view-results"', 'id="view-feedback"', 'id="results-empty"',
               'id="fb-body"', "showResults('SAC'", "showResults('Assessment'",
               "showFeedback(", "loadDemo(", "demoSacs", "renderFeedback",
               "downloadSlips", "slipHtml"):
        assert el in html, el
    # demo data is honest: chip + fictional label, deterministic generator
    assert "DEMO DATA" in html and "fictional students" in html
    assert "demoRand" in html
    # the old sibling-file targets are gone from the report links
    for stale in ("vce_sac_dashboard.html", "y7-10_dashboard.html",
                  "feedback_slips.html"):
        assert stale not in html, stale
    # remaining CLI file links carry the honest hint bar
    assert "frame-hint" in html
    # slips privacy + print contract
    assert "Generated locally by Markable" in html
    assert "page-break-after" in html


def test_js_source_is_modular():
    from pathlib import Path as _P
    webapp = _P(__file__).resolve().parents[1] / "src" / "markable" / "webapp"
    files = sorted(f.name for f in webapp.glob("*.js"))
    assert "00-pure.js" in files and len(files) >= 10
    # pure module carries the node export guard
    assert "module.exports" in (webapp / "00-pure.js").read_text(encoding="utf-8")


def test_rubric_builder_page():
    """Rubric builder: test → AI-drafted key → editable UI → key.yaml /
    printable export, plus the no-key prompt path."""
    html = render_studio()
    assert 'id="view-rubric"' in html
    for el in ("drop-rub-input", "genRubric", "renderRubricEditor", "collectRubric",
               "keyYaml", "downloadKeyYaml", "downloadRubricDoc", "sumCheck",
               "RUBRIC_PACK", "RUBRIC_SCHEMA", "genRubricPrompt", "rubricPasteBack",
               "Rubric Builder"):  # page + tool card
        assert el in html, el
    # editable controls: criteria rows, distractor notes, bands, accept/reject
    for el in ("crit-point", "crit-marks", "dn-note", "band-row", "-accept", "-reject"):
        assert el in html, el


def test_in_browser_dashboard_has_gradebook_parity():
    """The uploader engine mirrors render_gradebook: term toggle, key highlights,
    class-question analysis and a student spotlight — not just the basic tabs."""
    html = render_studio()
    for fn in ("highlightsCard", "classesTab", "renderClassQ", "studentTab",
               "renderSpot", "qmetaFor", "reRenderDash"):
        assert fn in html, fn
    # VCE (SAC) / Years 7–10 (Assessment) level toggle wording
    assert "VCE (SACs)" in html and "Years 7–10 (Assessments)" in html
    assert "LAST_TERM" in html
    # a dragged-in openpyxl workbook uses absolute rels targets (/xl/…) — the
    # path resolver must not double the xl/ prefix
    assert "tgt.startsWith('/')" in html
    # the downloaded dashboard bakes its own runtime so its selects stay live
    assert "f.toString()" in html
