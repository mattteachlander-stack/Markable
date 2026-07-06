# Markable

Assessment preparation, AI-marking, and curriculum-intelligence pipeline for
**paper-based** school assessments. Markable restructures a messy draft into a
scan-friendly, machine-markable paper plus a structured marking pack, so scanned
scripts can later be marked reliably, per-question, and auditably.

> **Status: Phase 1.** `ingest` and `build` work end-to-end. `scan`, `mark`,
> `report`, `curriculum`, and `tag` are stubs. See `PROJECT_BRIEF.md` for the
> full vision and `CLAUDE.md` for the locked-in architecture.

## Install

```bash
uv sync
```

Optional extras (not needed for Phase 1):

```bash
uv sync --extra scan   # pypdf, pdf2image, opencv, pyzbar — for `scan` (Phase 2)
uv sync --extra ai     # anthropic SDK — AI ingestion / marking
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

Print `paper.pdf`, have students sit the test on paper, scan the scripts — then
Phase 2 (`scan` + `mark`) will match and mark them.

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
