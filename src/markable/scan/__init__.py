"""`scan` — match scanned scripts back to the paper and crop every answer zone.

Pipeline per scanned page::

    raster page ──► find 4 registration marks ──► homography onto the mm grid
                ──► read QR (test_id, version_hash, page_number)
                ──► flip 180° if the QR isn't top-right
                ──► attach a student id (id-map / interactive / AI vision later)
                ──► crop every zone from manifest.json ──► scripts/<sid>/<qid>.png

Everything here is offline (OpenCV only). Reading *handwritten* student IDs via
vision is an AI-extra concern; in the offline flow the ID comes from an id-map
file or an interactive prompt, with the cropped ID box saved beside the report
so the teacher can check it.

Requires the `scan` extra: ``uv sync --extra scan``.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Callable, Optional

import numpy as np

from ..models import (
    Manifest,
    PageStatus,
    ScannedPage,
    ScanReport,
    StudentCoverage,
)
from ..qr import parse_payload
from . import crop as crop_mod
from . import pdfio, qr_read, register

# (source_name, source_index, paper_page_number, id_crop_path) -> student id or None
IdResolver = Callable[[str, int, int, Optional[Path]], Optional[str]]

UNASSIGNED_DIR = "_unassigned"
OUT_DPI = 300.0


def _student_for(
    source: str,
    index: int,
    page_number: int,
    id_map: Optional[dict],
    id_resolver: Optional[IdResolver],
    id_crop_path: Optional[Path],
) -> Optional[str]:
    if id_map:
        for key in (f"{source}:{index}", source):
            if key in id_map:
                return str(id_map[key])
    if id_resolver is not None:
        return id_resolver(source, index, page_number, id_crop_path)
    return None


def _save_id_crop(canonical: np.ndarray, manifest_page, package_dir: Path, source: str, index: int) -> Optional[Path]:
    """Crop the student-ID box so the teacher (or vision, later) can read it."""
    import cv2

    if manifest_page.id_box is None:
        return None
    ppm = OUT_DPI / 25.4
    img = crop_mod._slice(canonical, manifest_page.id_box, ppm, crop_mod.PAD_MM)
    out_dir = package_dir / "scripts" / "_id_boxes"
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"{Path(source).stem}_p{index}.png"
    cv2.imwrite(str(path), img)
    return path


def scan_package(
    package_dir: Path,
    inputs: list[Path],
    dpi: float = 300.0,
    id_map: Optional[dict] = None,
    id_resolver: Optional[IdResolver] = None,
) -> ScanReport:
    """Process scanned PDFs/images against the package's manifest."""
    import cv2

    manifest = Manifest.model_validate(
        json.loads((package_dir / "manifest.json").read_text(encoding="utf-8"))
    )
    pages_by_number = {p.number: p for p in manifest.pages}
    scripts_dir = package_dir / "scripts"
    scripts_dir.mkdir(exist_ok=True)

    results: list[ScannedPage] = []

    for raw in pdfio.load_pages(inputs, dpi=dpi):
        entry = ScannedPage(source=raw.source, source_index=raw.index, status=PageStatus.ok)
        results.append(entry)

        canonical = register.deskew(raw.gray, raw.dpi, out_dpi=OUT_DPI)
        if canonical is None:
            entry.status = PageStatus.no_fiducials
            entry.detail = "registration marks not found"
            continue

        payload, points = qr_read.read_qr(canonical)
        if payload is None:
            entry.status = PageStatus.no_qr
            entry.detail = "QR unreadable after deskew"
            continue

        # The four fiducials are rotationally symmetric, so a 180°-rotated scan
        # deskews upside down. The QR must sit top-right; if not, flip.
        h, w = canonical.shape
        if points is not None and not qr_read.qr_in_top_right(points, w, h):
            canonical = cv2.rotate(canonical, cv2.ROTATE_180)

        try:
            data = parse_payload(payload)
        except ValueError as exc:
            entry.status = PageStatus.no_qr
            entry.detail = f"bad QR payload: {exc}"
            continue

        if data["test_id"] != manifest.test_id or data["version_hash"] != manifest.version_hash:
            entry.status = PageStatus.wrong_test
            entry.detail = (
                f"QR is for {data['test_id']}@{data['version_hash']}, package is "
                f"{manifest.test_id}@{manifest.version_hash}"
            )
            continue

        page_number = int(data["page_number"])
        manifest_page = pages_by_number.get(page_number)
        if manifest_page is None:
            entry.status = PageStatus.wrong_test
            entry.detail = f"QR page {page_number} not in manifest"
            continue
        entry.page_number = page_number

        id_crop = _save_id_crop(canonical, manifest_page, package_dir, raw.source, raw.index)
        student = _student_for(raw.source, raw.index, page_number, id_map, id_resolver, id_crop)
        entry.student_id = student

        if student:
            target = scripts_dir / student
        else:
            entry.status = PageStatus.unassigned
            target = scripts_dir / UNASSIGNED_DIR / f"{Path(raw.source).stem}_p{raw.index}"

        entry.crops = crop_mod.crop_page(canonical, manifest_page, OUT_DPI, target, package_dir)

    report = ScanReport(
        test_id=manifest.test_id,
        version_hash=manifest.version_hash,
        total_pages_expected=manifest.total_pages,
        pages=results,
        students=_coverage(results, manifest.total_pages),
    )
    (package_dir / "scan_report.json").write_text(
        json.dumps(report.model_dump(mode="json"), indent=2), encoding="utf-8"
    )
    return report


def _coverage(pages: list[ScannedPage], total_pages: int) -> list[StudentCoverage]:
    by_student: dict[str, list[ScannedPage]] = {}
    for p in pages:
        if p.status is PageStatus.ok and p.student_id:
            by_student.setdefault(p.student_id, []).append(p)

    out = []
    expected = set(range(1, total_pages + 1))
    for sid in sorted(by_student):
        found = sorted({p.page_number for p in by_student[sid] if p.page_number})
        blanks = sorted(
            c.question_id for p in by_student[sid] for c in p.crops if c.blank
        )
        out.append(
            StudentCoverage(
                student_id=sid,
                pages_found=found,
                pages_missing=sorted(expected - set(found)),
                blank_questions=blanks,
            )
        )
    return out
