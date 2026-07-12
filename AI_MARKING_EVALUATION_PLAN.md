# AI_MARKING_EVALUATION_PLAN.md

## Purpose

No marking configuration is trusted until it clears an agreed threshold on a
**de-identified, teacher-marked gold dataset** of representative assessments.
The project brief's own gate applies: ≥99 % exact agreement on MCQ, ≥95 %
within-one-mark on short answers, before unsupervised use. Until then the
product runs in supervised-pilot mode: every flagged item human-reviewed and
unflagged items exported as labelled `auto-accepted` proposals.

## Gold dataset

- ≥3 assessments per subject/year pilot pair (one MCQ-heavy, one
  numerical/short, one extended-response).
- ≥30 scripts each, scanned exactly as teachers would scan them.
- De-identified: ID-labelled scripts only; `anon.py` aliases for the CLI path.
- Two independent teacher markers per script; disagreements resolved by a
  third → the gold mark, with per-question records retained so inter-rater
  reliability is itself measured (the AI is judged against *resolved* marks,
  and never expected to beat human–human agreement).

## Metrics (per assessment and pooled)

| Metric | Definition |
|---|---|
| Exact agreement | AI final == gold, per question |
| Within-1 agreement | abs diff ≤ 1 mark |
| Weighted Cohen's κ | quadratic weights, AI vs gold |
| False auto-approval rate | items NOT flagged for review where AI ≠ gold — **the safety metric** |
| Review recall | of items where AI ≠ gold, fraction flagged for review |
| Transcription error rate | word-level error vs human transcription sample |
| Missing-question rate | expected QIDs absent from responses |
| Teacher override rate | overrides / reviewed items in live pilot |
| Cost per script / time per script | provider usage ÷ scripts |

## Harness design

`markable eval <package> --gold gold_marks.csv` (P2 implementation):
1. Run the standard pipeline (or ingest an existing `marks_finalised.csv`).
2. Join on (student alias, question id).
3. Emit `eval_report.html` + `eval_metrics.csv` with the table above, per
   question type and per band of confidence.
4. Confidence-threshold sweep: plot false-auto-approval vs review volume for
   thresholds 0.5–0.95 so the review threshold is chosen from data, not vibes.

## Criterion-based marking (target schema)

Move from question-level to criterion-level judgements:

```
{question_id, criteria:[{criterion_id, description, marks_available,
  marks_proposed, evidence, ambiguity|null}],
 transcription, reasoning_summary, confidence, review_triggers[], feedback}
```

Deterministic post-processing computes question totals (criteria must sum),
applies review rules, and reconciles expected vs returned question/criterion
IDs against the structured key. No private chain-of-thought is requested or
stored — `reasoning_summary` is a concise, teacher-auditable justification.

## Model strategy (gated on baseline results)

- **Pass 1 (cheap)**: transcription + objective items (MCQ/numerical final
  answers) on a fast model.
- **Pass 2 (strong)**: rubric judging for short/extended/diagram on
  `AI_MODELS.claude` (currently `claude-opus-4-8`, centrally configured).
- **Adjudication**: where pass-1/pass-2 disagree, or deterministic rules fire,
  a second strong-model pass with both candidate judgements → still lands in
  the teacher review queue, never auto-resolves.

## Deployment gate

Do not enable any reduction in review coverage, and do not recommend
deployment beyond the supervised pilot, until the agreed thresholds are met on
representative assessments **and** false auto-approval is below the
school-agreed bound (proposed: <1 % of marks, measured per assessment type).
