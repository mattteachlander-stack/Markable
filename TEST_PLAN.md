# TEST_PLAN.md

## Current automated coverage (all offline, no API key)

**Python unit/fixture tests — `uv run pytest` (97 tests, incl. the node-bridge)**
- Ingest/question detection & marks parsing: `test_ingest.py`
- Build determinism, manifest/zone geometry: `test_build.py`, `test_qr.py`
- Scan round trip (rasterise → deskew → QR → crop, incl. 180° noisy scan):
  `test_scan_roundtrip.py`
- Marking engine: cohort batching, blank handling, threshold routing,
  pseudonymisation (marker never sees real IDs): `test_mark_engine.py`,
  `test_anon.py`
- Review queue contract (items JSON, overrides shape merged by report):
  `test_mark_engine.py::test_review_html_is_interactive`, `test_report.py`
- Exports incl. feedback slips honesty rules (pending marks excluded):
  `test_feedback.py`, `test_report.py`, `test_powerbi.py`
- Curriculum states & analysis: `test_curriculum.py`, `test_analysis.py`
- Gradebook importer: `test_gradebook.py`
- AI request shapes + injectable fake clients: `test_improve.py`,
  `test_rubric.py`
- Hub template contracts incl. **all P0 guards** (leak detection, consent,
  credential policy, validation, identity warnings, labelling, a11y hooks):
  `test_studio.py` (17 tests, incl. the live results/feedback views contract)

**Browser E2E — Playwright scripts (scratchpad `pw_*.py`, run against the
built hub in Chromium)**
- `pw_p0.py` (adversarial): legacy-key migration; HTTP endpoint rejection;
  consent shows hostname; cancel sends zero requests; leaky student export
  blocked with cited lines; labelled teacher master; consent lists scan files;
  malformed LLM JSON (marks>max, negative, confidence 1.7, duplicate QID,
  blank transcription) clamped + flagged; export gated until review complete;
  audit CSV columns; duplicate-ID warning banner; mobile hamburger.
- `pw_reports.py`: live results/feedback section — VCE + 7–10 nav entries,
  empty states, labelled demo data (chip clears on real upload), real workbook
  → results view, slips preview/class filter/printable download, CLI-file
  hint bar.
- `pw_ai.py`, `pw_opt.py`, `pw_rubric.py`, `pw_prompt.py`, `pw_review.py`,
  `pw_test.py`: feature E2E for upgrade, optimiser (before/after, docx/pdf
  magic-byte checks), rubric editor (edits → valid Key model), prompt path,
  interactive review queue (decisions → `markable report` merges overrides),
  dashboard parity incl. term toggle.

## Gaps → planned additions

| Area | Fixture/test to add | Priority |
|---|---|---|
| Merged Excel cells, formula-only workbooks, 10k-row sheets | XLSX fixtures via openpyxl; JS parser fixtures once P1-1 lands | P1 |
| DOCX with tables/equations/images | fixture docx asserting DOC_WARNS counts | P1 |
| Malicious filenames / spreadsheet text (HTML injection) | fixture with `<img onerror>` strings in cells; assert escaped rendering | P1 |
| Duplicate students end-to-end in browser | xlsx fixture with same-name/diff-ID rows; assert banner + no merge | P1 |
| Keyboard-only full journey + axe-core | Playwright a11y suite in CI | P1 |
| ~~JS unit tests (node --test)~~ | ✅ `tests/js/pure.test.mjs` (6 tests) | done |
| Gold-dataset eval harness | see AI_MARKING_EVALUATION_PLAN.md | P2 |

## E2E teacher journey (scripted, to run before each pilot build)

1. Upload marks workbook → identity warnings reviewed → dashboard.
2. Upload assessment → readiness → optimise → download STUDENT copy (leak
   check green) + TEACHER master.
3. Rubric builder → edit criteria → export key.yaml (validates against `Key`).
4. Marking studio → consent (hostname + files) → proposals → review flagged →
   override one with reason → export gated → finalised CSV → re-open CSV.
5. Repeat 1–4 at 420 px width and keyboard-only.
