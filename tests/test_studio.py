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
    assert "https://" not in html.split("</title>", 1)[1]


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
