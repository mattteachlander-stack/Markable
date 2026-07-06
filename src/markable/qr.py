"""Per-page QR payloads.

Every page carries a QR encoding ``{test_id, version_hash, page_number}`` so
pages can be matched even if scans arrive shuffled or upside down (brief 4.2).
The payload is a compact, sorted JSON string; `scan` (Phase 2) will read it back
with `parse_payload`.
"""

from __future__ import annotations

import json
from pathlib import Path

import segno


def make_payload(test_id: str, version_hash: str, page_number: int) -> str:
    """Build the canonical QR payload string for one page.

    Sorted keys + compact separators make the payload deterministic, so the same
    page always produces byte-identical QR content (useful for tests and diffs).
    """
    return json.dumps(
        {"test_id": test_id, "version_hash": version_hash, "page_number": page_number},
        sort_keys=True,
        separators=(",", ":"),
    )


def parse_payload(payload: str) -> dict:
    """Parse a QR payload string back into its fields (used by `scan`)."""
    data = json.loads(payload)
    expected = {"test_id", "version_hash", "page_number"}
    missing = expected - data.keys()
    if missing:
        raise ValueError(f"QR payload missing fields: {sorted(missing)}")
    return data


def write_png(payload: str, path: Path, scale: int = 8, border: int = 2) -> Path:
    """Render `payload` as a QR PNG at `path` for embedding in the paper."""
    path.parent.mkdir(parents=True, exist_ok=True)
    qr = segno.make(payload, error="m")
    qr.save(str(path), scale=scale, border=border)
    return path
