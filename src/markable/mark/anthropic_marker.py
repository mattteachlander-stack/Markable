"""Anthropic vision marker (requires the `ai` extra: uv sync --extra ai).

Marks one question across the whole cohort with a **shared, cached system
prompt** (the key entry + criteria — identical for every student, so prompt
caching makes the per-student cost the crop image + a small completion), and
per-student vision calls returning a structured JSON judgement enforced by
`output_config.format`. For whole-class runs, `use_batches=True` submits the
cohort through the Message Batches API (50% cheaper; results keyed by
custom_id, never order).

Verified against the current API docs (claude-api skill, 2026-06): model
`claude-opus-4-8`, adaptive thinking, `output_config.format` json_schema,
`cache_control` on the system block, `messages.batches` for batch runs.
"""

from __future__ import annotations

import base64
import json
import time
from typing import Any, Optional

from ..models import Judgement, JudgementStatus, KeyEntry, Question, QuestionType
from . import MarkItem

MODEL = "claude-opus-4-8"
MAX_TOKENS = 2048

_JUDGEMENT_SCHEMA = {
    "type": "object",
    "properties": {
        "marks_awarded": {"type": "number"},
        "criteria_met": {"type": "array", "items": {"type": "string"}},
        "option_chosen": {"type": ["string", "null"]},
        "transcription": {"type": "string"},
        "evidence": {"type": "string"},
        "feedback": {"type": "string"},
        "confidence": {"type": "number"},
        "needs_review": {"type": "boolean"},
        "review_reason": {"type": ["string", "null"]},
    },
    "required": [
        "marks_awarded",
        "criteria_met",
        "option_chosen",
        "transcription",
        "evidence",
        "feedback",
        "confidence",
        "needs_review",
        "review_reason",
    ],
    "additionalProperties": False,
}


def _key_context(question: Question, entry: KeyEntry) -> str:
    """The shared marking context for one question — stable across the cohort,
    so it sits in the cached system prompt."""
    parts = [
        "You are marking one question of a paper-based school assessment.",
        "You will see the scanned image of ONE student's handwritten answer zone.",
        "Mark strictly against the key below. Transcribe what the student wrote",
        "(so transcription errors are visible), cite evidence for each criterion",
        "awarded, and write one sentence of warm, specific student feedback.",
        "If the response is illegible, blank, or ambiguous (e.g. an MCQ with two",
        "bubbles filled or heavy erasures), set needs_review=true and award",
        "conservatively — never guess.",
        "",
        f"Question {question.id} ({question.type.value}, {entry.marks} marks):",
        question.stem,
    ]
    if question.type is QuestionType.mcq and question.options:
        parts.append("Options: " + "; ".join(f"{k}) {v}" for k, v in sorted(question.options.items())))
        parts.append(f"Correct answer: {entry.correct}")
        if entry.distractor_notes:
            notes = "; ".join(f"{k}: {v}" for k, v in entry.distractor_notes.items() if v)
            if notes:
                parts.append(f"Distractor notes: {notes}")
    if entry.criteria:
        parts.append("Criteria:")
        parts += [f"- [{c.marks}] {c.point}" for c in entry.criteria]
    if entry.accept:
        parts.append("Accept: " + "; ".join(entry.accept))
    if entry.reject:
        parts.append("Reject: " + "; ".join(entry.reject))
    if entry.rubric:
        parts.append("Rubric bands:")
        parts += [f"- {b.band}: {b.descriptor}" for b in entry.rubric]
    if entry.final_answer is not None:
        tol = f" (tolerance ±{entry.tolerance})" if entry.tolerance else ""
        parts.append(f"Expected final answer: {entry.final_answer}{tol}")
    return "\n".join(parts)


def _image_block(path) -> dict:
    data = base64.standard_b64encode(path.read_bytes()).decode("ascii")
    return {"type": "image", "source": {"type": "base64", "media_type": "image/png", "data": data}}


def _user_content(item: MarkItem) -> list[dict]:
    content: list[dict] = [_image_block(item.crop_path)]
    if item.final_crop_path is not None:
        content.append({"type": "text", "text": "The separated final-answer cell:"})
        content.append(_image_block(item.final_crop_path))
    content.append({"type": "text", "text": "Mark this response."})
    return content


