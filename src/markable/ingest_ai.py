"""Claude-assisted ingestion of unstructured `.docx` / `.pdf` drafts.

The brief (section 4.1) specifies that Markable uses Claude to extract a
structured question list from Word/PDF drafts. That path is **scaffolded but not
built in Phase 1** — Phase 1's exit criterion is a print/scan round trip driven
by the deterministic markdown path, and no marking/vision code is written until
that passes (brief section 11.3).

This module marks the seam clearly: calling it without the optional `ai` extra
and an `ANTHROPIC_API_KEY` raises a helpful error instead of failing obscurely.
When implemented, it must return the same validated `Assessment` as the markdown
path, so everything downstream is identical regardless of draft source.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Callable, Optional

from .models import Assessment


class AIIngestUnavailable(RuntimeError):
    """Raised when the AI ingestion path is requested but not usable."""


def ingest_document(
    path: Path,
    resolver: Optional[Callable] = None,
    assume_yes: bool = False,
) -> Assessment:
    """Extract structure from a `.docx`/`.pdf` draft using Claude (Phase 1b).

    Not implemented in Phase 1. Fails loudly with guidance so the boundary is
    obvious to anyone extending the tool.
    """
    if not os.environ.get("ANTHROPIC_API_KEY"):
        raise AIIngestUnavailable(
            f"Ingesting '{path.name}' requires Claude-assisted parsing, which needs "
            "ANTHROPIC_API_KEY and the optional 'ai' extra (uv sync --extra ai). "
            "In Phase 1, convert your draft to the markdown format instead "
            "(see fixtures/drafts/y9-chem-test.md)."
        )
    raise AIIngestUnavailable(
        "AI-assisted .docx/.pdf ingestion is scaffolded but not implemented in Phase 1. "
        "It will be built once the Phase 1 print/scan round trip is validated."
    )
