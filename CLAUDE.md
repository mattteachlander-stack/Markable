# CLAUDE.md — Markable architecture (authoritative)

Generated from `PROJECT_BRIEF.md` (Draft v1.1). The brief is the *why*; this file
is the *locked-in how*. When they disagree, update this file deliberately — code
should follow it. Read the brief once for context, then work from here.

## What Markable is

A single-user **CLI** that solves the *input* problem for AI marking of
paper-based assessments: it restructures a messy draft into a scan-friendly,
machine-markable paper + a structured marking pack, so scanned scripts can later
be marked reliably and auditably. Three parts, built strictly in order:

- **Part 1 (Phases 1–4):** structure & marking — `ingest` → `build` → `scan` → `mark` → `report`.
- **Part 2 (Phases 5–7):** curriculum intelligence — `curriculum`, `tag`, standards reports.
- **Part 3 (Phases 8–9):** dashboards — local HTML + Power BI export.

**Current status: Part 1 implemented (Phases 1–4 core).** `ingest`, `build`,
`scan`, `mark`, and `report` are all functional. The brief's §11.3 gate ("no
marking code before a physical print/scan round trip") was **explicitly waived
by the project owner on 2026-07-06**; the offline *digital* round trip in
`tests/test_scan_roundtrip.py` (build → rasterize → deskew → QR → crop,
including a 180°-rotated noisy scan) stands in for it. **Still outstanding
before first real class use:** a physical print → photocopy → scanner pass, and
the Phase 2 accuracy validation (≥99% MCQ agreement, ≥95% within-1-mark short
answers) against a hand-marked set. **Part 2 core is now in:** `curriculum
import|list` (structured pack.yaml only; Claude-assisted PDF import still
pending), `tag` (offline keyword-overlap proposals + interactive confirm or
`--map`), and `report --curriculum` (fact_attainment/dim_outcome CSVs + a
single-file `curriculum_report.html`). Part 3 (`report --dashboard`, Power BI)
remains stubbed.

## The pipeline (command contract)

```
markable ingest <draft>   → assessment.yaml                          ✓
markable build  <package> → paper.pdf + key.yaml + manifest.json     ✓
markable scan   <package> <pdfs|imgs> → scripts/<sid>/<qid>.png + scan_report.json  ✓
markable mark   <package> → marks.json + review.html (needs `ai` extra + API key)  ✓
markable report <package> → results/totals/item_analysis.csv + summary.md + export/ ✓
markable curriculum import <pack.yaml> --id <id> | list                    ✓
markable tag    <package> --curriculum <id> [--map tags.yaml]              ✓
markable report <package> --curriculum <id> → curriculum_report.html + CSVs ✓
markable report <package> --dashboard → dashboard.html (Tier 1, electric green) ✓
markable analyse <draft|package> --curriculum <id> → test_analysis.html + CSV ✓
markable gradebook <xlsx> [--study-design <id> --map sacmap.yaml] → sac_dashboard.html ✓
markable studio → markable.html (single-file hub: landing + left nav + upload boxes) ✓
markable powerbi <xlsx> [--study-design <id> --map sacmap.yaml] → tidy star-schema CSVs + guide ✓
```

`powerbi` is the **Tier 2 (§10.2) data cleaner**: it flattens the messy teacher
gradebook into an analysis-ready star schema (`fact_marks`, `fact_student_sac`,
`dim_student/question/assessment/skill`) as tidy CSVs Power BI reads directly,
logs data-quality issues (`data_quality.csv`), and writes `POWER_BI_GUIDE.md`
(load order, relationships, DAX measures, visual-by-visual build steps). No
`.pbit` is fabricated — clean data + guide is the dependable path.

`studio` emits the **hub**: one self-contained HTML landing page (tool cards +
instructions + inline-SVG hero) with a left-nav that opens the generated report
files (kept beside it) in an iframe, and **two client-side upload boxes** that
run with no Python/dev tools — a results `.xlsx` → live dashboard, and a test
`.docx/.md/.txt` → AI-marking readiness analysis. The in-browser engine reads
ZIP members via the built-in `DecompressionStream('deflate-raw')` (no JS
libraries) and ports the gradebook renderer to JS.

`gradebook` is a *marks-already-exist* path (no scanning): it reads a teacher's
per-SAC spreadsheet (question × student grid) and renders a tabbed single-file
dashboard — Overview (cohort + every student across every SAC), one tab per SAC
(question × cohort-quartile analysis), and, with `--study-design`, a Skills &
content tab mapping each SAC question to study-design areas per student (prac
criterion columns auto-map to key science skills; content SACs use a teacher
`--map`). Needs the `xlsx` extra.

