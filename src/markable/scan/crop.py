"""Crop answer zones from a deskewed canonical page.

Coordinates come straight from `manifest.json` (mm) — after `register.deskew`
the page *is* the mm grid, so a crop is a slice. A small outward pad keeps
zone borders visible in the crop (they help the marker see the frame), and the
ink-ratio heuristic flags visibly blank responses for the review queue.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np

from ..models import BBox, CropRecord, Page

PAD_MM = 1.5  # pad each crop outward so the printed border survives
INK_INSET_MM = 2.5  # measure ink inside the border, not the border itself
INK_DARK_THRESHOLD = 120  # px darker than this count as ink (ruled lines are ~60% luma)
BLANK_INK_RATIO = 0.0015  # below this fraction of dark pixels → flagged blank


def _slice(gray: np.ndarray, bbox: BBox, ppm: float, pad_mm: float) -> np.ndarray:
    h, w = gray.shape
    x0 = max(0, round((bbox.x - pad_mm) * ppm))
    y0 = max(0, round((bbox.y - pad_mm) * ppm))
    x1 = min(w, round((bbox.x + bbox.w + pad_mm) * ppm))
    y1 = min(h, round((bbox.y + bbox.h + pad_mm) * ppm))
    return gray[y0:y1, x0:x1]


def ink_ratio(gray: np.ndarray, bbox: BBox, ppm: float) -> float:
    inner = _slice(gray, bbox, ppm, -INK_INSET_MM)
    if inner.size == 0:
        return 0.0
    return float((inner < INK_DARK_THRESHOLD).mean())


def crop_page(
    canonical: np.ndarray,
    page: Page,
    out_dpi: float,
    student_dir: Path,
    package_dir: Path,
) -> list[CropRecord]:
    """Write one PNG per answer zone (plus `_final` for numerical cells)."""
    import cv2

    ppm = out_dpi / 25.4
    student_dir.mkdir(parents=True, exist_ok=True)
    records: list[CropRecord] = []

    for zone in page.zones:
        path = student_dir / f"{zone.question_id}.png"
        cv2.imwrite(str(path), _slice(canonical, zone.bbox, ppm, PAD_MM))
        if zone.final_answer_bbox is not None:
            final_path = student_dir / f"{zone.question_id}_final.png"
            cv2.imwrite(str(final_path), _slice(canonical, zone.final_answer_bbox, ppm, PAD_MM))

        ratio = ink_ratio(canonical, zone.bbox, ppm)
        records.append(
            CropRecord(
                question_id=zone.question_id,
                path=str(path.relative_to(package_dir)),
                ink_ratio=round(ratio, 5),
                blank=ratio < BLANK_INK_RATIO,
            )
        )
    return records
