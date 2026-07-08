"""`rubric` — AI-draft a complete marking key (rubric) from a test.

The single biggest driver of reliable AI marking is the quality of the key
(brief §4.2), and competitors are rubric-first. This module closes that gap:
send the test to Claude with RUBRIC_PACK and get back a complete `key.yaml`
draft in the exact `Key`/`KeyEntry` schema the marking engine consumes —
per-question criteria with marks, accept/reject lists, MCQ correct answers
with distractor notes, numerical final answers with tolerance, and banded
rubrics for extended responses. Everything the model had to infer is listed
in `verify` notes so the teacher signs off deliberately (human-in-the-loop).

The studio's Rubric builder page sends the identical pack from the browser;
`markable rubric` is the CLI twin. Needs the `ai` extra + ANTHROPIC_API_KEY.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Optional

import yaml

from .models import Key, KeyEntry

MODEL = "claude-opus-4-8"
MAX_TOKENS = 16000

RUBRIC_PACK = """You are drafting the marking key (rubric) for a teacher's test so it can be \
marked reliably and consistently — by an AI marker with human review, or by a colleague. \
For EVERY question in the test, produce one key entry:

1. TYPE each item: mcq, short_answer, numerical, extended, or diagram (respect any type
   already stated in the question header).
2. MARKS: use the marks stated on the question. Criteria marks MUST sum exactly to the
   question's marks.
3. mcq → give `correct` (the option letter) and a short `distractor_notes` entry for each
   wrong option explaining the misconception it represents.
4. short_answer / diagram → 1 criterion per mark: each `point` must be a single observable,
   gradeable statement (what must be present to earn that mark), plus `accept` (alternative
   correct wordings/values) and `reject` (common wrong answers that earn nothing).
5. numerical → criteria for working AND the `final_answer` (with units) plus a sensible
   `tolerance` where rounding is possible; include an error-carried-forward criterion where
   appropriate.
6. extended → criteria for the required content AND 3-4 `rubric` bands (band label +
   descriptor) describing quality levels from partial to full.
7. GROUND EVERYTHING IN THE TEST: never invent content the test doesn't assess. If the test
   doesn't state the correct answer and you had to infer it, add a note to `verify` —
   the teacher must confirm every inference before marking.
8. IDs: use the question IDs exactly as they appear (Q1, Q6a …).

Return JSON: test_id (from the test, or invent a sensible slug), total_marks,
questions (the key entries), verify (list of {question_id, note} the teacher must check)."""

# Structured-output schema. distractor_notes rides as an array of
# {option, note} pairs (strict schemas forbid arbitrary-key objects);
# `to_key` converts it to the dict KeyEntry expects.
_ENTRY_SCHEMA = {
    "type": "object",
    "properties": {
        "id": {"type": "string"},
        "type": {"type": "string", "enum": ["mcq", "short_answer", "numerical", "extended", "diagram"]},
        "marks": {"type": "integer"},
        "correct": {"type": ["string", "null"]},
        "distractor_notes": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {"option": {"type": "string"}, "note": {"type": "string"}},
                "required": ["option", "note"],
                "additionalProperties": False,
            },
        },
        "criteria": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {"point": {"type": "string"}, "marks": {"type": "integer"}},
                "required": ["point", "marks"],
                "additionalProperties": False,
            },
        },
        "accept": {"type": "array", "items": {"type": "string"}},
        "reject": {"type": "array", "items": {"type": "string"}},
        "final_answer": {"type": ["string", "null"]},
        "tolerance": {"type": ["number", "null"]},
        "rubric": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {"band": {"type": "string"}, "descriptor": {"type": "string"}},
                "required": ["band", "descriptor"],
                "additionalProperties": False,
            },
        },
    },
    "required": ["id", "type", "marks", "correct", "distractor_notes", "criteria",
                 "accept", "reject", "final_answer", "tolerance", "rubric"],
    "additionalProperties": False,
}

RUBRIC_SCHEMA = {
    "type": "object",
    "properties": {
        "test_id": {"type": "string"},
        "total_marks": {"type": "integer"},
        "questions": {"type": "array", "items": _ENTRY_SCHEMA},
        "verify": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {"question_id": {"type": "string"}, "note": {"type": "string"}},
                "required": ["question_id", "note"],
                "additionalProperties": False,
            },
        },
    },
    "required": ["test_id", "total_marks", "questions", "verify"],
    "additionalProperties": False,
}


def build_rubric_request(test_text: str, model: str = MODEL) -> dict:
    """Pure request construction — unit-testable without a client or key."""
    return {
        "model": model,
        "max_tokens": MAX_TOKENS,
        "thinking": {"type": "adaptive"},
        "system": [
            {
                "type": "text",
                "text": RUBRIC_PACK,
                "cache_control": {"type": "ephemeral"},
            }
        ],
        "output_config": {"format": {"type": "json_schema", "schema": RUBRIC_SCHEMA}},
        "messages": [
            {"role": "user", "content": f"Draft the marking key for this test:\n\n{test_text}"}
        ],
    }


def run_rubric(test_text: str, client: Optional[Any] = None, model: str = MODEL) -> dict:
    """Send the test + rubric pack to Claude; return the raw rubric payload."""
    if client is None:
        try:
            import anthropic
        except ImportError as exc:
            raise RuntimeError("The rubric builder needs the 'ai' extra: uv sync --extra ai") from exc
        client = anthropic.Anthropic()
    if not test_text.strip():
        raise ValueError("the test is empty — nothing to build a rubric from")
    message = client.messages.create(**build_rubric_request(test_text, model))
    if getattr(message, "stop_reason", None) == "refusal":
        raise RuntimeError("the model declined to process this document")
    text = next(b.text for b in message.content if b.type == "text")
    return json.loads(text)


def to_key(payload: dict) -> Key:
    """Validate the AI payload into the authoritative `Key` model — the same
    schema `markable mark` reads, so the draft drops straight into the pipeline."""
    entries = []
    for q in payload["questions"]:
        notes = {d["option"]: d["note"] for d in (q.get("distractor_notes") or [])}
        entries.append(KeyEntry(
            id=q["id"],
            type=q["type"],
            marks=q["marks"],
            correct=q.get("correct"),
            distractor_notes=notes or None,
            criteria=q.get("criteria") or [],
            accept=q.get("accept") or [],
            reject=q.get("reject") or [],
            final_answer=q.get("final_answer"),
            tolerance=q.get("tolerance"),
            rubric=q.get("rubric") or [],
            # brief policy: harder-to-judge types review at a higher bar
            review_threshold=0.9 if q["type"] in ("extended", "diagram") else 0.85,
        ))
    return Key(
        test_id=payload["test_id"],
        total_marks=payload.get("total_marks") or sum(e.marks for e in entries),
        questions=entries,
    )


def write_key(key: Key, path: Path) -> Path:
    path.write_text(
        "# Marking key drafted by `markable rubric` — review every entry, especially\n"
        "# anything listed under 'verify' in the command output, before marking.\n"
        + yaml.safe_dump(key.model_dump(mode="json", exclude_none=True), sort_keys=False,
                         allow_unicode=True),
        encoding="utf-8",
    )
    return path


def marks_check(payload: dict) -> list[str]:
    """Local guard: criteria must sum to the question's marks (rule 2)."""
    problems = []
    for q in payload["questions"]:
        crit = q.get("criteria") or []
        if crit and sum(c["marks"] for c in crit) != q["marks"]:
            problems.append(
                f"{q['id']}: criteria sum to {sum(c['marks'] for c in crit)}, question is worth {q['marks']}"
            )
    return problems
