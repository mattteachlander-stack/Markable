"""Load scanned input (PDF or image files) as grayscale page arrays.

Uses `pypdfium2` to rasterise PDFs — a self-contained wheel, no system poppler.
Plain image files (PNG/JPG/TIFF) are accepted too, since some copiers email
per-page images rather than PDFs.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterator

import numpy as np

_IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".tif", ".tiff", ".bmp"}


@dataclass
class RawPage:
    source: str  # input file name
    index: int  # 1-based page index within the source
    gray: np.ndarray  # uint8 grayscale, as scanned (any orientation/skew)
    dpi: float  # nominal resolution the page was rasterised/scanned at


def _to_gray(arr: np.ndarray) -> np.ndarray:
    import cv2

    if arr.ndim == 2:
        return arr
    if arr.shape[2] == 4:
        arr = cv2.cvtColor(arr, cv2.COLOR_BGRA2BGR)
    return cv2.cvtColor(arr, cv2.COLOR_BGR2GRAY)


def load_pages(inputs: list[Path], dpi: float = 300.0) -> Iterator[RawPage]:
    """Yield every page of every input as a grayscale array at ~`dpi`."""
    import cv2

    for path in inputs:
        suffix = path.suffix.lower()
        if suffix == ".pdf":
            import pypdfium2 as pdfium

            doc = pdfium.PdfDocument(str(path))
            try:
                for i in range(len(doc)):
                    page = doc[i]
                    bitmap = page.render(scale=dpi / 72.0)
                    arr = bitmap.to_numpy()
                    yield RawPage(path.name, i + 1, _to_gray(arr), dpi)
            finally:
                doc.close()
        elif suffix in _IMAGE_SUFFIXES:
            arr = cv2.imread(str(path), cv2.IMREAD_GRAYSCALE)
            if arr is None:
                raise ValueError(f"could not read image {path}")
            # Infer DPI from A4 height so mm coordinates keep working: a school
            # scan is A4, so height_px / 297mm gives the effective resolution.
            inferred = max(arr.shape) / 297.0 * 25.4
            yield RawPage(path.name, 1, arr, inferred)
        else:
            raise ValueError(f"unsupported scan input '{path.name}' (PDF or image expected)")
