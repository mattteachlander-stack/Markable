"""Curriculum packs and question tagging (Part 2, Phase 5).

A **curriculum pack** is a structured, versioned representation of an official
curriculum (brief 9.1), stored under `curricula/<pack-id>/pack.yaml` with a
`source_meta.json` provenance record. Packs are immutable once an assessment is
tagged against them — historical reports stay valid when curricula update.

Tagging (`markable tag`, brief 9.2) maps each question to outcome codes. The
proposal engine here is **offline and deterministic**: keyword-overlap scoring
between the question (stem + criteria) and each outcome (description +
elaborations + strand). Claude-assisted proposals are a later refinement; the
teacher's confirmation is what makes downstream reports defensible either way,
so the interactive confirm flow is the contract, not the proposer.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Callable, Optional

import yaml

from .ingest import load_assessment, write_assessment
from .models import Assessment, CurriculumPack, Outcome

DEFAULT_CURRICULA_DIR = Path("curricula")

# ---------------------------------------------------------------------------
# Pack management
# ---------------------------------------------------------------------------


class CurriculumError(ValueError):
    pass


def import_pack(source: Path, pack_id: str, curricula_dir: Path = DEFAULT_CURRICULA_DIR) -> Path:
    """Import a pack.yaml-shaped file as `curricula/<pack_id>/`.

    Only the structured-YAML path is implemented; Claude-assisted ingestion of
    PDF/webpage curricula (brief 9.1) raises a clear not-yet message.
    """
    if source.suffix.lower() not in {".yaml", ".yml"}:
        raise CurriculumError(
            f"'{source.name}': only structured pack.yaml import is implemented. "
            "Claude-assisted ingestion of PDF/webpage curricula lands later in Phase 5."
        )
    data = yaml.safe_load(source.read_text(encoding="utf-8"))
    pack = CurriculumPack.model_validate(data)  # fail loudly on shape problems

    target = curricula_dir / pack_id
    if (target / "pack.yaml").exists():
        raise CurriculumError(
            f"pack '{pack_id}' already exists — packs are immutable once used; "
            "import a revision under a new id."
        )
    target.mkdir(parents=True, exist_ok=True)
    (target / "pack.yaml").write_text(
        yaml.safe_dump(pack.model_dump(mode="json", exclude_none=True), sort_keys=False, allow_unicode=True),
        encoding="utf-8",
    )
    (target / "source_meta.json").write_text(
        json.dumps(
            {
                "source": str(source),
                "curriculum": pack.curriculum,
                "version": pack.version,
                "ingested_by": "markable curriculum import",
                "date_ingested": date.today().isoformat(),
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    return target


def list_packs(curricula_dir: Path = DEFAULT_CURRICULA_DIR) -> list[dict]:
    out = []
    if not curricula_dir.is_dir():
        return out
    for pack_dir in sorted(p for p in curricula_dir.iterdir() if (p / "pack.yaml").exists()):
        pack = load_pack(pack_dir.name, curricula_dir)
        out.append(
            {
                "id": pack_dir.name,
                "curriculum": pack.curriculum,
                "version": pack.version,
                "levels": pack.levels,
                "outcomes": len(pack.outcomes),
            }
        )
    return out


def load_pack(pack_id: str, curricula_dir: Path = DEFAULT_CURRICULA_DIR) -> CurriculumPack:
    path = curricula_dir / pack_id / "pack.yaml"
    if not path.exists():
        # Direct path escape hatch: `--curriculum path/to/pack.yaml`
        direct = Path(pack_id)
        if direct.suffix in {".yaml", ".yml"} and direct.exists():
            path = direct
        else:
            raise CurriculumError(
                f"curriculum pack '{pack_id}' not found under {curricula_dir}/ "
                "(run `markable curriculum import` first)"
            )
    return CurriculumPack.model_validate(yaml.safe_load(path.read_text(encoding="utf-8")))


# ---------------------------------------------------------------------------
# Tag proposals — offline keyword-overlap scorer
# ---------------------------------------------------------------------------

_STOP = {
    "the", "a", "an", "and", "or", "of", "to", "in", "on", "for", "with", "your",
    "is", "are", "how", "what", "which", "that", "this", "its", "it", "be", "by",
    "using", "use", "used", "their", "them", "when", "each", "one", "two", "give",
    "show", "state", "describe", "explain", "identify", "draw", "label", "should",
    "answer", "question", "marks", "mark", "simple",
}


def _terms(text: str) -> set[str]:
    words = re.findall(r"[a-z]{3,}", text.lower())
    out = set()
    for w in words:
        if w in _STOP:
            continue
        # crude stem so "reactions" matches "reaction", "increases"/"increased" match
        out.add(w[:-1] if w.endswith("s") else w)
    return out


@dataclass
class TagProposal:
    code: str
    score: float
    justification: str


def propose_tags(question, pack: CurriculumPack, top_n: int = 3) -> list[TagProposal]:
    q_terms = _terms(question.stem)
    proposals = []
    for outcome in pack.outcomes:
        o_text = " ".join([outcome.description, outcome.strand, *outcome.elaborations])
        o_terms = _terms(o_text)
        shared = q_terms & o_terms
        if not shared:
            continue
        score = len(shared) / max(3, len(o_terms) ** 0.5)
        proposals.append(
            TagProposal(
                code=outcome.code,
                score=round(score, 3),
                justification="shared terms: " + ", ".join(sorted(shared)[:6]),
            )
        )
    proposals.sort(key=lambda p: -p.score)
    return proposals[:top_n]


# (question_id, proposals) -> confirmed outcome codes (possibly edited/empty)
TagResolver = Callable[[str, list[TagProposal]], list[str]]


def run_tag(
    package_dir: Path,
    pack: CurriculumPack,
    resolver: Optional[TagResolver] = None,
    tag_map: Optional[dict[str, list[str]]] = None,
) -> Assessment:
    """Write confirmed outcome codes into the package's assessment.yaml.

    Precedence: an explicit `tag_map` (qid -> codes) wins; otherwise proposals
    go through `resolver` (the interactive confirm). Unknown codes are rejected
    so typos can't silently corrupt downstream reports.
    """
    assessment = load_assessment(package_dir / "assessment.yaml")
    valid = {o.code for o in pack.outcomes}

    for q in assessment.questions:
        if tag_map is not None and q.id in tag_map:
            codes = list(tag_map[q.id])
        elif resolver is not None:
            codes = resolver(q.id, propose_tags(q, pack))
        else:
            continue
        bad = [c for c in codes if c not in valid]
        if bad:
            raise CurriculumError(f"{q.id}: unknown outcome code(s) {bad} for pack '{pack.curriculum}'")
        q.outcome_codes = codes

    write_assessment(assessment, package_dir / "assessment.yaml")
    return assessment


def outcome_index(pack: CurriculumPack) -> dict[str, Outcome]:
    return {o.code: o for o in pack.outcomes}
