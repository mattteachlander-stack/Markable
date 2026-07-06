"""Assemble `manifest.json` from the laid-out paper.

The manifest records, per page, the four registration-mark centres, the exact QR
payload, and the bounding box of every answer zone. This is the map `scan`
(Phase 2) uses to crop each question deterministically after deskewing to the
registration marks.
"""

from __future__ import annotations

from ..models import Assessment, Manifest, Page, Zone
from .layout import LaidOutPaper, id_box_bbox


def build_manifest(assessment: Assessment, paper: LaidOutPaper, version_hash: str) -> Manifest:
    pages: list[Page] = []
    for lp in paper.pages:
        zones = [
            Zone(
                question_id=pq.question.id,
                kind=pq.question.type,
                bbox=pq.zone.bbox,
                final_answer_bbox=pq.zone.final_answer_bbox,
            )
            for pq in lp.questions
        ]
        pages.append(
            Page(
                number=lp.number,
                width_mm=paper.page_w,
                height_mm=paper.page_h,
                registration=lp.registration,
                qr_payload=lp.qr_payload,
                id_box=id_box_bbox(),
                zones=zones,
            )
        )

    return Manifest(
        test_id=assessment.test_id,
        version_hash=version_hash,
        total_pages=len(pages),
        pages=pages,
    )
