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
    # the ONLY permitted remote host is Anthropic's API (the teacher-opt-in
    # cloud features); no CDN scripts, fonts, or trackers.
    import re
    hosts = set(re.findall(r"https://([a-z0-9.-]+)", html.split("</title>", 1)[1]))
    assert hosts <= {"api.anthropic.com"}, hosts


def test_has_nav_landing_and_tools():
    html = render_studio()
    # left nav + landing hero
    assert 'class="nav"' in html and "Home &amp; tools" in html
    assert "<svg" in html  # hero graphic
    # every tool card title present
    for title in ("Ingest &amp; Build", "Scan", "Mark", "Report &amp; Dashboard",
                  "Curriculum Report", "Test Analysis", "SAC Gradebook"):
        assert title in html, title
    # report links to the sibling output files
    for f in ("dashboard.html", "sac_dashboard.html", "curriculum_report.html", "test_analysis.html"):
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
    assert "analyseReadiness(out.improved_markdown)" in html
    # export format selector: markdown, Word or PDF — generated client-side
    for el in ("opt-fmt", "downloadOpt", "mdToDocx", "mdToPdf", "makeZip", "crc32",
               "wordprocessingml.document", "application/pdf"):
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
