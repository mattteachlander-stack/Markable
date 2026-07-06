"""`ingest` — parse a teacher's draft into the canonical `assessment.yaml`.

Phase 1 implements the fully-offline **markdown** path: a lightly-structured
markdown draft is parsed deterministically into an `Assessment`. This keeps the
round trip testable without any API key.

The `.docx` / `.pdf` path described in the brief (section 4.1) uses Claude to
extract structure from unstructured documents; it is scaffolded in
`ingest_ai.py` and raises a clear "not available in Phase 1 without
ANTHROPIC_API_KEY" message rather than silently doing nothing.

Draft markdown format
---------------------
A header block of ``key: value`` lines, then one ``## <id> [<type>, <marks>]``
section per question. Example::

    # Year 9 Chemistry Test
    test_id: 2026-T3-Y9-chem
    subject: Science
    year: 9

    ## Q1 [mcq, 1]
    What is the charge on a proton?
    - A) negative
    - B) neutral
    - C) positive *
    - D) variable

    ## Q6a [short_answer, 2]
    Define an exothermic reaction.

- ``marks`` may be omitted (``## Q4 [extended]``); the gap is resolved
  interactively ("Q4 has no marks allocated — how many?").
- For MCQ, ``- A) text`` lines are options and a trailing ``*`` marks the
  correct answer (an answer already embedded in the draft).
- A trailing part letter (``Q6a``) links the question to a stem parent (``Q6``).
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Optional

import yaml

from .models import Assessment, Question, QuestionType

# `## Q07a [short_answer, 2]`  or  `## Q4 [extended]`
_HEADER_RE = re.compile(r"^##\s+(?P<id>\S+)\s*\[(?P<attrs>[^\]]+)\]\s*$")
# `- C) positive *`
_OPTION_RE = re.compile(r"^[-*]\s*(?P<label>[A-Z])[).]\s*(?P<text>.*?)\s*(?P<correct>\*)?\s*$")
_KEYVAL_RE = re.compile(r"^(?P<key>[A-Za-z_]+):\s*(?P<val>.+?)\s*$")

# A gap the parser could not fill from the draft alone.
GapResolver = Callable[[str, "Gap"], object]


@dataclass
class Gap:
    """A missing field the teacher must supply (brief section 4.1)."""

    question_id: str
    field: str  # e.g. "marks"
    prompt: str


@dataclass
class _PartialQuestion:
    id: str
    type: QuestionType
    marks: Optional[int]
    stem_lines: list[str] = field(default_factory=list)
    options: dict[str, str] = field(default_factory=dict)
    correct: Optional[str] = None


class IngestError(ValueError):
    """Raised when a draft cannot be parsed into a valid assessment."""


def _parse_attrs(raw: str, qid: str) -> tuple[QuestionType, Optional[int]]:
    """Parse ``mcq, 2`` / ``extended`` / ``short_answer, marks=2`` bracket body."""
    parts = [p.strip() for p in raw.split(",") if p.strip()]
    if not parts:
        raise IngestError(f"{qid}: empty question attributes")
    try:
        qtype = QuestionType(parts[0])
    except ValueError as exc:
        valid = ", ".join(t.value for t in QuestionType)
        raise IngestError(f"{qid}: unknown type '{parts[0]}' (expected one of: {valid})") from exc

    marks: Optional[int] = None
    for token in parts[1:]:
        token = token.removeprefix("marks=").strip()
        if token:
            try:
                marks = int(token)
            except ValueError as exc:
                raise IngestError(f"{qid}: marks '{token}' is not an integer") from exc
    return qtype, marks


def parse_markdown(text: str) -> tuple[dict, list[_PartialQuestion]]:
    """Parse draft markdown into ``(meta, partial_questions)``.

    `meta` carries test_id/title/subject/year_level; questions may still have
    unresolved gaps (e.g. `marks is None`).
    """
    meta: dict = {}
    partials: list[_PartialQuestion] = []
    current: Optional[_PartialQuestion] = None
    seen_question = False

    for line in text.splitlines():
        header = _HEADER_RE.match(line)
        if header:
            seen_question = True
            qtype, marks = _parse_attrs(header["attrs"], header["id"])
            current = _PartialQuestion(id=header["id"], type=qtype, marks=marks)
            partials.append(current)
            continue

        if current is None:
            # Pre-question header block: `# Title` and `key: value` lines.
            if line.startswith("# "):
                meta.setdefault("title", line[2:].strip())
                continue
            kv = _KEYVAL_RE.match(line)
            if kv and not seen_question:
                meta[kv["key"].lower()] = kv["val"].strip()
            continue

        # Inside a question body.
        if current.type is QuestionType.mcq:
            opt = _OPTION_RE.match(line.strip())
            if opt:
                current.options[opt["label"]] = opt["text"].strip()
                if opt["correct"]:
                    current.correct = opt["label"]
                continue
        if line.strip():
            current.stem_lines.append(line.strip())

    if not partials:
        raise IngestError("draft contains no questions (expected '## <id> [type, marks]' headers)")
    return meta, partials


def _default_prompt(qid: str, gap: Gap) -> str:
    return gap.prompt


def resolve(
    partials: list[_PartialQuestion],
    resolver: Optional[GapResolver] = None,
    assume_yes: bool = False,
) -> list[Question]:
    """Fill gaps and build validated `Question` objects.

    `resolver(question_id, gap)` returns the teacher's answer. When `assume_yes`
    is set and a resolver is not supplied, unresolved gaps raise — so
    non-interactive runs require a complete draft.
    """
    questions: list[Question] = []
    for p in partials:
        marks = p.marks
        if marks is None:
            gap = Gap(p.id, "marks", f"{p.id} has no marks allocated — how many?")
            if resolver is not None:
                marks = int(resolver(p.id, gap))  # type: ignore[arg-type]
            elif assume_yes:
                raise IngestError(
                    f"{p.id} is missing marks; cannot resolve in non-interactive mode. "
                    "Add '[type, marks]' to the draft or run interactively."
                )
            else:
                raise IngestError(f"unresolved gap: {gap.prompt}")

        parent = _stem_parent(p.id)
        questions.append(
            Question(
                id=p.id,
                type=p.type,
                marks=marks,
                stem=" ".join(p.stem_lines).strip(),
                parent=parent,
                options=p.options or None,
                expected_answer=p.correct if p.type is QuestionType.mcq else None,
            )
        )
    return questions


def _stem_parent(qid: str) -> Optional[str]:
    """`Q07a` -> `Q07`; `Q07` -> None."""
    m = re.match(r"^(Q\d+)([a-z]+)$", qid)
    return m.group(1) if m else None


def ingest_markdown(
    text: str,
    resolver: Optional[GapResolver] = None,
    assume_yes: bool = False,
) -> Assessment:
    """Parse markdown draft text into a validated `Assessment`."""
    meta, partials = parse_markdown(text)
    questions = resolve(partials, resolver=resolver, assume_yes=assume_yes)

    test_id = meta.get("test_id")
    if not test_id:
        raise IngestError("draft header must define 'test_id:'")

    return Assessment(
        test_id=test_id,
        title=meta.get("title", ""),
        subject=meta.get("subject", ""),
        year_level=str(meta.get("year", meta.get("year_level", ""))),
        questions=questions,
    )


def ingest_file(
    path: Path,
    resolver: Optional[GapResolver] = None,
    assume_yes: bool = False,
) -> Assessment:
    """Dispatch on file extension. Only `.md` is implemented in Phase 1."""
    suffix = path.suffix.lower()
    if suffix in {".md", ".markdown", ".txt"}:
        return ingest_markdown(path.read_text(encoding="utf-8"), resolver, assume_yes)
    if suffix in {".docx", ".pdf"}:
        from .ingest_ai import ingest_document

        return ingest_document(path, resolver=resolver, assume_yes=assume_yes)
    raise IngestError(f"unsupported draft format '{suffix}' (expected .md, .docx, or .pdf)")


def write_assessment(assessment: Assessment, path: Path) -> Path:
    """Serialise an assessment to `assessment.yaml` (human-editable)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    data = assessment.model_dump(mode="json", exclude_none=True)
    path.write_text(
        yaml.safe_dump(data, sort_keys=False, allow_unicode=True),
        encoding="utf-8",
    )
    return path


def load_assessment(path: Path) -> Assessment:
    """Load and validate an `assessment.yaml`."""
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    return Assessment.model_validate(data)
