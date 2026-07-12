# COUNCIL_AUDIT.md — LLM Council review of Markable

Scope: `markable-all.html` (the distributed hub) and its **source** — the Python
package `src/markable/` that generates it. Key fact established first: the
~1 MB HTML is a **build artifact** of `markable studio --embed`, generated from
modular Python (`studio_html.py`, `improve.py`, `rubric.py`, `gradebook*.py`,
`report.py`, `mark/`, …). The audit therefore reviews the generating source.

Every finding below was verified against the code (file:function cited).
Severity: **C**ritical / **H**igh / **M**edium / **L**ow.
Status: ✅ fixed in this audit's P0 pass · ▶ backlog (see PRIORITISED_BACKLOG.md).

Seed-concern verification summary: **13 of 15 confirmed**, 2 partially
(SC3: the "nothing uploaded" copy was accurate *for the local boxes* but
globally misleading; SC11: Scan/Mark cards did say "CLI:" in prose but carried
no visual labelling).

---

## Council Member 1 — School Assessment Expert

**Strengths.** Question-level cohort/quartile analysis is genuinely useful and
mirrors good item-analysis practice. The CLI pipeline's review rules
(`mark/__init__.py:_apply_review_rules`) enforce thresholds server-side. The
feedback slips exclude unreviewed AI marks from student-visible totals
(`feedback_html.py`) — the right validity instinct. Rubric builder produces
criterion-level keys with a `verify` list of inferences.

**Defects.**
- (C, ✅) **Answer leakage**: `improve.py:INSTRUCTION_PACK` rule 3 instructs the
  model to mark the correct MCQ option with a trailing `*`; the optimiser's
  docx/pdf exports printed that file verbatim → a "student paper" containing
  the answers. *Fixed*: student/teacher export split, `stripAnswerMarkers`,
  `detectAnswerLeaks` blocking gate, labelled filenames/headers.
