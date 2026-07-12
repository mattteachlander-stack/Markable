# PRIVACY_AND_DATA_FLOW.md

## Data-flow map (hub, after this pass)

| Feature | Where it runs | What leaves the browser | Gate |
|---|---|---|---|
| Results spreadsheet → dashboard | **Local** | Nothing | — |
| Test → readiness check | **Local** | Nothing | — |
| Downloadable dashboards / slips / review queue | **Local** files | Nothing | — |
| Assessment optimiser (Option A) | **Cloud** | Extracted test text | Consent dialog (provider + hostname + payload list) |
| Rubric builder (Option A) | **Cloud** | Extracted test text | Consent dialog |
| AI marking studio | **Cloud** | Test text, key text, scan images/PDFs | Consent dialog listing every file + size |
| Option B "own AI" prompts | **Local generation**; teacher pastes into their own AI | Whatever the teacher pastes | Teacher's own action |
| CLI `markable mark` | Cloud (Anthropic) | Answer-zone crops + **random aliases only** (`anon.py`) | Pseudonymisation on by design |

Every cloud surface is labelled with an amber **CLOUD** chip; every local
surface with a green **LOCAL** chip. The former blanket claim "nothing is
uploaded anywhere" has been removed; local claims are now scoped to the
specific boxes they are true of.

## Credentials

- Default: **sessionStorage** — cleared when the tab closes.
- "Remember on this device" is an explicit opt-in (localStorage).
- Legacy keys found in localStorage are migrated to session storage on load.
- "Clear keys from this browser" wipes both stores.
- Keys are read at call time and are **never** written into any exported file.
- Custom endpoints: HTTPS mandatory; hostname must match the Azure/OpenAI
  allowlist or be explicitly approved by the teacher (then pinned); the
  destination hostname is displayed at save time and in every consent dialog.

## Student identifiers

- Dashboards: names stay in the browser; exports produced by the CLI star
  schema are ID-only; feedback-slip names join locally from `class_list.csv`.
- Browser marking: scans may contain handwriting/names. The consent dialog
  requires the teacher to confirm and recommends ID-labelled scripts.
  **Pilot rule: only ID-labelled scans may be sent** (see checklist).
- CLI marking: student IDs are replaced by `secrets.token_hex` aliases before
  any provider sees an item; the re-identification key (`anon_key.yaml`,
  chmod 600) never leaves the package folder; deleting it permanently unlinks
  transmitted data.

## Retention & deletion

- In-browser: uploaded files live in page memory only; review decisions and
  dashboards persist in the browser's local storage until cleared; keys as
  above.
- Provider-side retention is governed by the school's provider agreement —
  a governance decision, not a product default.

## Decisions requiring formal school approval (governance, not legal advice)

1. Approval to send assessment content and student work to the chosen AI
   provider(s), and under which provider data-retention terms.
2. Whether teacher-held API keys are acceptable for the pilot, or whether the
   school proxy (ARCHITECTURE.md) must come first.
3. The ID-only-scans rule and the fallback when scripts carry names.
4. Where finalised marks/exports are stored and for how long.
5. Parent/student communication about AI-assisted marking with teacher review.
