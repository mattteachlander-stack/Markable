# CHANGELOG.md

## Council P0 hardening pass (this release)

### Safety & privacy
- **Answer-leak protection**: optimiser exports split into *Student copy*
  (answer markers stripped, leak detector blocks download and cites offending
  lines) and *Teacher master* (labelled, keeps the `*` markers `markable
  ingest` requires). The reformat flow now labels its output as the teacher
  master and points to the optimiser for student copies.
- **Credential policy**: API keys default to session-only storage; explicit
  "remember on this device" opt-in; legacy localStorage keys migrated; clear-
  keys control; keys never enter exports.
- **Endpoint safety**: custom Copilot/Azure endpoints must be HTTPS and match
  an allowlist (unknown hosts need explicit approval); destination hostname
  shown at save time and before every send.
- **Consent gate**: every cloud action (optimise, reformat, rubric, marking)
  opens a dialog naming the provider, the destination hostname and the exact
  payload (files + sizes), with a student-identifier reminder. Cancel sends
  nothing.
- **Honest labelling**: LOCAL / CLOUD / CLI chips across the hub; the global
  "nothing is uploaded anywhere" claim removed; curriculum auto-mappings
  labelled **SUGGESTED MAPPING**; guide privacy copy rewritten.

### Marking integrity
- **Deterministic validation** independent of the model: marks clamped to
  [0, available] with visible flags, confidence clamped + independent 0.85
  review floor, duplicate question IDs and blank transcriptions flagged;
  model `needs_review` is one input, never the decider.
- **Review → finalise workflow**: accept / override (reason required) / undo
  per flagged item; per-student finalise status; **export locked** until every
  flagged item is decided.
- **Complete audit export**: proposed vs final marks, review flags, teacher
  action, override reason, transcription, evidence, feedback per row.
- Cancel button between scripts; 20 MB per-scan cap; one retry with backoff on
  rate-limit/5xx; model IDs centralised in `AI_MODELS`.

### Data integrity
- Spreadsheet scanning uses real sheet extents (fixed 40/80/120/200 limits
  removed); students keyed by ID when present; same-name students are never
  merged (kept separate, disambiguated by ID); duplicate IDs/rows, missing-ID
  workbooks, marks above maximum and negative marks raise a visible warning
  banner on the dashboard; duplicate question labels deduplicated visibly.
- DOCX extraction reports what it could NOT extract (tables, images,
  equations) on every upload.

### Accessibility & UX
- Collapsible mobile navigation (hamburger, aria-expanded) below 880 px;
  visible keyboard focus (`:focus-visible`) on all controls; upload/processing
  statuses announced via `role="status" aria-live="polite"`; leak warnings via
  `role="alert"`; consent dialog is a focused `role="dialog"`.

### Engineering
- `scripts/build_dist.sh` → self-contained `dist/markable.html`.
- 6 new P0 regression test groups in `test_studio.py` (93 pytest total) plus
  an adversarial Playwright suite (`pw_p0.py`) covering malformed model JSON,
  endpoint attacks, consent cancellation, leak blocking, identity warnings and
  mobile nav.
- Council deliverables: COUNCIL_AUDIT, DECISION_LOG, PRIORITISED_BACKLOG,
  ARCHITECTURE, PRIVACY_AND_DATA_FLOW, AI_MARKING_EVALUATION_PLAN, TEST_PLAN.
