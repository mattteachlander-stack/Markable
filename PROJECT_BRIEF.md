# Project Brief: Markable

**An assessment preparation, AI-marking, and curriculum-intelligence pipeline for paper-based school assessments.**

Author: Matthew Lander · Draft v1.1 · July 2026

The project has three parts. **Part 1 (sections 1–8): Structure & Marking** — restructure draft assessments into machine-markable papers, mark scanned scripts, produce scores and item analysis. **Part 2 (section 9): Curriculum Intelligence** — map every question to an official curriculum, and report each student's attainment, deficiencies, and misconceptions against curriculum standards. **Part 3 (section 10): Dashboards** — surface the analysis to teachers and faculty through an instant local dashboard and a Power BI semantic model. Part 1 must be complete and trusted before Parts 2–3 are built on top of it.
Intended use: hand this brief to Claude Code as the founding spec (`PROJECT_BRIEF.md`), then generate a `CLAUDE.md` from it once architecture decisions are locked.

---

## 1. Problem statement

Teachers write assessments in Word or Google Docs with no consistent structure. Marking them with AI fails not because AI can't mark, but because the inputs are messy: questions aren't uniquely identified, answers appear anywhere on the page, scans can't be matched to students or questions, and there's no machine-readable answer key. The result is that AI marking is unreliable and the teacher can't trust or audit it.

**Markable solves the input problem.** It takes a draft assessment and restructures it into a scan-friendly, machine-markable paper plus a structured marking pack — so that when scanned student scripts come back, an AI marker can reliably produce raw scores, per-question feedback, and class-level item analysis, with a human review queue for anything uncertain.

## 2. Target user and context

- Secondary Science teacher (Years 7–10), Victorian curriculum, but nothing subject-specific should be hard-coded.
- Assessments are completed **on paper, by hand**, then scanned (multi-page PDF per class, or per student).
- v1 must handle **all question types**: multiple choice, short answer, extended response, numerical working, and **diagrams/labelling** — with the understanding that lower-confidence judgements are flagged for teacher review rather than silently guessed.
- Single-user CLI tool first. No web app, no accounts, no server in v1.

## 3. Core concepts and vocabulary

| Term | Meaning |
|---|---|
| **Draft** | The teacher's original assessment (docx, PDF, or markdown). |
| **Assessment Package** | The folder Markable produces: print-ready paper + marking pack + manifest. |
| **Marking Pack** | Machine-readable answer key + rubrics + marks map (`key.yaml`). |
| **Script** | One student's completed, scanned paper. |
| **Question ID** | Stable unique ID per question/part, e.g. `Q07a`. Never renumbered after the paper is finalised. |
| **Answer Zone** | A defined region on the page where the student's response must go (bubble grid, response box, working frame, diagram frame). |
| **Review Queue** | Items the marker was not confident about, surfaced for the teacher to judge. |

## 4. Pipeline overview

Five commands, each independently runnable:

```
markable ingest <draft>          # parse the teacher's draft
markable build <package>         # generate the print-ready paper + marking pack
markable scan <package> <pdfs>   # split, deskew, and match scanned scripts
markable mark <package>          # AI-mark all matched scripts
markable report <package>        # scores, feedback sheets, item analysis
```

### 4.1 `ingest` — parse the draft

- Accepts `.docx`, `.pdf`, or `.md`.
- Uses Claude to extract a structured question list: stem text, question type, parts, marks allocated, any stimulus material (images, data tables), and any answers already embedded in the draft.
- Interactively resolves gaps: *"Q4 has no marks allocated — how many?"*, *"Q9 looks like a diagram question — what must the diagram show to earn each mark?"*
- Output: `assessment.yaml` (the canonical structured assessment) — the single source of truth for everything downstream.

### 4.2 `build` — generate the paper and marking pack

Produces the **Assessment Package** folder:

```
packages/2026-T3-Y9-chemistry-test/
├── assessment.yaml        # canonical structure
├── key.yaml               # marking pack (answers, rubrics, marks)
├── paper.pdf              # print-ready student paper
├── paper.docx             # editable version (optional export)
├── manifest.json          # test ID, version hash, page map
└── scripts/               # populated later by `scan`
```

**Paper layout requirements (the heart of the project):**

