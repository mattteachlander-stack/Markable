# Markable

Assessment preparation, AI-marking, and curriculum-intelligence pipeline for
**paper-based** school assessments. Markable restructures a messy draft into a
scan-friendly, machine-markable paper plus a structured marking pack, so scanned
scripts can later be marked reliably, per-question, and auditably.

> **Status: Part 1 implemented.** `ingest`, `build`, `scan`, `mark`, and
> `report` work end-to-end (validated by an offline digital round trip;
> a physical print/scan pass and marking-accuracy validation against a
> hand-marked set are still recommended before first real class use).
> `curriculum` and `tag` (Part 2) are stubs. See `PROJECT_BRIEF.md` for the
> full vision and `CLAUDE.md` for the locked-in architecture.

## Install

```bash
uv sync                # core deps (dev sync includes the scan libraries)
uv sync --extra scan   # opencv + pypdfium2 + pypdf — for `markable scan`
uv sync --extra ai     # anthropic SDK — for `markable mark`
```

## Quick start

```bash
# 1. Parse a draft into the canonical assessment.yaml
uv run markable ingest fixtures/drafts/y9-chem-test.md -o packages/demo/assessment.yaml -y

# 2. Build the print-ready paper + marking pack + manifest
uv run markable build packages/demo

# → packages/demo/
#     assessment.yaml   canonical structure
#     key.yaml          marking-pack scaffold (refine before scanning)
#     paper.typ         Typst source
#     paper.pdf         print-ready student paper (QR + registration marks + zones)
#     manifest.json     exact bbox of every answer zone, per page
#     assets/           per-page QR PNGs
#     scripts/          populated later by `scan`
```

```bash
# 3. Match scanned scripts and crop every answer zone
uv run markable scan packages/demo scans/period3.pdf --id-map ids.yaml
#    (omit --id-map to assign student IDs interactively; any page order,
#     upside-down pages, and photocopier skew are handled automatically)

# 4. AI-mark, per question, against the refined key.yaml
export ANTHROPIC_API_KEY=...   # requires: uv sync --extra ai
uv run markable mark packages/demo --batch
#    → marks.json; anything uncertain lands in review.html — record your final
#      marks in review_overrides.yaml (the teacher always owns the marks)

# 5. Scores, item analysis, teacher summary, BI export
uv run markable report packages/demo
#    → results.csv, totals.csv, item_analysis.csv, summary.md,
#      export/ (star schema: fact_response + dims, student IDs only — no names)

# 6. Curriculum intelligence (Part 2)
uv run markable curriculum import fixtures/curricula/mini-science/pack.yaml --id mini-science
uv run markable tag packages/demo --curriculum mini-science
uv run markable report packages/demo --curriculum mini-science
#    → curriculum_report.html — a single self-contained file (attainment heatmap,
#      strand/dimension rollups, misconceptions, coverage audit) that opens in
#      any browser with no dev tools, plus fact_attainment/dim_outcome CSVs
```

### Draft format

A draft is lightly-structured markdown: a header of `key: value` lines then one
`## <id> [<type>, <marks>]` section per question. Types: `mcq`, `short_answer`,
`numerical`, `extended`, `diagram`. MCQ options are `- A) text` lines; a trailing
`*` marks the correct answer. Omit `marks` and `ingest` asks for it interactively.
See `fixtures/drafts/y9-chem-test.md`.

## Development

```bash
uv run pytest        # full suite — offline, no API key needed
```

The layout engine (`src/markable/build/layout.py`) is the single source of truth
for page geometry: both the printed paper and `manifest.json` derive from it, so
answer-zone coordinates match the page by construction.

## Privacy

Scripts are keyed by **student ID, never name**. Names live only in a local
`class_list.csv` you control and are joined at report time. No student data is
stored anywhere but the local package folder. See `PROJECT_BRIEF.md` §7.