`analyse` is the teacher-facing proof of concept: point it at a draft and get a
per-item table (marks · strand/concept area · VCAA/ACARA code · Bloom's level ·
specific skill). Proposals are offline heuristics (keyword overlap + verb
classification); `fixtures/curricula/vc2-science` is a REPRESENTATIVE VC2.0
Science subset — codes must be verified against VCAA before official use.

Each command is independently runnable and reads/writes files in the **Assessment
Package** — there is no daemon and no shared state beyond the package folder.

## Folder conventions

```
src/markable/
  models.py            # AUTHORITATIVE Pydantic schemas for every artifact
  ids.py               # question ids + version_hash
  qr.py                # per-page QR payload {test_id, version_hash, page_number}
  ingest.py            # markdown draft → assessment.yaml (offline, deterministic)
  ingest_ai.py         # .docx/.pdf via Claude — SCAFFOLD ONLY (Phase 1b)
  build/
    __init__.py        # build_package() orchestrator
    layout.py          # deterministic geometry engine (mm) — the crux
    typst_render.py    # layout → paper.typ → paper.pdf (typst pkg)
    keypack.py         # assessment → key.yaml scaffold
    manifest.py        # layout → manifest.json (answer-zone + id-box bboxes)
  scan/
    __init__.py        # scan_package() orchestrator + student-id resolution
    pdfio.py           # PDF/image → grayscale pages (pypdfium2 — no poppler)
    register.py        # fiducial detection + homography deskew onto the mm grid
    qr_read.py         # OpenCV QR decode w/ retry ladder (no system zbar)
    crop.py            # manifest bbox → PNG crops + blank-ink heuristic
  mark/
    __init__.py        # run_mark(): per-question cohort batching + review rules
    anthropic_marker.py# Claude vision marker (`ai` extra) — cached key context,
                       # structured-output judgements, optional Batches API
    review.py          # review.html + review_overrides.yaml scaffold
  report.py            # results/totals/item_analysis CSVs, summary.md,
                       # review-override merge, star-schema export/
  curriculum.py        # pack import/list/load + offline tag proposals + run_tag
  standards.py         # attainment math, fact_attainment/dim_outcome export
  standards_html.py    # single-file curriculum_report.html (semantic-heat
                       # red→amber→green heatmap, official strand labels, tooltips)
  analysis.py          # `analyse`: item → code/Bloom's/skill mapping + HTML/CSV
  dashboard_html.py    # `report --dashboard`: Tier 1 single-file dashboard
                       # (validated electric-green ramp)
  gradebook.py         # read teacher SAC xlsx → Gradebook/SAC/GradeStudent (xlsx extra)
  studydesign.py       # map SAC questions → study-design codes → per-student attainment
  gradebook_html.py    # tabbed single-file SAC dashboard (overview/per-SAC/skills)
  studio_html.py       # `studio`: single-file hub — landing + left nav + client-side
                       # upload boxes (in-browser xlsx→dashboard, doc→readiness)
  powerbi.py           # `powerbi`: clean gradebook → tidy star-schema CSVs + build guide
  cli.py               # typer app wiring all commands

curricula/<pack-id>/   # imported packs: pack.yaml + source_meta.json
                       # (immutable once used — revisions get a new id)

fixtures/
  drafts/y9-chem-test.md              # 6 questions, every type — used by all tests
  curricula/mini-science/pack.yaml    # 10-outcome pack for Part 2 tests
tests/                                 # pytest; no network, no API key required

packages/<test-id>/    # BUILD OUTPUT (gitignored) — the Assessment Package:
  assessment.yaml  key.yaml  paper.typ  paper.pdf  manifest.json  assets/
  scripts/<sid>/<qid>.png   scan_report.json          # written by `scan`
  marks.json  review.html  review_overrides.yaml      # written by `mark`
  results.csv totals.csv item_analysis.csv summary.md # written by `report`
  export/fact_response.csv + dim_*.csv                #   " (star schema, no names)
```

**Data format discipline (brief §5):** YAML for human-edited files
(`assessment.yaml`, `key.yaml`, `pack.yaml`), JSON for machine artifacts
(`manifest.json`), CSV for exports. No SQLite in v1.

## The core architectural decision

`build/layout.py` is a **single deterministic layout engine**. It computes all
page geometry in **millimetres, origin top-left**, and is the *only* place page
coordinates are decided. From that one computation:

- `typst_render.py` emits absolute-positioned Typst (`place(dx, dy)`), and
- `manifest.py` emits the answer-zone bounding boxes.

Because both derive from the same geometry, **the printed zones and the manifest
coordinates agree by construction** — this is what makes `scan`'s per-question
cropping deterministic. Never hand-place an element in Typst without the matching
bbox flowing from `layout`; never write a manifest coordinate that isn't computed
by `layout`.