- Every page: header with test ID, page `n of N`, and a student-ID box (pre-printed ID grid or handwritten ID box — support both).
- A **QR code on every page** encoding `{test_id, version_hash, page_number}` so pages can be matched even if scans arrive shuffled or upside down.
- Corner **registration marks** on every page for deskewing and for locating answer zones by fixed coordinates.
- **MCQ**: bubble grid in a fixed column (consistent x-position on every page).
- **Short answer**: bordered response box sized to the expected answer length; lines optional.
- **Numerical/working**: response box with a separated "final answer" cell so the final answer is always in a predictable location, while working remains visible above it.
- **Diagram/labelling**: fixed frame containing the stimulus (or blank frame for student-drawn diagrams) with labelled anchor points where applicable.
- Question IDs printed beside every answer zone (small, e.g. `Q07a`), so a cropped zone is self-identifying even without coordinates.
- The `manifest.json` records the exact bounding box of every answer zone per page — this is what makes per-question cropping deterministic.

**Marking pack (`key.yaml`) schema (illustrative):**

```yaml
test_id: 2026-T3-Y9-chem
total_marks: 45
questions:
  - id: Q01
    type: mcq
    marks: 1
    correct: C
    distractor_notes:        # optional, improves feedback + item analysis
      A: "confused atomic number with mass number"
  - id: Q07a
    type: short_answer
    marks: 2
    criteria:
      - point: "states that rate increases"
        marks: 1
      - point: "links to increased collision frequency"
        marks: 1
    accept: ["more successful collisions per second"]
    reject: ["particles get more energy (without collision link)"]
  - id: Q09
    type: diagram
    marks: 3
    criteria:
      - point: "labels anode and cathode correctly"
        marks: 1
      - point: "electron flow arrow from anode to cathode"
        marks: 1
      - point: "electrolyte identified"
        marks: 1
    review_threshold: 0.8    # below this confidence → review queue
  - id: Q10
    type: extended
    marks: 6
    rubric:
      - band: "5–6"
        descriptor: "explains both variables, links to theory, uses data"
      - band: "3–4"
        descriptor: "explains one variable with partial theory link"
      - band: "1–2"
        descriptor: "identifies variables without explanation"
```

### 4.3 `scan` — ingest completed scripts

- Input: one or more scanned PDFs (whole-class batch or per-student files), any page order.
- Steps: split to page images → read QR → deskew via registration marks → group pages by student (student-ID box read via vision; ambiguous IDs go to a quick interactive confirm) → crop every answer zone using the manifest's coordinates.
- Output: `scripts/<student_id>/Q07a.png`, etc., plus a `scan_report` listing missing pages, unreadable IDs, and blank responses.

### 4.4 `mark` — AI marking engine

- Marks **per question, not per script**: for each question, batch all students' cropped responses with the key entry and criteria. This keeps the marking context tight, consistent across the cohort, and cheap.
- Every judgement returns structured JSON:

```json
{
  "student": "S1042",
  "question": "Q07a",
  "marks_awarded": 1,
  "criteria_met": ["states that rate increases"],
  "transcription": "the reaction gets faster",
  "evidence": "response states rate increases but gives no collision reasoning",
  "feedback": "You correctly said the rate increases — now explain *why* using collision theory.",
  "confidence": 0.93
}
```

- **Confidence and review rules:**
  - Below the question's `review_threshold` (default 0.85; diagrams/extended default higher) → review queue.
  - Illegible or blank → review queue, never a guess.
  - MCQs with two bubbles filled, or erasures → review queue.
  - v1 policy: **all diagram and extended-response marks are spot-checkable** — the report links every mark to its cropped image and evidence string, so auditing takes seconds.
- Review queue UX in v1: a generated `review.html` page showing each flagged crop beside the AI's proposed mark and evidence, with the teacher recording final marks back into the results file (simple edit or a tiny local form — keep it minimal).
- API usage: Anthropic Python SDK, vision inputs of the cropped zones. Use prompt caching for the shared key/rubric context and the batch API for whole-class runs. Verify current model names, batch, and caching details against the official docs at build time: https://docs.claude.com/en/api/overview

### 4.5 `report` — outputs

