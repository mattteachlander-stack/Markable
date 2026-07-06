"""`build` — turn an `assessment.yaml` into a print-ready Assessment Package.

Orchestrates the Phase 1 round trip::

    assessment.yaml  ->  layout (geometry)  ->  paper.typ / paper.pdf
                                             ->  manifest.json (answer-zone bboxes)
                                             ->  key.yaml (marking-pack scaffold)

The single deterministic layout engine (`layout.py`) computes all page geometry;
both the Typst markup and the manifest bounding boxes are derived from it, so the
printed zones and the manifest coordinates agree *by construction*.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

import yaml

from ..ids import version_hash
from ..models import Assessment, Manifest
from . import keypack, layout, manifest, typst_render


@dataclass
class BuildResult:
    package_dir: Path
    assessment_path: Path
    key_path: Path
    typst_path: Path
    pdf_path: Path | None
    manifest_path: Path
    version_hash: str
    total_pages: int


def build_package(assessment: Assessment, package_dir: Path, compile_pdf: bool = True) -> BuildResult:
    """Generate the full Assessment Package folder for `assessment`."""
    package_dir.mkdir(parents=True, exist_ok=True)
    (package_dir / "scripts").mkdir(exist_ok=True)

    vhash = version_hash(assessment)
    paper = layout.lay_out(assessment, vhash)

    # 1. Canonical assessment (echoed into the package for provenance).
    assessment_path = package_dir / "assessment.yaml"
    assessment_path.write_text(
        yaml.safe_dump(assessment.model_dump(mode="json", exclude_none=True), sort_keys=False, allow_unicode=True),
        encoding="utf-8",
    )

    # 2. Marking-pack scaffold for the teacher to refine.
    key = keypack.scaffold(assessment)
    key_path = package_dir / "key.yaml"
    key_path.write_text(
        yaml.safe_dump(key.model_dump(mode="json", exclude_none=True), sort_keys=False, allow_unicode=True),
        encoding="utf-8",
    )

    # 3. Manifest — the map that makes per-question cropping deterministic.
    man: Manifest = manifest.build_manifest(assessment, paper, vhash)
    manifest_path = package_dir / "manifest.json"
    manifest_path.write_text(json.dumps(man.model_dump(mode="json"), indent=2), encoding="utf-8")

    # 4. Paper: Typst source (+ compiled PDF).
    typst_path = package_dir / "paper.typ"
    pdf_path = typst_render.render(paper, package_dir, compile_pdf=compile_pdf)

    return BuildResult(
        package_dir=package_dir,
        assessment_path=assessment_path,
        key_path=key_path,
        typst_path=typst_path,
        pdf_path=pdf_path,
        manifest_path=manifest_path,
        version_hash=vhash,
        total_pages=len(paper.pages),
    )
