"""Deterministic page-layout engine — the crux of Phase 1.

Computes every page's geometry in **millimetres**, origin top-left. This is the
single source of truth: `typst_render` reads the placed elements to emit absolute
Typst positions, and `manifest` reads the same placed zones to emit bounding
boxes. Because both consume this one computation, the printed paper and the
manifest coordinates agree by construction — which is what makes later
per-question cropping (`scan`) reliable.

All constants are A4 in mm. Answer-zone heights are per question type; questions
flow top-to-bottom and paginate when they no longer fit.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Optional

from ..models import Assessment, BBox, Question, QuestionType, RegistrationMarks
from ..qr import make_payload

# --- Page geometry (A4, millimetres) ---------------------------------------
PAGE_W = 210.0
PAGE_H = 297.0
MARGIN = 15.0  # left/right content margin
BOTTOM_MARGIN = 15.0
HEADER_TOP = 8.0  # header band starts here
CONTENT_TOP = 34.0  # first question starts below the header band
CONTENT_X = MARGIN
CONTENT_W = PAGE_W - 2 * MARGIN
CONTENT_BOTTOM = PAGE_H - BOTTOM_MARGIN

# --- Registration fiducials (centres, mm) ----------------------------------
REG_OFFSET = 8.0
REG_SIZE = 5.0  # side length of each corner mark

# --- Header furniture -------------------------------------------------------
QR_SIZE = 22.0
QR_X = PAGE_W - MARGIN - QR_SIZE
QR_Y = HEADER_TOP + 2.0
ID_BOX_W = 60.0
ID_BOX_H = 14.0

# --- Answer-zone heights by type (mm) --------------------------------------
ZONE_H: dict[QuestionType, float] = {
    QuestionType.mcq: 12.0,
    QuestionType.short_answer: 26.0,
    QuestionType.numerical: 46.0,
    QuestionType.extended: 74.0,
    QuestionType.diagram: 74.0,
}
FINAL_ANSWER_H = 12.0  # separated final-answer cell for numerical zones

# --- Text estimation (rough, for pagination only) --------------------------
LINE_H = 5.0
CHARS_PER_LINE = 88
STEM_PAD = 3.0
GAP_STEM_ZONE = 2.0
BLOCK_GAP = 7.0
MCQ_BUBBLE_D = 6.0  # bubble diameter


def id_box_bbox() -> BBox:
    """Student-ID box in the header — same bbox drawn by typst_render and
    recorded in the manifest so `scan` can crop it for vision ID reading."""
    return BBox(x=QR_X - ID_BOX_W - 6.0, y=HEADER_TOP, w=ID_BOX_W, h=ID_BOX_H)


def registration_marks() -> RegistrationMarks:
    return RegistrationMarks(
        top_left=(REG_OFFSET, REG_OFFSET),
        top_right=(PAGE_W - REG_OFFSET, REG_OFFSET),
        bottom_left=(REG_OFFSET, PAGE_H - REG_OFFSET),
        bottom_right=(PAGE_W - REG_OFFSET, PAGE_H - REG_OFFSET),
    )


@dataclass
class PlacedZone:
    question: Question
    bbox: BBox
    final_answer_bbox: Optional[BBox] = None


@dataclass
class PlacedQuestion:
    question: Question
    stem_bbox: BBox
    zone: PlacedZone


@dataclass
class LaidOutPage:
    number: int
    registration: RegistrationMarks
    qr_payload: str
    questions: list[PlacedQuestion] = field(default_factory=list)


@dataclass
class LaidOutPaper:
    assessment: Assessment
    version_hash: str
    page_w: float
    page_h: float
    pages: list[LaidOutPage]


def _stem_height(q: Question) -> float:
    """Estimate stem block height (incl. MCQ option lines) for pagination."""
    text = q.stem or q.id
    lines = max(1, math.ceil(len(text) / CHARS_PER_LINE))
    if q.type is QuestionType.mcq and q.options:
        lines += len(q.options)
    return lines * LINE_H + STEM_PAD


def _block_height(q: Question) -> float:
    return _stem_height(q) + GAP_STEM_ZONE + ZONE_H[q.type] + BLOCK_GAP


def lay_out(assessment: Assessment, version_hash: str) -> LaidOutPaper:
    """Flow questions onto pages, computing zone bboxes as we go."""
    pages: list[LaidOutPage] = []
    reg = registration_marks()

    def new_page() -> LaidOutPage:
        number = len(pages) + 1
        page = LaidOutPage(
            number=number,
            registration=reg,
            qr_payload=make_payload(assessment.test_id, version_hash, number),
        )
        pages.append(page)
        return page

    page = new_page()
    y = CONTENT_TOP

    for q in assessment.questions:
        block_h = _block_height(q)
        if y + block_h > CONTENT_BOTTOM and page.questions:
            page = new_page()
            y = CONTENT_TOP

        stem_h = _stem_height(q)
        stem_bbox = BBox(x=CONTENT_X, y=y, w=CONTENT_W, h=stem_h)
        zone_y = y + stem_h + GAP_STEM_ZONE
        zone_bbox = BBox(x=CONTENT_X, y=zone_y, w=CONTENT_W, h=ZONE_H[q.type])

        final_bbox = None
        if q.type is QuestionType.numerical:
            # Final-answer cell pinned to the bottom of the working box, so the
            # final answer is always in a predictable location (brief 4.2).
            final_bbox = BBox(
                x=CONTENT_X,
                y=zone_y + ZONE_H[q.type] - FINAL_ANSWER_H,
                w=CONTENT_W,
                h=FINAL_ANSWER_H,
            )

        page.questions.append(
            PlacedQuestion(
                question=q,
                stem_bbox=stem_bbox,
                zone=PlacedZone(question=q, bbox=zone_bbox, final_answer_bbox=final_bbox),
            )
        )
        y += block_h

    return LaidOutPaper(
        assessment=assessment,
        version_hash=version_hash,
        page_w=PAGE_W,
        page_h=PAGE_H,
        pages=pages,
    )