1. **`results.csv`** — one row per student × question: marks awarded, max marks, criteria met, confidence, review status. Plus a per-student totals sheet with raw score and percentage.
2. **Feedback sheets** — one page per student (PDF or docx): per-question feedback, strengths, and next steps, written in a warm, student-appropriate voice. Tone configurable.
3. **Item analysis (`item_analysis.csv` + summary)** —
   - Facility index per question (proportion of marks earned).
   - Discrimination index (top-third vs bottom-third performance).
   - MCQ distractor analysis: how many students chose each option, mapped to `distractor_notes` for misconception reporting.
   - Curriculum-tag rollup if questions carry tags (e.g. `VC2S9U04`) — cohort performance by outcome.
4. **Teacher summary** — a short generated narrative: hardest questions, common misconceptions, suggested reteach focus.

## 5. Tech stack (recommended, not mandated)

- **Language:** Python 3.12, single package, `uv` for env management.
- **Paper generation:** Typst (preferred — precise layout, fast, plain-text templates, deterministic coordinates) with a `docx` export fallback via pandoc for teachers who want to hand-edit. If Typst proves awkward, ReportLab is the fallback for pixel-exact zone placement.
- **QR / registration:** `segno` for QR generation; OpenCV for registration-mark detection, deskew, and zone cropping. `pyzbar` or OpenCV's QR detector for reading.
- **PDF/scan handling:** `pypdf` + `pdf2image` (poppler).
- **AI:** Anthropic Python SDK (vision, structured outputs, batch, prompt caching) — confirm specifics against https://docs.claude.com/en/api/overview at build time.
- **Data:** YAML for human-edited files, JSON for machine artifacts, CSV for exports. SQLite only if state management becomes painful — avoid it in v1.
- **CLI:** `typer` + `rich` for the interactive gap-resolution prompts and progress output.

## 6. Build phases

**Phase 1 — Structure (the foundation, no AI marking yet)**
`ingest` + `build`. Prove the round trip: draft in → print-ready paper + key.yaml out. Print a real test, check zones, QR, and registration marks survive photocopying and a school scanner. *Exit criteria: a real Year 9 test printed, sat, scanned, and every answer zone cropped correctly from the scans.*

**Phase 2 — MCQ + short answer marking**
`scan` + `mark` + basic `report` for MCQ and short-answer types only. Validate against a hand-marked set: target ≥99% agreement on MCQ, ≥95% within-1-mark on short answers before trusting it.

**Phase 3 — Extended response, working, diagrams**
Add rubric-band marking, final-answer-cell numerical marking, and diagram criteria marking with the review queue and `review.html`. Diagrams launch in "propose + always review" mode; loosen only after measured agreement.

**Phase 4 — Analysis polish**
Full item analysis, distractor/misconception reporting, curriculum-tag rollups, teacher summary narrative, feedback-sheet templates.

## 7. Guardrails, risks, honest limitations

- **Human-in-the-loop is a feature, not a fallback.** The tool proposes marks; the teacher owns them. Every mark links to its evidence crop. Nothing below threshold is auto-finalised.
- **Student privacy:** scripts are marked by student ID, never name; names live only in a local `class_list.csv` the teacher controls and are joined only at report time. Check school policy on sending student work to external AI services before first real use — if required, the ID-only design plus stripping any name fields from crops supports a de-identified workflow. No student data is stored anywhere except the local package folder.
- **Handwriting reality:** vision transcription is strong but not perfect, especially for messy Year 8 handwriting and crossed-out working. The transcription field in every judgement exists so errors are visible, not hidden.
- **Bias/consistency:** marking per-question in cohort batches (not per-student) reduces drift; a fixed marking prompt per question keeps criteria application consistent. Re-runs should be deterministic in outcome distribution (low temperature, structured criteria).
- **Version integrity:** the `version_hash` in every QR ties scripts to the exact paper version — prevents marking a script against a revised key.
- **Scope discipline for v1:** no LMS integration, no web dashboard, no multi-teacher accounts, no online testing mode. Paper in, marks and analysis out.

## 8. Example end-to-end session

