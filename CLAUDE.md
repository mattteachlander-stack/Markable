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

**Current status: Phase 1 only.** `ingest` and `build` are implemented. Everything
else is a CLI stub that names its phase and exits non-zero. **Do not write any
marking (`mark`) or scanning (`scan`) code until the Phase 1 print/scan round trip
is validated** (brief §11.3).

## The pipeline (command contract)

```
markable ingest <draft>   → assessment.yaml        (Phase 1 ✓)
markable build  <package> → paper.pdf + key.yaml + manifest.json   (Phase 1 ✓)
markable scan   <package> <pdfs>                    (Phase 2 — stub)
markable mark   <package>                           (Phase 2/3 — stub)
markable report <package>                           (Phase 4 — stub)
markable tag        <package> --curriculum <id>     (Phase 5 — stub)
markable curriculum import|list                     (Phase 5 — stub)
```

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
    manifest.py        # layout → manifest.json (answer-zone bboxes)
  cli.py               # typer app wiring all commands

fixtures/
  drafts/y9-chem-test.md              # 6 questions, every type — used by all tests
  curricula/mini-science/pack.yaml    # 10-outcome pack for Part 2 tests
tests/                                 # pytest; no network, no API key required

packages/<test-id>/    # BUILD OUTPUT (gitignored) — the Assessment Package:
  assessment.yaml  key.yaml  paper.typ  paper.pdf  manifest.json  assets/  scripts/
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

External specifics to re-verify at build time against
<https://docs.claude.com/en/api/overview> before writing `mark`: current model
names, vision inputs, prompt caching, and the batch API.

## Working commands

```bash
uv sync                                              # install (core deps)
uv run markable ingest fixtures/drafts/y9-chem-test.md -o /tmp/assessment.yaml -y
uv run markable build packages/2026-T3-Y9-chem -a /tmp/assessment.yaml
uv run pytest                                        # full suite, offline
```

## Conventions for future work

- Extend `models.py` first; treat the YAML/JSON on disk as serialisations of it.
- Any new page element = new geometry in `layout.py` + matching Typst in
  `typst_render.py` + (if it's an answer zone) a `Zone` in `manifest.py`.
- Keep each phase's code behind its command; don't let Phase 2+ logic leak into
  Phase 1 modules. Stubs raise `typer.Exit(code=2)` via `_phase_stub`.
- Tests must stay offline (no network, no API key). Fixtures drive everything.