Registration marks (4 corner fiducials) and the per-page QR are likewise emitted
from `layout` values so deskew + coordinate lock line up with the manifest.

## Authoritative schemas (see `models.py`)

- **`assessment.yaml` → `Assessment`/`Question`** — canonical structured
  assessment; single source of truth. Question ids (`Q07a`) are stable and never
  renumbered. `outcome_codes` on a question is empty until Part 2 `tag`.
- **`key.yaml` → `Key`/`KeyEntry`** — marking pack. `build` writes a *scaffold*
  (criteria placeholders, rubric bands, MCQ correct/distractor slots) for the
  teacher to refine before scanning. `review_threshold` defaults 0.85, 0.9 for
  diagram/extended.
- **`manifest.json` → `Manifest`/`Page`/`Zone`** — per page: registration-mark
  centres, exact QR payload string, and a `BBox` (mm) per answer zone. Numerical
  zones also carry a `final_answer_bbox` (the separated final-answer cell).
- **`pack.yaml` → `CurriculumPack`** — Part 2 curriculum representation. Modelled
  now, unused in Phase 1.
- **Star schema → `FactResponse`, `FactAttainment`, `DimAssessment`,
  `DimQuestion`, `DimStudent`, `DimOutcome`, `DimGrading`** — the BI contract
  (brief §10.1). **A Part 1 commitment:** `report` must write `fact_response` +
  the dims from day one so Parts 2–3 are purely additive. Models exist now;
  population lands in Phase 4.

`version_hash` (`ids.py`) is a short sha256 of the canonical assessment. It goes
in every QR and the manifest, tying a script to the exact paper version and
preventing marking against a revised key (brief §7).

## Guardrails baked into the design

- **Human-in-the-loop:** the tool proposes, the teacher owns. Nothing below
  `review_threshold` is auto-finalised; every mark will link to its evidence crop.
- **Privacy:** scripts are keyed by **student ID, never name**. `DimStudent.name`
  is local-only and never exported; the name join happens at report time from a
  local `class_list.csv`. Shared/BI exports contain no names, scans, or crops.
- **Scope discipline for v1:** no web app, no accounts, no server, no LMS, no
  online testing. Paper in → marks + analysis out.

## Tech stack (as built)

Python ≥3.11, `uv`. Core deps: `typer`+`rich` (CLI), `pydantic` v2 (schemas),
`pyyaml`, `segno` (QR), `typst` (paper compile, no system binary), `pillow`.
Scan-time libs (`pypdf`, `pdf2image`, `opencv`, `pyzbar`) live in the optional
`scan` extra; the Anthropic SDK in the `ai` extra — neither is needed for Phase 1.

The marker was written against the API surface verified on 2026-07-06:
model `claude-opus-4-8`, adaptive thinking, `output_config.format` structured
outputs (assistant prefills are rejected on 4.6+), `cache_control` on the shared
key/rubric system block, and the Message Batches API behind `--batch`. The scan
extra deliberately avoids system libraries: OpenCV's QR detector instead of
pyzbar/zbar, `pypdfium2` instead of pdf2image/poppler.

## Working commands

```bash
uv sync                                              # core + dev (incl. scan libs)
uv run markable ingest fixtures/drafts/y9-chem-test.md -o packages/demo/assessment.yaml -y
uv run markable build packages/demo
uv run markable scan packages/demo scans/*.pdf --id-map ids.yaml   # or interactive
uv run markable mark packages/demo [--batch]         # needs `ai` extra + ANTHROPIC_API_KEY
uv run markable report packages/demo
uv run markable curriculum import fixtures/curricula/mini-science/pack.yaml --id mini-science
uv run markable tag packages/demo --curriculum mini-science        # or --map tags.yaml
uv run markable report packages/demo --curriculum mini-science     # → curriculum_report.html
uv run pytest                                        # full suite, offline, no API key
```

## Conventions for future work

- Extend `models.py` first; treat the YAML/JSON on disk as serialisations of it.
- Any new page element = new geometry in `layout.py` + matching Typst in
  `typst_render.py` + (if it's an answer zone) a `Zone` in `manifest.py`.
- Keep each phase's code behind its command; don't let Part 2+ logic leak into
  Part 1 modules. Remaining stubs raise `typer.Exit(code=2)` via `_phase_stub`.
- Tests must stay offline (no network, no API key). Fixtures drive everything;
  the Anthropic marker is tested via `build_request` shape checks and an
  injectable client, and the scan pipeline via the synthetic digital round trip.
- Review rules live in `mark/__init__.py` (`_apply_review_rules`), not in
  markers — any marker implementation gets thresholds/blank/ambiguity handling
  for free.