```bash
markable ingest drafts/y9-chem-test.docx
# → interactive: confirms 14 questions, asks for marks on Q4,
#   asks for diagram criteria on Q9 → writes assessment.yaml

markable build packages/2026-T3-Y9-chem
# → paper.pdf (print 26 copies), key.yaml scaffolded for review
#   (teacher opens key.yaml, refines accept/reject lists)

# ...students sit the test, scripts scanned on the school copier...

markable scan packages/2026-T3-Y9-chem scans/period3.pdf
# → 26 scripts matched, 1 unreadable student ID → interactive fix

markable mark packages/2026-T3-Y9-chem
# → 361/364 responses marked, 3 in review queue → review.html

markable report packages/2026-T3-Y9-chem
# → results.csv, item_analysis.csv, 26 feedback PDFs, summary.md
```

---

# Part 2: Curriculum Intelligence

## 9. Overview

Part 2 turns Markable's question-level results into **standards-referenced reporting**. Every question is mapped to one or more outcomes in an official curriculum; every student then receives a report describing their attainment *against that curriculum* — content knowledge by strand, science skills, identified deficiencies, and misconceptions — and the teacher gets the cohort-level equivalent.

Science first, but the engine must be **curriculum-agnostic**: nothing science-specific lives in code, only in curriculum packs and prompt templates. Rolling out to another faculty should mean importing another curriculum pack, not writing code.

### 9.1 Curriculum packs

A **curriculum pack** is a structured, versioned representation of an official curriculum, ingested once and reused across every assessment:

```
curricula/
├── ac9-science/            # Australian Curriculum v9 – Science
│   ├── pack.yaml
│   └── source_meta.json    # provenance: source, version, date ingested
├── vc2-science/             # Victorian Curriculum 2.0 – Science
└── vce-chemistry-2024/      # VCE study design
```

**`pack.yaml` schema (illustrative):**

```yaml
curriculum: AC v9 Science
version: "9.0"
levels: ["7", "8", "9", "10"]
dimensions:
  - id: SU        # Science Understanding
  - id: SI        # Science Inquiry
  - id: SHE       # Science as a Human Endeavour
outcomes:
  - code: AC9S9U04
    level: "9"
    dimension: SU
    strand: "Chemical sciences"
    description: "explain how the products of chemical reactions..."
    elaborations: [...]
  - code: AC9S9I05
    level: "9"
    dimension: SI
    strand: "Processing, modelling and analysis"
    description: "select and construct appropriate representations..."
achievement_standards:
  - level: "9"
    statements:
      - id: AS9-03
        maps_to: [AC9S9U04]
        text: "...explain the effects of chemical reactions..."
misconception_library: []   # grows over time — see 9.4
```

**Ingestion (`markable curriculum import`):**

