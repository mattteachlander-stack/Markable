"""Map SAC questions to a VCE study design, then roll up per-student attainment.

Part 2 of the gradebook feature: "when provided the VCE SAC, map it against the
VCE study design per question, and show what skills / content each student is
performing to."

Mapping sources, in precedence order:
1. An explicit teacher map (`{sac_number: {question_id: [codes]}}`) — the
   defensible path, mirroring `markable tag`.
2. **Auto-derivation from criterion names.** A prac-investigation SAC already
   names each column by the skill it assesses ("Discussion – Evaluates
   Hypothesis", "Scientific Communication"), so those map to key-science-skills
   outcomes by keyword overlap — no stems needed.

A question with no confident match is reported as unmapped, never guessed.
"""

from __future__ import annotations

import re
from collections import defaultdict
from dataclasses import dataclass, field

from .curriculum import _terms
from .gradebook import SAC, GradeStudent
from .models import CurriculumPack, Outcome


@dataclass
class QuestionMap:
    question_id: str
    max_marks: float
    codes: list[str]
    source: str  # "teacher" | "auto" | "unmapped"
    areas: list[str] = field(default_factory=list)  # study-design areas the codes belong to


@dataclass
class SkillsAttainment:
    sac_number: str
    sac_topic: str
    question_maps: list[QuestionMap]
    # (student_name, area) -> [awarded, available]
    per_student_area: dict[tuple[str, str], list[float]]
    cohort_area: dict[str, list[float]]  # area (strand) -> [awarded, available]
    area_outcomes: dict[str, list[str]]  # area -> outcome codes contributing
    students: list[str]
    unmapped: list[str]


def _auto_match(label: str, pack: CurriculumPack, min_overlap: int = 1) -> list[str]:
    """Match a criterion label to study-design outcomes by keyword overlap."""
    q_terms = _terms(label)
    scored = []
    for o in pack.outcomes:
        o_terms = _terms(" ".join([o.topic or "", o.strand, *o.elaborations]))
        shared = q_terms & o_terms
        if len(shared) >= min_overlap:
            scored.append((len(shared), o.code))
    scored.sort(reverse=True)
    return [scored[0][1]] if scored else []


def map_sac(
    sac: SAC,
    pack: CurriculumPack,
    teacher_map: dict | None = None,
) -> list[QuestionMap]:
    outcomes = {o.code: o for o in pack.outcomes}
    explicit = (teacher_map or {}).get(sac.number) or (teacher_map or {}).get(str(sac.number)) or {}
    maps = []
    for q in sac.questions:
        if q.id in explicit:
            codes = [c for c in explicit[q.id] if c in outcomes]
            source = "teacher"
        else:
            codes = _auto_match(q.id, pack)
            source = "auto" if codes else "unmapped"
        maps.append(QuestionMap(question_id=q.id, max_marks=q.max_marks, codes=codes, source=source))
    return maps


def compute_skills(sac: SAC, pack: CurriculumPack, teacher_map: dict | None = None) -> SkillsAttainment:
    outcomes = {o.code: o for o in pack.outcomes}
    dim_names = {d.id: (d.name or d.id) for d in pack.dimensions}
    maps = map_sac(sac, pack, teacher_map)
    by_q = {m.question_id: m for m in maps}

    def area_of(code: str) -> str:
        return outcomes[code].strand

    # Attach the resolved area(s) to each question map for downstream views.
    for m in maps:
        m.areas = sorted({area_of(c) for c in m.codes})

    per_student: dict[tuple[str, str], list[float]] = defaultdict(lambda: [0.0, 0.0])
    cohort: dict[str, list[float]] = defaultdict(lambda: [0.0, 0.0])
    area_outcomes: dict[str, set[str]] = defaultdict(set)

    for st in sac.students:
        for q in sac.questions:
            m = by_q[q.id]
            if not m.codes:
                continue
            awarded = st.marks.get(q.id, 0.0)
            # A question's marks are evidence toward each area it touches.
            areas = {area_of(c) for c in m.codes}
            for area in areas:
                per_student[(st.name, area)][0] += awarded
                per_student[(st.name, area)][1] += q.max_marks
                cohort[area][0] += awarded
                cohort[area][1] += q.max_marks
                area_outcomes[area].update(m.codes)

    return SkillsAttainment(
        sac_number=sac.number,
        sac_topic=sac.topic,
        question_maps=maps,
        per_student_area=dict(per_student),
        cohort_area=dict(cohort),
        area_outcomes={a: sorted(cs) for a, cs in area_outcomes.items()},
        students=[st.name for st in sac.students],
        unmapped=[m.question_id for m in maps if m.source == "unmapped"],
    )