class AnthropicMarker:
    """Marker backed by the Anthropic API. `client` is injectable for tests."""

    def __init__(self, client: Optional[Any] = None, model: str = MODEL, use_batches: bool = False):
        if client is None:
            try:
                import anthropic
            except ImportError as exc:
                raise RuntimeError(
                    "The Anthropic marker needs the 'ai' extra: uv sync --extra ai"
                ) from exc
            client = anthropic.Anthropic()
        self.client = client
        self.model = model
        self.use_batches = use_batches
        self.name = f"anthropic:{model}"

    # -- request construction (pure; unit-testable without a client) --------

    def build_request(self, question: Question, entry: KeyEntry, item: MarkItem) -> dict:
        return {
            "model": self.model,
            "max_tokens": MAX_TOKENS,
            "thinking": {"type": "adaptive"},
            "system": [
                {
                    "type": "text",
                    "text": _key_context(question, entry),
                    # Shared across the cohort — cached so each student pays
                    # only for their crop + completion (brief 4.4).
                    "cache_control": {"type": "ephemeral"},
                }
            ],
            "output_config": {"format": {"type": "json_schema", "schema": _JUDGEMENT_SCHEMA}},
            "messages": [{"role": "user", "content": _user_content(item)}],
        }

    def _to_judgement(self, question_id: str, student_id: str, payload: dict) -> Judgement:
        return Judgement(
            student=student_id,
            question=question_id,
            marks_awarded=float(payload["marks_awarded"]),
            criteria_met=list(payload.get("criteria_met") or []),
            option_chosen=payload.get("option_chosen"),
            transcription=payload.get("transcription", ""),
            evidence=payload.get("evidence", ""),
            feedback=payload.get("feedback", ""),
            confidence=float(payload.get("confidence", 0.0)),
            review_reason=(payload.get("review_reason") if payload.get("needs_review") else None),
        )

    def _parse_response(self, question_id: str, student_id: str, message: Any) -> Judgement:
        if getattr(message, "stop_reason", None) == "refusal":
            return Judgement(
                student=student_id,
                question=question_id,
                status=JudgementStatus.error,
                review_reason="marker refused this item",
            )
        text = next(b.text for b in message.content if b.type == "text")
        return self._to_judgement(question_id, student_id, json.loads(text))

    # -- marking -------------------------------------------------------------

    def mark_question(
        self, question: Question, entry: KeyEntry, items: list[MarkItem]
    ) -> list[Judgement]:
        if self.use_batches and len(items) > 1:
            return self._mark_via_batch(question, entry, items)
        out = []
        for item in items:
            try:
                message = self.client.messages.create(**self.build_request(question, entry, item))
                out.append(self._parse_response(question.id, item.student_id, message))
            except Exception as exc:  # keep the run going; surface per-item errors
                out.append(
                    Judgement(
                        student=item.student_id,
                        question=question.id,
                        status=JudgementStatus.error,
                        review_reason=f"marker error: {exc}",
                    )
                )
        return out

    def _mark_via_batch(
        self, question: Question, entry: KeyEntry, items: list[MarkItem]
    ) -> list[Judgement]:
        requests = [
            {
                "custom_id": f"{question.id}--{item.student_id}",
                "params": self.build_request(question, entry, item),
            }
            for item in items
        ]
        batch = self.client.messages.batches.create(requests=requests)
        while True:
            batch = self.client.messages.batches.retrieve(batch.id)
            if batch.processing_status == "ended":
                break
            time.sleep(15)

        by_student: dict[str, Judgement] = {}
        for result in self.client.messages.batches.results(batch.id):
            sid = result.custom_id.split("--", 1)[1]
            if result.result.type == "succeeded":
                by_student[sid] = self._parse_response(question.id, sid, result.result.message)
            else:
                by_student[sid] = Judgement(
                    student=sid,
                    question=question.id,
                    status=JudgementStatus.error,
                    review_reason=f"batch result: {result.result.type}",
                )
        # Results arrive unordered; return in item order for stable output.
        return [
            by_student.get(
                i.student_id,
                Judgement(
                    student=i.student_id,
                    question=question.id,
                    status=JudgementStatus.error,
                    review_reason="missing from batch results",
                ),
            )
            for i in items
        ]