- **AC v9 (best case):** ACARA publishes the curriculum as machine-readable files — JSON+LD/RDF downloads and a SPARQL endpoint (see https://www.australiancurriculum.edu.au/machine-readable-australian-curriculum). Import directly; codes, strands, elaborations, and achievement standards come pre-structured. This is the reference implementation.
- **Victorian Curriculum 2.0 / VCE study designs / any PDF-or-webpage curriculum:** Claude-assisted ingestion — parse the source document, propose a pack.yaml, teacher reviews and approves. Same schema regardless of source.
- Packs are versioned and immutable once used by an assessment (same `version_hash` discipline as papers), so historical reports stay valid when curricula update.

### 9.2 Question tagging (`markable tag`)

```bash
markable tag packages/2026-T3-Y9-chem --curriculum ac9-science
```

- Claude reads each question (stem, criteria, marks) against the pack and proposes tags: one or more outcome codes, the dimension (content vs inquiry skill), and optionally a cognitive-demand level (Bloom's or SOLO — pick one and stay consistent).
- Each proposal carries a confidence and a one-line justification. Teacher confirms/edits in the same interactive style as `ingest` — tagging is a judgement call and the teacher's confirmation is what makes downstream reports defensible.
- Tags are written into `assessment.yaml` per question (and per criterion where a single question assesses multiple outcomes — e.g. a prac-analysis question that is both `SU` content and an `SI` skill).
- Once tagged, a question's tags travel with it forever — enabling a future question bank where reusing a question reuses its curriculum mapping for free.

### 9.3 Standards-referenced reporting (`markable report --curriculum`)

Extends Part 1's reports with:

**Per student:**
- **Curriculum attainment profile:** marks earned vs available per outcome code, rolled up by strand and dimension — e.g. *Chemical sciences 78%, Physical sciences 45%; Science Inquiry: planning strong, data analysis weak.*
- **Achievement standard mapping:** evidence collected against each relevant achievement-standard statement at the student's level (working towards / at / above framing — configurable to school language).
- **Deficiencies:** outcomes where the student repeatedly missed criteria, stated specifically ("cannot yet balance chemical equations — missed in Q3, Q7b, Q11") with the evidence links from Part 1.
- **Misconceptions:** drawn from MCQ distractor choices (`distractor_notes`) and short-answer evidence, phrased as the misconception itself, not just the wrong answer ("believes mass is lost when gas is produced in a reaction").
- **Next steps:** 2–3 concrete, curriculum-linked recommendations in student-friendly language.

**Per cohort (teacher view):**
- Heatmap: outcome code × class facility — where the whole class is weak.
- Misconception frequency table — what to reteach, ranked by prevalence.
- Coverage audit: which outcomes at this level have been assessed this year, and which haven't — turning Markable into a curriculum-coverage tracker as a side effect.

**Longitudinal (the compounding value):**
- A local per-student attainment store (`students/<id>/history.json` or SQLite) accumulating outcome-level evidence across every Markable assessment through the year.
- Reports show trajectory per strand/skill across the semester, and end-of-year reports draw on the full evidence base rather than one test.
- Privacy: this is the most sensitive artifact in the system — local only, ID-keyed, and covered by the same de-identification rules as Part 1. Longitudinal profiling of students must comply with school policy; make the store easy to export and easy to delete.

### 9.4 Misconception library

- Each curriculum pack carries a growing `misconception_library`: canonical misconceptions linked to outcome codes (science education research documents these extensively — seed the library with well-known ones per topic, then grow it from real distractor and response data).
- At `build` time, the library suggests high-quality MCQ distractors ("want a distractor targeting the 'heavier objects fall faster' misconception?") — closing the loop from analysis back into better assessment design.

### 9.5 Multi-faculty rollout

- The engine never says "science": dimensions, strands, and skills all come from the pack. A Humanities pack with its own skills dimension should work untouched.
- Prompt templates (marking, tagging, feedback voice) live in per-subject template files, overridable per faculty.
- Rollout playbook per faculty: import curriculum pack → run one real assessment through Parts 1+2 with that faculty's teacher reviewing everything → tune templates → hand over.

### 9.6 Build phases (continuing from Part 1's Phases 1–4)

**Phase 5 — Curriculum packs + tagging.** MRAC importer for AC v9 Science; Claude-assisted importer for VC 2.0; `markable tag` with interactive confirmation. *Exit criteria: a real tagged assessment where the teacher agrees with ≥90% of first-pass tag proposals.*

**Phase 6 — Standards-referenced reports.** Per-student curriculum profiles, cohort heatmap, misconception table, coverage audit. Single-assessment scope only.

**Phase 7 — Longitudinal + misconception library.** Cross-assessment attainment store, trajectory reporting, seeded misconception library, distractor suggestions at build time.

---

# Part 3: Dashboards & Faculty Reporting

## 10. Overview

The analysis from Parts 1–2 is surfaced to teachers and faculty through interactive dashboards. Reference design: a per-assessment overview with cohort KPIs (average, median, high/low, % ≥70, % <50, scaled average, grade distribution), score-distribution histogram, a question-performance matrix segmented by cohort quartile (all / top 25% / middle 50% / bottom 25%), performance by topic/section, per-question difficulty classification (easy ≥80% / moderate 50–79% / difficult <50%), a student performance snapshot with ranks, auto-generated key insights, and filters for assessment, class, and teacher — with drill-through pages for question analysis (including distractor data), topic analysis, student analysis, and class comparison.

**Two delivery tiers, one data model:**

1. **Tier 1 — instant local dashboard (`markable report --dashboard`):** a self-contained HTML file per assessment package (same zero-infrastructure philosophy as `review.html`). Charts via a bundled JS chart library, no server, opens in any browser, shareable as a single file. This is the teacher's day-one view and ships in the same phase as reporting.
2. **Tier 2 — Power BI (`markable export --powerbi`):** the faculty-scale view. Markable exports an analysis-ready star schema to a shared location (e.g. a SharePoint/OneDrive folder Power BI refreshes from), plus a provided `.pbit` Power BI template implementing the reference design. Faculty gets cross-class, cross-teacher, cross-assessment, whole-year views without Markable running a server. Verify current Power BI connector/refresh specifics against Microsoft docs at build time.

### 10.1 The star schema (the contract between Markable and any BI tool)

```
fact_response        # one row per student × question × assessment
  assessment_id, student_id, question_id, marks_awarded, marks_available,
  correct (bool, MCQ), option_chosen (MCQ), criteria_met_count,
  confidence, reviewed (bool), quartile_at_assessment

fact_attainment      # one row per student × outcome × assessment (Part 2)
  assessment_id, student_id, outcome_code, marks_awarded, marks_available

dim_assessment       # test id, title, subject, year level, class, teacher,
                     # date, total marks, version_hash
dim_question         # question id, type, topic/section, marks, difficulty
                     # class (computed), outcome codes, misconception tags
dim_student          # student id, class, (name join is LOCAL-ONLY — see privacy)
dim_outcome          # outcome code, strand, dimension, level, curriculum version
dim_grading          # score band → grade mapping (see 10.2)
```

Everything on the reference dashboard is derivable from these tables: quartile matrices from `fact_response` + `quartile_at_assessment`; topic rollups via `dim_question`; grade donuts via `dim_grading`; curriculum heatmaps via `fact_attainment` + `dim_outcome`. Exports as CSV (and Parquet for larger faculties).

### 10.2 Grading and scaling configuration (`grading.yaml`)

The reference design shows both raw % and **scaled %** plus A+–E grades. These are school-specific, so they're config, not code:

```yaml
scaling: none | linear | mean-anchored   # how scaled % is derived
grade_bands:                              # school's scheme
  A+: [90, 100]
  A:  [80, 89]
  # ...
  E:  [0, 19]
```

### 10.3 Key insights panel

The auto-generated narrative (Claude, at report time): lowest/highest performing questions with a suggested action ("Q1d had the lowest success rate — consider reviewing enzyme mechanisms"), intervention flags (% below 50), skill-area commentary, and — with Part 2 — misconception and curriculum-coverage insights. Exported as `insights.json` so both dashboard tiers render the same text; every insight links back to its evidence (question, crop set, or outcome).

### 10.4 Privacy in dashboards

- Per-student views with names/ranks are appropriate for the owning teacher's Tier 1 dashboard; **faculty-level Power BI defaults to ID-only**, with the name join applied via a local-only lookup or Power BI row-level security if the school configures it.
- Student rank tables are a config toggle (`show_ranks: false` by default) — ranking visibility is a school-culture decision, not a software default.
- The shared export folder contains no names, no scans, no crops — only the star schema and insights.

### 10.5 Build phases (continuing)

**Phase 8 — Tier 1 dashboard.** Self-contained HTML dashboard implementing the reference design for a single assessment (overview + question drill-down + topic view). *Exit criteria: a real marked assessment rendered as the reference dashboard, teacher-usable with zero setup.*

**Phase 9 — Power BI export.** Star-schema export, `.pbit` template with the reference pages plus class comparison and year-to-date curriculum views, refresh from a shared folder, RLS guidance documented.

---

## 11. First instructions to Claude Code

1. Read this brief fully. Generate a `CLAUDE.md` capturing the architecture decisions, folder conventions, and the key.yaml / manifest / pack.yaml / star-schema definitions as authoritative. The star schema (10.1) is a Part 1 commitment: `report` should write `fact_response` and the dims from day one, so Parts 2–3 are additive.
2. Scaffold the package (`uv`, `typer` CLI with subcommands stubbed — including `curriculum` and `tag` as empty stubs so the architecture anticipates Part 2).
3. Build Phase 1 only. Do not write any marking code until a printed-and-scanned round trip passes.
4. Create `fixtures/` with a small sample draft (6 questions covering every type) used by all tests, plus a miniature 10-outcome curriculum pack fixture for future Part 2 tests.
