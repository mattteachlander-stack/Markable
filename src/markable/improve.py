"""`improve` — send a draft test to Claude with an upgrade-instruction pack and
get back an AI-marking-ready version.

The readiness box (studio) and `markable analyse` *diagnose*; this module
*fixes*: the teacher's draft goes to Claude together with INSTRUCTION_PACK (the
codified readiness rules), and Claude returns the same test restructured into
Markable's ingest markdown — unique stable IDs, explicit marks, typed items,
answer-space cues — plus an itemised change log so the teacher can see exactly
what was altered and why. The upgraded file drops straight into
`markable ingest` → `build`.

Content discipline: the pack instructs Claude to preserve the teacher's
questions, difficulty and topic coverage — restructure, never rewrite the
assessment's substance. The teacher reviews the change log and owns the result
(human-in-the-loop, brief §2).

Privacy: a draft test contains no student data, so this path needs no
pseudonymisation. Needs the `ai` extra + ANTHROPIC_API_KEY.
"""

from __future__ import annotations

import json
import re
import zipfile
from pathlib import Path
from typing import Any, Optional

MODEL = "claude-opus-4-8"
MAX_TOKENS = 16000

# The upgrade rules — kept as data so the studio's in-browser upgrader and the
# CLI send the identical package of instructions.
INSTRUCTION_PACK = """You are upgrading a teacher's draft test so it is ready for reliable, \
auditable AI marking with Markable. Restructure it into Markable's markdown format:

# <Test title>
test_id: <year>-<term>-<class>-<subject slug>   (invent a sensible one if absent)
subject: <subject>
year: <year level, if stated or inferable>

## Q1 [<type>, <marks>]
<question stem>

Rules — apply every one:
1. UNIQUE STABLE IDS: number every question Q1, Q2 … (sub-parts Q6a, Q6b). Never renumber
   an existing explicit ID; fill gaps around it.
2. MARKS: every question states its marks in the header `[type, marks]`. If the draft
   gives no allocation, infer a defensible one from the demand of the task and flag it
   in the change log.
3. TYPE each item as one of: mcq, short_answer, numerical, extended, diagram.
   - mcq: exactly 4 options as `- A) …` to `- D) …`, mark the correct one with a trailing ` *`.
     If the draft has a correct answer stated, use it; otherwise choose and flag it.
   - numerical: the stem must ask students to show working AND give a final answer.
   - extended: the stem should name the concepts/criteria the response must cover.
   - diagram: the stem must say what must be drawn AND what must be labelled.
4. ONE CONSTRUCT PER ITEM: split double-barrelled questions into sub-parts (Q3a, Q3b),
   preserving the original intent and total marks.
5. UNAMBIGUOUS STEMS: tighten wording only where a marker could not judge the answer
   reliably (undefined referents, missing units, "discuss" with no criteria). Keep the
   teacher's voice everywhere else.
6. PRESERVE THE ASSESSMENT: same topics, same difficulty, same intent. Do not add new
   questions, delete questions, or change what is being assessed. Restructure, don't rewrite.
7. CHANGE LOG: report every change you made as {question_id, change, reason} — including
   every inference (marks, mcq answer, type) the teacher must verify.

Return JSON: improved_markdown (the complete upgraded test), changes (the log),
summary (2-3 sentences for the teacher)."""

IMPROVE_SCHEMA = {
    "type": "object",
    "properties": {
        "improved_markdown": {"type": "string"},
        "changes": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "question_id": {"type": "string"},
                    "change": {"type": "string"},
                    "reason": {"type": "string"},
                },
                "required": ["question_id", "change", "reason"],
                "additionalProperties": False,
            },
        },
        "summary": {"type": "string"},
    },
    "required": ["improved_markdown", "changes", "summary"],
    "additionalProperties": False,
}


def extract_text(path: Path) -> str:
    """Draft text from .md/.txt/.markdown or .docx (no python-docx needed —
    a .docx is a zip; paragraph text lives in word/document.xml)."""
    suffix = path.suffix.lower()
    if suffix in {".md", ".markdown", ".txt"}:
        return path.read_text(encoding="utf-8")
    if suffix == ".docx":
        with zipfile.ZipFile(path) as z:
            xml = z.read("word/document.xml").decode("utf-8", errors="replace")
        paras = re.split(r"</w:p>", xml)
        out = []
        for p in paras:
            text = "".join(re.findall(r"<w:t[^>]*>([^<]*)</w:t>", p))
            if text.strip():
                out.append(text.strip())
        return "\n".join(out)
    raise ValueError(f"unsupported draft format '{suffix}' — use .md, .txt or .docx")


def build_improve_request(draft_text: str, model: str = MODEL) -> dict:
    """Pure request construction — unit-testable without a client or key."""
    return {
        "model": model,
        "max_tokens": MAX_TOKENS,
        "thinking": {"type": "adaptive"},
        "system": [
            {
                "type": "text",
                "text": INSTRUCTION_PACK,
                # The pack is identical across every teacher's upgrade call.
                "cache_control": {"type": "ephemeral"},
            }
        ],
        "output_config": {"format": {"type": "json_schema", "schema": IMPROVE_SCHEMA}},
        "messages": [
            {
                "role": "user",
                "content": f"Upgrade this draft test:\n\n{draft_text}",
            }
        ],
    }


def run_improve(draft_text: str, client: Optional[Any] = None, model: str = MODEL) -> dict:
    """Send the draft + instruction pack to Claude; return the upgrade payload
    {improved_markdown, changes, summary}. `client` is injectable for tests."""
    if client is None:
        try:
            import anthropic
        except ImportError as exc:
            raise RuntimeError(
                "The AI test upgrader needs the 'ai' extra: uv sync --extra ai"
            ) from exc
        client = anthropic.Anthropic()

    if not draft_text.strip():
        raise ValueError("the draft is empty — nothing to upgrade")
    message = client.messages.create(**build_improve_request(draft_text, model))
    if getattr(message, "stop_reason", None) == "refusal":
        raise RuntimeError("the model declined to process this document")
    text = next(b.text for b in message.content if b.type == "text")
    return json.loads(text)
