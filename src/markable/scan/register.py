"""Registration-mark detection and deskew.

The paper prints a solid `REG_SIZE` mm black square at each corner (centres from
`layout.registration_marks()`). We find those four blobs in the scan, then warp
the page onto the canonical millimetre grid with a homography. After `deskew`,
pixel (x, y) == millimetre (x/px_per_mm, y/px_per_mm) — exactly the coordinate
space `manifest.json` speaks — so cropping is pure arithmetic.

A 180°-rotated scan still deskews "successfully" (the four corners are
symmetric); orientation is disambiguated afterwards by the QR position (top
right on a correctly-oriented page). See `scan.__init__`.
"""

from __future__ import annotations

import numpy as np

from ..build import layout


def px_per_mm(dpi: float) -> float:
    return dpi / 25.4


def _expected_centres_px(scale: float) -> np.ndarray:
    reg = layout.registration_marks()
    return np.array(
        [reg.top_left, reg.top_right, reg.bottom_left, reg.bottom_right],
        dtype=np.float32,
    ) * scale


def find_fiducials(gray: np.ndarray, dpi: float) -> np.ndarray | None:
    """Locate the four corner squares; returns 4x2 centres (TL, TR, BL, BR order
    *by position in the scanned image*) or None if not all four are found.
    """
    import cv2

    h, w = gray.shape
    scale = px_per_mm(dpi)
    expected_side = layout.REG_SIZE * scale
    # Photocopying / rescaling tolerance on the blob area.
    min_area = (expected_side * 0.45) ** 2
    max_area = (expected_side * 2.2) ** 2

    _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
    contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    candidates: list[tuple[float, float]] = []
    for c in contours:
        area = cv2.contourArea(c)
        if not (min_area <= area <= max_area):
            continue
        x, y, bw, bh = cv2.boundingRect(c)
        aspect = bw / bh if bh else 0
        if not (0.6 <= aspect <= 1.7):
            continue
        # Solid square: contour area ≈ bounding-box area.
        if area / (bw * bh) < 0.75:
            continue
        candidates.append((x + bw / 2.0, y + bh / 2.0))

    if len(candidates) < 4:
        return None

    # Assign the best candidate to each image corner; fiducials sit within
    # ~15% of the page edges, QR/bubbles etc. live further in.
    corners = np.array([(0, 0), (w, 0), (0, h), (w, h)], dtype=np.float32)
    limit = 0.18 * max(h, w)
    picked = []
    for corner in corners:
        dists = [float(np.hypot(cx - corner[0], cy - corner[1])) for cx, cy in candidates]
        best = int(np.argmin(dists))
        if dists[best] > limit:
            return None
        picked.append(candidates[best])
    if len({tuple(p) for p in picked}) < 4:
        return None
    return np.array(picked, dtype=np.float32)


def deskew(gray: np.ndarray, dpi: float, out_dpi: float = 300.0) -> np.ndarray | None:
    """Warp the scan onto the canonical A4 mm grid at `out_dpi`.

    Returns the canonical grayscale image, or None when the registration marks
    can't be found. The result may still be 180°-rotated — the caller checks the
    QR corner and flips if needed.
    """
    import cv2

    found = find_fiducials(gray, dpi)
    if found is None:
        return None

    scale = px_per_mm(out_dpi)
    target = _expected_centres_px(scale)
    matrix = cv2.getPerspectiveTransform(found, target)
    out_size = (round(layout.PAGE_W * scale), round(layout.PAGE_H * scale))
    return cv2.warpPerspective(
        gray, matrix, out_size, flags=cv2.INTER_AREA, borderValue=255
    )
