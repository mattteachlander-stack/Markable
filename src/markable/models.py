"""Canonical data models for Markable.

These Pydantic models are the *authoritative* definitions of every persisted
artifact. They are the code equivalent of the schemas sketched in the brief
(sections 4.1, 4.2, 9.1, 10.1) and are the single source of truth — the YAML
and JSON files on disk are just serialisations of these types.

Grouping:
- Assessment layer  : the canonical structured assessment (`assessment.yaml`).
- Marking pack      : the answer key + rubrics (`key.yaml`).
- Package manifest  : test id, version hash, page map, answer-zone bboxes
                      (`manifest.json`).
- Curriculum packs  : Part 2 curriculum representation (`pack.yaml`).
- Star schema       : the Part 1 reporting contract (section 10.1). Defined now
                      even though `report` is a later phase, so Parts 2-3 are
                      purely additive (brief section 11.1).
"""

from __future__ import annotations

from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field, model_validator

# ---------------------------------------------------------------------------
# Assessment layer — assessment.yaml
# ---------------------------------------------------------------------------


class QuestionType(str, Enum):
    """The five question types v1 must handle (brief section 2)."""

    mcq = "mcq"
    short_answer = "short_answer"
    numerical = "numerical"
    extended = "extended"
    diagram = "diagram"


class Stimulus(BaseModel):
    """Optional stimulus material attached to a question (image, data table)."""

    kind: str  # "image" | "table" | "text"
    caption: Optional[str] = None
    # Path (relative to the draft/package) for images, or inline content for
    # small tables/text. Kept deliberately loose in Phase 1.
    ref: Optional[str] = None
    content: Optional[str] = None


class Question(BaseModel):
    """One question or question-part.

    A multi-part question is represented as several `Question` entries that
    share a `parent` stem id (e.g. Q07a, Q07b under Q07). Question ids are
    stable and never renumbered once a paper is finalised.
    """

    id: str = Field(..., description="Stable unique id, e.g. 'Q07a'.")
    type: QuestionType
    marks: int = Field(..., ge=0)
    stem: str = ""
    parent: Optional[str] = Field(
        default=None, description="Stem id for multi-part questions, e.g. 'Q07'."
    )
    stimulus: list[Stimulus] = Field(default_factory=list)
    # MCQ options as a mapping of label -> text, e.g. {"A": "...", "B": "..."}.
    options: Optional[dict[str, str]] = None
    # Curriculum tags are written here by Part 2 `markable tag`; empty in Phase 1.
    outcome_codes: list[str] = Field(default_factory=list)
    # Free-form hints captured at ingest to seed the marking pack later.
    expected_answer: Optional[str] = None

    @model_validator(mode="after")
    def _check_mcq_options(self) -> "Question":
        if self.type is QuestionType.mcq and not self.options:
            raise ValueError(f"MCQ {self.id} must define options")
        return self


class Assessment(BaseModel):
    """The canonical structured assessment — `assessment.yaml`.

    Single source of truth for everything downstream (brief section 4.1).
    """

    test_id: str
    title: str = ""
    subject: str = ""
    year_level: str = ""
    questions: list[Question]

    @property
    def total_marks(self) -> int:
        return sum(q.marks for q in self.questions)

    @model_validator(mode="after")
    def _unique_ids(self) -> "Assessment":
        ids = [q.id for q in self.questions]
        dupes = {i for i in ids if ids.count(i) > 1}
        if dupes:
            raise ValueError(f"Duplicate question ids: {sorted(dupes)}")
        return self


# ---------------------------------------------------------------------------
# Marking pack — key.yaml
# ---------------------------------------------------------------------------


class Criterion(BaseModel):
    """A single mark-earning criterion (brief section 4.2)."""

    point: str
    marks: int = Field(..., ge=0)


class RubricBand(BaseModel):
    """A banded rubric row for extended responses."""

    band: str
    descriptor: str


class KeyEntry(BaseModel):
    """Marking-pack entry for one question."""

    id: str
    type: QuestionType
    marks: int = Field(..., ge=0)

    # MCQ
    correct: Optional[str] = None
    distractor_notes: Optional[dict[str, str]] = None

    # short_answer / numerical / diagram
    criteria: list[Criterion] = Field(default_factory=list)
    accept: list[str] = Field(default_factory=list)
    reject: list[str] = Field(default_factory=list)

    # numerical
    final_answer: Optional[str] = None
    tolerance: Optional[float] = None

    # extended
    rubric: list[RubricBand] = Field(default_factory=list)

    # Below this marking confidence the item goes to the review queue.
    # Diagram/extended default higher; see mark-engine policy (Phase 3).
    review_threshold: float = 0.85


