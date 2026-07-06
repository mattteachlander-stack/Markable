"""Stable identifiers and version hashing.

`version_hash` ties a scanned script to the exact paper version it was printed
from (brief section 7 "Version integrity"). It is a short, stable digest of the
canonical assessment content, so any edit to questions/marks produces a new hash
and prevents marking a script against a revised key.
"""

from __future__ import annotations

import hashlib

from .models import Assessment


def question_id(number: int, part: str | None = None) -> str:
    """Format a stable question id, e.g. (7) -> 'Q07', (7, 'a') -> 'Q07a'."""
    base = f"Q{number:02d}"
    return f"{base}{part}" if part else base


def version_hash(assessment: Assessment, length: int = 12) -> str:
    """Deterministic short digest of an assessment's canonical content.

    Uses a stable JSON serialisation (sorted keys) so the same assessment always
    hashes identically regardless of field ordering in the source YAML.
    """
    canonical = assessment.model_dump_json(exclude_none=False)
    # Re-serialise through a sorted representation for order independence.
    import json

    normalised = json.dumps(json.loads(canonical), sort_keys=True, separators=(",", ":"))
    digest = hashlib.sha256(normalised.encode("utf-8")).hexdigest()
    return digest[:length]
