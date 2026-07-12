# ARCHITECTURE.md

## The key fact

`markable-all.html` / `dist/markable.html` are **compiled artifacts**, not the
source. The source is a modular Python package that already satisfies
"modular source → self-contained single-file distribution":

```
src/markable/
  models.py            # authoritative Pydantic schemas (Assessment, Key, Manifest, star schema)
  ingest.py            # importer: markdown draft → assessment.yaml
  gradebook.py         # importer: teacher XLSX → Gradebook (CLI twin of the browser parser)
  improve.py           # AI prompts + schema: assessment optimiser (INSTRUCTION_PACK)
  rubric.py            # AI prompts + schema: marking-key drafting (RUBRIC_PACK)
  anon.py              # privacy: alias↔ID pseudonymisation (CLI marking path)
  build/               # deterministic layout → paper.pdf + manifest (scan-ready papers)
  scan/                # CLI-only: deskew, QR match, crop
  mark/                # marking engine + review rules + Anthropic provider + review.html
  report.py, feedback_html.py, dashboard_html.py, standards_html.py,
  gradebook_html.py, analysis.py, powerbi.py        # report generators (single-file HTML/CSV)
  curriculum.py, standards.py, studydesign.py       # curriculum packs + attainment
  studio_html.py       # THE HUB TEMPLATE: page markup + embedded browser engine (JS)
  cli.py               # typer entry points
tests/                 # 93 offline tests (pytest) + Playwright E2E scripts
scripts/build_dist.sh  # → dist/markable.html
```

Mapping to the requested tree: importers = `ingest.py`/`gradebook.py` + the JS
`parseXlsx`/`docText`; providers = `anthropic_marker.py` + JS
`callClaude`/`callOpenAI`; prompts = `improve.py`/`rubric.py` packs; validation
= `mark/_apply_review_rules` + JS `validateResult`/`detectAnswerLeaks`;
privacy = `anon.py` + JS credential/consent layer; exports = report generators
+ JS exporters (`mdToDocx`, `mdToPdf`, `makeZip`, CSV builders).

## Known architectural debt

The browser engine (~2,000 lines of JS) lives inside `studio_html.py` as
Python string literals. It is exercised end-to-end by Playwright but has no
JS-level unit tests. **P1-1**: move it to `src/markable/webapp/*.js`
(app/, importers/, marking/, review/, privacy/, exports/), concatenated by the
build; test with `node --test`. No framework — plain JS is sufficient. Any
third-party parser (P1-2) must be vendored into the bundle, never CDN-loaded.

## Build

```bash
# development
uv sync
uv run pytest                    # full offline suite
uv run markable studio -o markable.html            # hub, sibling-linked reports

# distribution (self-contained single file)
scripts/build_dist.sh            # → dist/markable.html (no embedded reports)
scripts/build_dist.sh <reports-dir>   # → dist/markable.html with reports baked in
```

Downloadable dashboards produced by the hub (`downloadDash`, feedback slips,
review queue, curriculum reports) are themselves single-file and fully
offline; they embed data + rendering code and never reference the network.

## Production architecture: school-managed provider proxy (P2)

For deployment beyond a supervised pilot, replace teacher-held keys with a
school proxy:

```
Browser hub ── HTTPS ──▶ school proxy (per-teacher SSO auth)
                          │  • holds the provider key (never in browsers)
                          │  • enforces endpoint policy + rate/size limits
                          │  • appends to an immutable audit log (who/what/when)
                          │  • strips/blocks detected student identifiers
                          ▼
                    api.anthropic.com / Azure OpenAI
```

The hub already routes every cloud call through two functions
(`callClaude`/`callOpenAI`); pointing them at a proxy is a configuration
change, not a rewrite. Admin controls (allowlists, disable-cloud flag,
retention) live on the proxy.