class Key(BaseModel):
    """The marking pack — `key.yaml` (brief section 4.2)."""

    test_id: str
    total_marks: int
    questions: list[KeyEntry]


# ---------------------------------------------------------------------------
# Package manifest — manifest.json
# ---------------------------------------------------------------------------


class BBox(BaseModel):
    """Axis-aligned bounding box in millimetres, origin top-left of the page.

    Millimetres (not pixels) so the manifest is resolution-independent: `scan`
    deskews to the registration marks, then converts mm -> pixels at whatever
    DPI the scanner produced.
    """

    x: float
    y: float
    w: float
    h: float


class Zone(BaseModel):
    """One answer zone on the page (brief section 4.2 "Answer Zone")."""

    question_id: str
    kind: QuestionType
    bbox: BBox
    # For numerical zones: the separated final-answer cell (brief section 4.2).
    final_answer_bbox: Optional[BBox] = None


class RegistrationMarks(BaseModel):
    """Centres of the four corner fiducials in mm, for deskew + coordinate lock."""

    top_left: tuple[float, float]
    top_right: tuple[float, float]
    bottom_left: tuple[float, float]
    bottom_right: tuple[float, float]


class Page(BaseModel):
    """One printed page and everything on it needed to locate answers."""

    number: int
    width_mm: float
    height_mm: float
    registration: RegistrationMarks
    qr_payload: str  # exact string encoded in this page's QR (see qr.py)
    zones: list[Zone] = Field(default_factory=list)


class Manifest(BaseModel):
    """`manifest.json` — the map that makes per-question cropping deterministic.

    Records the exact bounding box of every answer zone per page (brief 4.2).
    """

    test_id: str
    version_hash: str
    total_pages: int
    pages: list[Page]


# ---------------------------------------------------------------------------
# Curriculum packs — pack.yaml (Part 2; models defined early, unused in Phase 1)
# ---------------------------------------------------------------------------


class Dimension(BaseModel):
    id: str
    name: Optional[str] = None


class Outcome(BaseModel):
    code: str
    level: str
    dimension: str
    strand: str
    description: str
    elaborations: list[str] = Field(default_factory=list)


class AchievementStatement(BaseModel):
    id: str
    maps_to: list[str] = Field(default_factory=list)
    text: str


class AchievementStandard(BaseModel):
    level: str
    statements: list[AchievementStatement] = Field(default_factory=list)


class Misconception(BaseModel):
    id: str
    outcome_codes: list[str] = Field(default_factory=list)
    text: str


class CurriculumPack(BaseModel):
    """A structured, versioned representation of an official curriculum (9.1)."""

    curriculum: str
    version: str
    levels: list[str]
    dimensions: list[Dimension]
    outcomes: list[Outcome]
    achievement_standards: list[AchievementStandard] = Field(default_factory=list)
    misconception_library: list[Misconception] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Star schema — the reporting contract (section 10.1)
# ---------------------------------------------------------------------------
# Defined now so `report` can write fact_response + dims from day one. Populated
# from Phase 4 onwards; Parts 2-3 add fact_attainment/dim_outcome on top.


class FactResponse(BaseModel):
    assessment_id: str
    student_id: str
    question_id: str
    marks_awarded: float
    marks_available: float
    correct: Optional[bool] = None  # MCQ only
    option_chosen: Optional[str] = None  # MCQ only
    criteria_met_count: Optional[int] = None
    confidence: Optional[float] = None
    reviewed: bool = False
    quartile_at_assessment: Optional[int] = None


class FactAttainment(BaseModel):
    assessment_id: str
    student_id: str
    outcome_code: str
    marks_awarded: float
    marks_available: float


class DimAssessment(BaseModel):
    assessment_id: str
    title: str
    subject: str
    year_level: str
    class_group: Optional[str] = None
    teacher: Optional[str] = None
    date: Optional[str] = None
    total_marks: int
    version_hash: str


class DimQuestion(BaseModel):
    question_id: str
    type: QuestionType
    topic: Optional[str] = None
    marks: int
    difficulty: Optional[str] = None  # easy | moderate | difficult (computed)
    outcome_codes: list[str] = Field(default_factory=list)
    misconception_tags: list[str] = Field(default_factory=list)


class DimStudent(BaseModel):
    student_id: str
    class_group: Optional[str] = None
    # Name is LOCAL-ONLY and never exported (brief 7, 10.4). Joined at report
    # time from class_list.csv; kept optional and out of shared artifacts.
    name: Optional[str] = None


class DimOutcome(BaseModel):
    outcome_code: str
    strand: str
    dimension: str
    level: str
    curriculum_version: str


class DimGrading(BaseModel):
    """score band -> grade mapping (grading.yaml, section 10.2)."""

    grade: str
    low: float
    high: float