- (C, ✅) **No accept/edit/override/finalise in the browser marking flow**
  (`renderMarks` was display-only; CLI `review.html` had it, browser didn't).
  *Fixed*: per-item accept/override(+reason)/undo, per-student finalise state,
  export gated until all flagged items resolved.
- (H, ▶) Partial credit / consequential-error handling depends entirely on key
  quality; the rubric pack asks for an ECF criterion on numericals but nothing
  verifies one exists. Backlog: key-lint rule.
- (M, ✅) Curriculum attainment from one assessment risked over-reading;
  in-browser mappings were unlabelled. *Fixed*: "SUGGESTED MAPPING" labels;
  confirmed mappings remain a CLI `--map` concept. (▶ four-state model below.)
- (M, ▶) No moderation support (second-marker sampling, cross-class drift).

**Risk.** A teacher could previously print the optimised "test" and hand
students the answers. This was the single worst defect in the product.

## Council Member 2 — AI Marking & Evaluation Engineer

**Strengths.** Structured outputs everywhere (`output_config.format`
json_schema); shared key context cached; per-question cohort batching in the
CLI; transcription + evidence + feedback demanded by both `MARK_SYS_PREFIX`
(browser) and `_key_context` (CLI `anthropic_marker.py`).

**Defects.**
- (C, ✅) **Model-trusted review flags** (SC4): browser flow used `j.needs_review`
  as the only review signal; no bounds checks. A response of `marks_awarded: 5`
  on a 1-mark question rendered as `5 / 1`. *Fixed*: `validateResult()` —
  deterministic rules (range clamp with visible flag, confidence clamp +
  independent 0.85 threshold, duplicate-qid detection, blank-transcription
  flag); `_review` is OUR flag, model's field is one input among several.
- (H, ✅) **Incomplete audit exports** (SC6): CSV had 7 columns, no
  transcription/evidence/override trail. *Fixed*: 14-column export
  (proposed vs final, flags, teacher_action, override_reason, transcription,
  evidence, feedback).
- (H, ▶) Whole-script marking (no expected-question reconciliation against a
  structured key — browser key is free text). Backlog: accept a structured
  key.yaml from the Rubric builder and reconcile expected vs returned IDs.
- (M, ▶) Criterion-level judgements (per-criterion marks) — designed in
  AI_MARKING_EVALUATION_PLAN.md; current schema is question-level.
- (M, ✅) Model IDs were string-literals in two call sites. *Fixed*: `AI_MODELS`
  constant. (▶ tiered model strategy — cheap transcription pass / strong
  judging pass / adjudication — is designed in the eval plan.)
- (M, ✅) No retry/rate-limit handling. *Fixed*: one retry with backoff on
  429/5xx/overloaded; Cancel button between scripts.
- (H, ▶) **No gold-dataset evaluation has ever been run.** The brief's own gate
  (≥99 % MCQ, ≥95 % within-1) is still unmet. Blocking for anything beyond a
  supervised pilot; harness specified in AI_MARKING_EVALUATION_PLAN.md.

## Council Member 3 — Privacy, Security & Governance

**Strengths.** CLI path has real pseudonymisation (`anon.py`: random aliases,
0600 local key, batch custom_ids carry aliases only). Star-schema exports are
name-free. Name joins are local (`class_list.csv`).

**Defects.**
- (C, ✅) **Keys persisted indefinitely in localStorage** (SC2:
  `saveKey`/`getKey`). *Fixed*: sessionStorage by default, explicit
  "remember on this device" opt-in, legacy-key migration, Clear-keys control,
  keys never serialised into any export (verified: exports embed data + code,
  storage reads happen at call time).
- (C, ✅) **Arbitrary endpoint exfiltration** (SC13): any URL incl. HTTP was
  accepted for the Copilot path. *Fixed*: `validateEndpoint` — HTTPS required,
  Azure/OpenAI suffix allowlist, explicit confirm-to-allow for other hosts
  (persisted allowlist), destination hostname displayed at save time and in
  every consent dialog.
- (C, ✅) **No consent step / local-cloud confusion** (SC3): cloud sends
  happened straight from a button; guide said "nothing is uploaded anywhere".
  *Fixed*: `cloudConsent()` modal before every send (provider, hostname,
  itemised payload, PII reminder, cancel); all privacy copy rescoped; LOCAL /
  CLOUD chips on every surface.
- (H, ▶) Browser marking sends handwriting images that may contain names —
  consent dialog warns and recommends IDs, but automated PII detection on
  images is not feasible client-side. Governance decision required (see
  PRIVACY_AND_DATA_FLOW.md): pilot rule = ID-labelled scans only.
- (M, ▶) No audit log of cloud sends; no admin controls. Production answer is
  a school-managed proxy (documented in ARCHITECTURE.md) — P2.

**Decisions requiring formal school approval** (not legal advice): sending
assessment content and student work to an external AI provider; retention
settings on the provider account; whether teacher-held keys are acceptable for
a pilot vs a school proxy; the ID-only-scans rule.

## Council Member 4 — Front-End, Accessibility & UX

**Strengths.** Single-file portability is a genuine teacher win; numbers are
printed inside every heat cell (colour is never the only carrier); tool cards
carry jump buttons; the three-workspace shape already half-exists
(analyse locally / build / mark).

**Defects.**
- (H, ✅) No mobile navigation (fixed 248 px column). *Fixed*: collapsible nav
  with hamburger (`#nav-toggle`, aria-expanded) under 880 px.
- (H, ✅) No visible focus, no status announcements. *Fixed*: `:focus-visible`
  outlines; every `.status` is `role="status" aria-live="polite"`; leak box is
  `role="alert"`; consent modal is `role="dialog" aria-modal` with initial
  focus.
- (M, ✅) Errors now name the failing file/limit in teacher language (size
  limits, leak lines, endpoint messages).
- (M, ▶) Full IA reduction to exactly three workspaces + progress indicator —
  backlog P1 (nav currently groups Upload / AI cloud / Reports, which
  approximates it).
- (M, ▶) File remove/reorder for the scans list; page-count display for PDFs.
- (L, ▶) Full WCAG 2.2 AA audit (contrast measurement, reduced-motion, table
  headers scope) — P1 with axe-core in CI.

## Council Member 5 — Software Architect

**Finding that reframes the brief.** The product is *not* a monolithic
hand-maintained HTML file. Source is modular Python (`models.py` schemas,
importers, exporters, providers split across `improve/rubric/anthropic_marker`,
report generators); `dist` HTML files are compiled artifacts. The requested
"modular source → compiled single file" architecture **already holds**; the
weak point is that the browser engine lives as JS-in-Python-strings.

- (H, ▶) Extract the ~2,000-line embedded JS into `src/markable/webapp/*.js`
  modules concatenated at build time (no framework needed) with JS unit tests
  (node --test). Mapped in ARCHITECTURE.md; deferred (P1/P2) because it is a
  pure refactor with regression risk during a P0 safety pass.
- (M, ✅) Model IDs centralised (`AI_MODELS`); build task added
  (`scripts/build_dist.sh` → `dist/markable.html`).
- (M, ▶) Handwritten XLSX/DOCX parsers are a data-integrity risk (SC7/SC8
  class). Mitigated now with honest-extraction warnings + dynamic bounds;
  bundling a maintained parser (SheetJS-community/exceljs subset) is P1.
- (L) Versioning: build stamps exist in git; add a version string to the
  footer at build time (P1).

## Council Member 6 — Data & Curriculum Analytics

**Defects.**
- (C, ✅) **Silent identity merging** (SC9): students keyed by display name;
  duplicate names merged trajectories; ID column parsed but unused; fixed scan
  limits (40/80/120/200 — SC8) silently truncated large sheets. *Fixed*:
  `gridExtents()` dynamic bounds; ID-preferred identity; same-name students
  kept separate and disambiguated "(id)"; duplicate IDs, duplicate rows,
  missing-ID condition, marks > max, negative marks all raised in a blocking
  `warn-banner` on the dashboard.
- (H, ✅→▶) Mapping provenance: browser mappings now labelled **suggested**;
  the four-state model (confirmed / suggested / ambiguous / unmapped) exists
  end-to-end only via CLI (`tag --map` = confirmed; keyword overlap =
  suggested; no-hit = unmapped). Ambiguous (multiple candidates) not yet
  distinguished — P1.
- (M, ▶) Facility/discrimination on tiny cohorts (n<10) should display an
  "insufficient n" caveat — P1.
- (M, ✅) Label-only mapping (SC10) is now visibly labelled as such; full-stem
  mapping requires the CLI `analyse` path which does use stems.

## Council Member 7 — Adversarial QA / Red Team

Executed against the built hub in Chromium (`pw_p0.py` + prior suites):

| Attack | Result |
|---|---|
| Marks > max, negative marks, confidence 1.7, duplicate QID, blank transcription in LLM JSON | clamped + flagged + forced review ✅ |
| Malformed LLM JSON / refusal | caught per-script, surfaced as failed card, excluded from export ✅ |
| HTTP endpoint | blocked at save ✅ |
| Unknown HTTPS host | explicit confirm required ✅ |
| Consent cancel | zero network calls ✅ |
| Leaky optimised test (option `*` + "Answer:" line) | student download blocked, lines cited ✅ |
| Duplicate students / IDs, no-ID workbook, marks>max in XLSX | visible banner ✅ |
| Same file re-selected (no change event) | known Chromium behaviour; harmless (state kept) |
| >20 MB scan | blocked with per-file message ✅ |
| Rate limit / 5xx | one retry then teacher-readable error ✅ |
| Keyboard-only | focus-visible outlines; consent traps initial focus; full trap loop P1 |
| Malformed DOCX/XLSX (not a zip) | caught: "not a valid .xlsx/.docx" ✅ |
| Merged cells / formulas | formulas: cached values read (data_only semantics in browser parser reads `<v>`) ✅; merged cells untested — P1 fixture |
| Very large PDFs / rotated scans / mixed pages | size cap only; rotation/mixing is CLI territory (deskew/QR) — labelled CLI ✅ |

Unresolved red-team items are in the backlog with fixtures specified in
TEST_PLAN.md.
