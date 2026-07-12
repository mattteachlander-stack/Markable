# PRIORITISED_BACKLOG.md

Status legend: ✅ done in this pass · ▶ open.

## P0 — must fix before any teacher pilot (ALL ✅ this pass)

| # | Problem | Solution shipped | Files | Cx | Acceptance criteria | Tests |
|---|---------|------------------|-------|----|---------------------|-------|
| P0-1 ✅ | Optimised test leaked MCQ answers (`*` marker) into printable exports | Student/teacher export split; `stripAnswerMarkers`; `detectAnswerLeaks` blocks student download and cites lines; labelled filenames + in-document headers | `studio_html.py` (optimiser JS) | M | Student export with any answer indicator is blocked with cited lines; teacher master labelled `TEACHER-MASTER` | `test_p0_answer_leak_protection`; `pw_p0.py` (leak block + labelled download) |
| P0-2 ✅ | AI review flags trusted; marks/confidence unvalidated | `validateResult()`: range clamps (flagged), independent 0.85 confidence floor, duplicate-QID + blank-transcription flags; totals computed deterministically | `studio_html.py` | M | `5/1` renders as clamped `1/1` + review flag; model `needs_review:false` cannot suppress review | `test_p0_marking_validation_and_review`; `pw_p0.py` (BAD_MARK payload) |
| P0-3 ✅ | No accept/edit/override/finalise; export incomplete | Review controls per flagged item (accept / override + required reason / undo), per-student finalise chip, export locked until resolved; 14-column audit CSV (proposed vs final, flags, action, reason, transcription, evidence) | `studio_html.py` | M–H | Export button disabled while any flagged item undecided; CSV contains full audit trail | same as P0-2 |
| P0-4 ✅ | Keys persisted forever in localStorage | Session-only default, remember-on-device opt-in, legacy migration, clear-keys control, never in exports | `studio_html.py` | S | Fresh key + closed tab ⇒ key gone; legacy localStorage key auto-migrates | `test_p0_credential_safety`; `pw_p0.py` (migration) |
| P0-5 ✅ | Arbitrary/HTTP endpoints could receive the key | `validateEndpoint`: HTTPS required, Azure/OpenAI allowlist, confirm-to-add others, hostname shown at save + in consent | `studio_html.py` | S | `http://` rejected; unknown host requires explicit approval | `pw_p0.py` (http rejected) |
| P0-6 ✅ | Cloud sends without consent; local/cloud copy conflated | `cloudConsent()` modal on all four cloud actions (provider, hostname, itemised payload, PII reminder, cancel); LOCAL/CLOUD/CLI chips; all privacy copy rescoped | `studio_html.py` | M | Cancel ⇒ zero network calls; every cloud action shows destination first | `test_p0_consent_and_transport`; `pw_p0.py` (cancel sends nothing) |
| P0-7 ✅ | Silent identity merging; fixed sheet-scan limits; silent bad marks | Dynamic `gridExtents`; ID-preferred identity; same-name kept separate + disambiguated; duplicate ID/row, no-ID, >max and negative marks in a visible `warn-banner`; duplicate question labels deduped visibly | `studio_html.py` | M | Duplicate-name students never merge; banner lists every issue; 500-row sheet fully read | `test_p0_data_identity_and_import_warnings`; `pw_p0.py` (banner) |
| P0-8 ✅ | DOCX losses silent | Table/image/equation counts surfaced on every upload status | `studio_html.py` | S | DOCX with a table shows "1 table(s) NOT extracted" | `test_p0_data_identity_and_import_warnings` |
| P0-9 ✅ | No size caps / cancel / retry | 20 MB per-scan cap with per-file message; Cancel between scripts; one retry w/ backoff on 429/5xx | `studio_html.py` | S | Oversized scan blocked; cancel stops the queue | `pw_p0.py` |
| P0-10 ✅ | Feature claims unlabelled | LOCAL / CLOUD / CLI chips; scan/build cards marked CLI; mappings marked SUGGESTED; "nothing uploaded" copy removed/rescoped | `studio_html.py` | S | No global "nothing is uploaded" claim remains | `test_p0_labelling_and_a11y` |

## P1 — teacher pilot quality (mostly ✅ this pass; P1-2, P1-4, P1-8 remain open)

| # | Problem | Proposed solution | Files | Cx | Acceptance |
|---|---------|-------------------|-------|----|-----------|
| P1-1 ✅ | Embedded JS untestable as JS | Extract to `src/markable/webapp/*.js`, concat at build, `node --test` unit suite | studio_html.py → webapp/ | H | JS unit tests run in CI; built hub byte-equivalent behaviour |
| P1-2 ▶ | Handwritten XLSX parser vs merged cells/styles | Bundle a maintained parser (vendored, no CDN) behind the same `parseXlsx` API; fixture tests | webapp/importers | M | merged-cell + formula fixtures parse correctly |
| P1-3 ✅ | Structured-key reconciliation in browser marking | Accept key.yaml from Rubric builder; check expected vs returned QIDs, marks_available vs key; missing-question flags | studio_html.py | M | Missing/extra question ⇒ review flag per script |
| P1-4 ▶ | Criterion-level marking schema | Per-criterion judgements (id, marks, evidence) + deterministic totals; teacher review at criterion level | MARK_SCHEMA, aimark | H | Criteria sum enforced; per-criterion display |
| P1-5 ✅ (browser: suggested/ambiguous/unmapped; confirmed remains CLI --map) | Four-state curriculum mapping | confirmed / suggested / ambiguous / unmapped states end-to-end incl. browser import of a teacher map | curriculum.py, studio | M | Legend + per-question state everywhere mappings shown |
| P1-6 ✅ (filters + bulk accept) | Review-queue UX at scale | Filters (student/question/flag type), keyboard shortcuts, bulk-accept for identical MCQ flags | studio_html.py | M | 100-item queue triaged < 10 min |
| P1-7 ✅ (list/remove/sizes; reorder & PDF page count still open) | Scans list management | Remove/reorder files, per-file size + (PDF) page count, thumbnails | aimark | S–M | Files removable before consent |
| P1-8 ▶ | WCAG 2.2 AA sweep | axe-core in Playwright CI; contrast tokens; focus trap in modal; table header scopes | CSS/JS | M | axe: no serious/critical violations |
| P1-9 ✅ (browser hub) | Small-cohort stats caveats | n<10 ⇒ "insufficient n" chips on facility/discrimination | gradebook_html, studio | S | Chips render for small n |
| P1-10 ✅ (workspaces strip + numbered nav) | Three-workspace IA + progress | Home reduced to Analyse / Build / Mark cards with step indicators | studio_html.py | M | Usability walkthrough passes |

## P2 — production readiness (open)

| # | Item | Notes |
|---|------|-------|
| P2-1 ▶ | School-managed provider proxy | Server holds keys; per-teacher auth; request/response audit log; org retention controls (ARCHITECTURE.md §Proxy) |
| P2-2 ▶ | Audit logging of cloud sends | Local append-only log + export; proxy-side canonical log |
| P2-3 ▶ | Evaluation harness + gold dataset | Implement AI_MARKING_EVALUATION_PLAN.md; block auto-accept-threshold changes on eval results |
| P2-4 ▶ | Tiered model strategy + adjudication | Cheap transcription pass; strong judge; second-pass on disagreement |
| P2-5 ▶ | Admin console | Endpoint allowlist policy, feature flags (disable cloud), pack management |
| P2-6 ▶ | LMS/CSV integrations | Compass/SEQTA-shaped exports |
| P2-7 ▶ | Signed builds + version stamping | Footer version, integrity hash for distributed hub |
