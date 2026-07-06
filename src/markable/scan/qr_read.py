"""Read the per-page QR using OpenCV's built-in detector (no system zbar).

On a correctly-oriented canonical page the QR sits in the top-right corner
(layout.QR_X/QR_Y). `locate_and_read` also reports which quadrant the code was
found in so the orchestrator can detect a 180°-rotated deskew and flip.
"""

from __future__ import annotations

import numpy as np


def read_qr(gray: np.ndarray) -> tuple[str | None, np.ndarray | None]:
    """Decode a QR anywhere in `gray`; returns (payload, corner points 4x2).

    Deskew resampling + photocopier noise can defeat a single plain decode, so
    this walks a retry ladder of cheap preprocessing variants. Points are always
    returned in the original image's coordinates.
    """
    import cv2

    detector = cv2.QRCodeDetector()

    def attempt(img: np.ndarray, scale: float) -> tuple[str | None, np.ndarray | None]:
        payload, points, _ = detector.detectAndDecode(img)
        if payload:
            return payload, points.reshape(-1, 2) / scale if points is not None else None
        return None, None

    variants = [
        (lambda g: (g, 1.0)),  # as-is
        (lambda g: (cv2.resize(g, None, fx=2, fy=2, interpolation=cv2.INTER_CUBIC), 2.0)),
        (lambda g: (cv2.threshold(g, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)[1], 1.0)),
        (lambda g: (cv2.resize(g, None, fx=0.5, fy=0.5, interpolation=cv2.INTER_AREA), 0.5)),
    ]
    for make in variants:
        img, scale = make(gray)
        payload, points = attempt(img, scale)
        if payload:
            return payload, points
    return None, None


def qr_in_top_right(points: np.ndarray, width: int, height: int) -> bool:
    """True if the decoded QR's centre lies in the page's top-right quadrant."""
    cx, cy = points.mean(axis=0)
    return cx > width / 2 and cy < height / 2
