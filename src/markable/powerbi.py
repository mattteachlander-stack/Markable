"""`markable powerbi` — clean a teacher gradebook into a Power BI-ready dataset.

The teacher workbook is *wide and messy*: metadata rows, merged headers, blank
spacers, per-SAC sheets, mixed text/number cells. Power BI wants **tidy, long,
star-schema** tables. This tool does the cleaning and emits exactly that, plus a
build guide (Power Query M + DAX measures + visual-by-visual steps), so a
dashboard can be assembled with a few clicks — no manual data wrangling.

Output (into the target folder):

    fact_marks.csv        one row per student × question × assessment (the grain)
    fact_student_sac.csv  one row per student × assessment (totals, %, band)
    dim_student.csv       student id + name (local only — see privacy note)
    dim_question.csv      assessment_id, question_id, max_marks, (study-design area)
    dim_assessment.csv    assessment_id, sac_number, topic, total_marks, questions
    dim_skill.csv         study-design areas (only with --study-design)
    data_quality.csv      what was cleaned / flagged, per sheet
    POWER_BI_GUIDE.md     load order, relationships, DAX measures, visuals

Everything is UTF-8 CSV with a header row — Power BI's *Get Data → Text/CSV*
reads it directly, and the star schema means relationships and measures "just
work".
"""

from __future__ import annotations

import csv
import re
from dataclasses import dataclass, field
from pathlib import Path

from .gradebook import Gradebook, SAC, read_gradebook

_GRADE_BANDS = [  # VCE-ish A+..E on percentage; purely for a demo grade column
    ("A+", 90), ("A", 80), ("B+", 75), ("B", 70), ("C+", 65),
    ("C", 60), ("D+", 55), ("D", 50), ("E", 0),
]


def _grade(pct: float) -> str:
    for g, lo in _GRADE_BANDS:
        if pct >= lo:
            return g
    return "UG"


def _assessment_id(sac: SAC) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", sac.topic.lower()).strip("-")
    return f"SAC{sac.number}-{slug}"[:48]


@dataclass
class QualityRow:
    assessment: str
    issue: str
    detail: str


@dataclass
class CleanResult:
    fact_marks: list[dict]
    fact_student_sac: list[dict]
    dim_student: list[dict]
    dim_question: list[dict]
    dim_assessment: list[dict]
    dim_skill: list[dict]
    quality: list[QualityRow] = field(default_factory=list)


def _student_key(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", name.lower())


def clean(gb: Gradebook, area_of: dict | None = None) -> CleanResult:
    """Flatten a parsed gradebook into tidy star-schema tables.

    `area_of` optionally maps (assessment_id, question_id) -> study-design area.
    """
    area_of = area_of or {}
    res = CleanResult([], [], [], [], [], [])
    seen_students: dict[str, str] = {}
    seen_areas: set[str] = set()

    for sac in gb.sacs:
        aid = _assessment_id(sac)
        res.dim_assessment.append({
            "assessment_id": aid,
            "sac_number": sac.number,
            "topic": sac.topic,
            "total_marks": sac.total_marks,
            "question_count": len(sac.questions),
            "students": len(sac.students),
        })
        for q in sac.questions:
            area = area_of.get((aid, q.id), "")
            if area:
                seen_areas.add(area)
            res.dim_question.append({
                "assessment_id": aid,
                "question_id": q.id,
                "question_uid": f"{aid}::{q.id}",
                "max_marks": q.max_marks,
                "study_design_area": area,
            })

        # duplicate-name guard → stable, unique student ids
        for st in sac.students:
            base = _student_key(st.name)
            sid = seen_students.get(st.name)
            if sid is None:
                sid = base or f"s{len(seen_students)+1}"
                if sid in seen_students.values():
                    sid = f"{sid}-{len(seen_students)+1}"
                seen_students[st.name] = sid
                res.dim_student.append({"student_id": sid, "student_name": st.name})

            total = 0.0
            for q in sac.questions:
                if q.id not in st.marks:
                    res.quality.append(QualityRow(aid, "missing_mark",
                                                  f"{st.name} has no mark for {q.id} (treated as blank)"))
                    continue
                aw = st.marks[q.id]
                total += aw
                if aw > q.max_marks:
                    res.quality.append(QualityRow(aid, "mark_over_max",
                                                  f"{st.name} {q.id}: {aw:g} > max {q.max_marks:g}"))
                res.fact_marks.append({
                    "assessment_id": aid,
                    "student_id": sid,
                    "question_uid": f"{aid}::{q.id}",
                    "question_id": q.id,
                    "marks_awarded": aw,
                    "marks_available": q.max_marks,
                    "pct": round(100 * aw / q.max_marks, 1) if q.max_marks else "",
                    "study_design_area": area_of.get((aid, q.id), ""),
                })
            pct = 100 * total / sac.total_marks if sac.total_marks else 0
            res.fact_student_sac.append({
                "assessment_id": aid,
                "student_id": sid,
                "raw_score": total,
                "max_score": sac.total_marks,
                "pct": round(pct, 1),
                "grade": _grade(pct),
            })

    res.dim_skill = [{"study_design_area": a} for a in sorted(seen_areas)]
    return res


def _write(path: Path, rows: list[dict], header: list[str] | None = None) -> None:
    if not rows and header is None:
        return
    cols = header or list(rows[0].keys())
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        w.writerows(rows)


def write_dataset(res: CleanResult, out_dir: Path) -> dict:
    out_dir.mkdir(parents=True, exist_ok=True)
    _write(out_dir / "fact_marks.csv", res.fact_marks)
    _write(out_dir / "fact_student_sac.csv", res.fact_student_sac)
    _write(out_dir / "dim_student.csv", res.dim_student)
    _write(out_dir / "dim_question.csv", res.dim_question)
    _write(out_dir / "dim_assessment.csv", res.dim_assessment)
    if res.dim_skill:
        _write(out_dir / "dim_skill.csv", res.dim_skill)
    _write(
        out_dir / "data_quality.csv",
        [{"assessment": q.assessment, "issue": q.issue, "detail": q.detail} for q in res.quality],
        header=["assessment", "issue", "detail"],
    )
    (out_dir / "POWER_BI_GUIDE.md").write_text(_guide(res), encoding="utf-8")
    (out_dir / "POWER_QUERY_LOAD.m").write_text(_power_query(res), encoding="utf-8")
    return {
        "fact_rows": len(res.fact_marks),
        "students": len(res.dim_student),
        "assessments": len(res.dim_assessment),
        "quality_flags": len(res.quality),
        "has_skills": bool(res.dim_skill),
    }


def run_powerbi(workbook: Path, out_dir: Path, area_of: dict | None = None) -> dict:
    gb = read_gradebook(workbook)
    res = clean(gb, area_of=area_of)
    return write_dataset(res, out_dir)


# Column → Power Query type. Names not listed default to `type text`.
_M_TYPES = {
    "marks_awarded": "type number", "marks_available": "type number",
    "pct": "type number", "raw_score": "type number", "max_score": "type number",
    "max_marks": "type number", "total_marks": "type number",
    "question_count": "Int64.Type", "students": "Int64.Type",
}


def _power_query(res: CleanResult) -> str:
    """Emit a paste-ready Power Query M loader, one typed query per table, with
    column types derived from the actual data — so the load is one paste each."""
    tables = [
        ("fact_marks", res.fact_marks),
        ("fact_student_sac", res.fact_student_sac),
        ("dim_student", res.dim_student),
        ("dim_question", res.dim_question),
        ("dim_assessment", res.dim_assessment),
    ]
    if res.dim_skill:
        tables.append(("dim_skill", res.dim_skill))
    tables.append(("data_quality", [{"assessment": "", "issue": "", "detail": ""}]))

    blocks = []
    for name, rows in tables:
        cols = list(rows[0].keys()) if rows else []
        typemap = ",\n        ".join(
            f'{{"{c}", {_M_TYPES.get(c, "type text")}}}' for c in cols
        )
        blocks.append(f"""// ---------- {name} ----------
let
    FolderPath = "C:\\Markable\\powerbi",
    Source = Csv.Document(File.Contents(FolderPath & "\\{name}.csv"), [Delimiter=",", Encoding=65001, QuoteStyle=QuoteStyle.Csv]),
    Promoted = Table.PromoteHeaders(Source, [PromoteAllScalars=true]),
    Typed = Table.TransformColumnTypes(Promoted, {{
        {typemap}
    }})
in
    Typed""")

    header = """// Markable -> Power BI - one-paste loader
// =======================================================================
// Loads every clean CSV with correct column types, so you skip importing
// files by hand.
//
// 1. Unzip the Markable dataset to a folder, e.g. C:\\Markable\\powerbi
//    (Mac: /Users/you/Markable/powerbi). All .csv files go in that folder.
// 2. Power BI Desktop -> Home -> Transform data (opens Power Query Editor).
// 3. For EACH block below: Home -> New Source -> Blank Query, then
//    View -> Advanced Editor, paste the block (from "let" to "in Typed"),
//    and set FolderPath to your folder. Name the query the same as the table.
// 4. Home -> Close & Apply.
// 5. Model view -> draw relationships + add DAX measures from POWER_BI_GUIDE.md.
//
// Tip: make a parameter (Home -> Manage Parameters) named FolderPath and
// replace the literal path in each query with it, so you set the folder once.
// =======================================================================

"""
    return header + "\n\n".join(blocks) + "\n"


def _guide(res: CleanResult) -> str:
    skill = res.dim_skill
    skill_load = "\n6. `dim_skill.csv`" if skill else ""
    skill_rel = ("\n- `dim_skill[study_design_area]` → `dim_question[study_design_area]` "
                 "(and `fact_marks[study_design_area]`) — one-to-many" if skill else "")
    skill_visual = ("""
### 5. Skills / study-design page (only if you exported with a study design)
- **Matrix**: Rows `dim_student[student_name]`, Columns `dim_skill[study_design_area]`,
  Values `Attainment %`. Conditional-format the values green→red. This is the
  "what is each student performing to" view.
""" if skill else "")
    return f"""# Power BI — build guide (Markable clean export)

This folder is an **analysis-ready star schema**. Everything is tidy CSV, so
Power BI reads it with no cleaning. Follow the steps below; the whole build is a
few clicks plus pasting the measures.

> **Privacy:** `dim_student.csv` contains student names for *your* local report.
> If you publish to a shared workspace, remove the name column (or apply
> row-level security) so shared views are ID-only.

## 1. Load the data
In Power BI Desktop: **Home → Get data → Text/CSV**, and load each file (or
**Get data → Folder** and select this folder to load them all at once):

1. `fact_marks.csv`  — the grain: one row per student × question × assessment
2. `fact_student_sac.csv` — one row per student × assessment (totals)
3. `dim_student.csv`
4. `dim_question.csv`
5. `dim_assessment.csv`{skill_load}
7. `data_quality.csv` (optional — a page to review what was flagged)

Power BI usually detects types correctly. If `pct`/`marks_*` load as text,
select the column → **Transform → Data type → Decimal number**.

> **One-paste option:** `POWER_QUERY_LOAD.m` in this folder has a typed loader
> query per table. In **Transform data → New Source → Blank Query → Advanced
> Editor**, paste each block and set `FolderPath` to this folder — column types
> are already set, so you skip the manual typing step above.

## 2. Relationships (Model view)
Create these (drag field to field). All are **one-to-many**, single direction
from the dim to the fact:

- `dim_student[student_id]` → `fact_marks[student_id]`
- `dim_student[student_id]` → `fact_student_sac[student_id]`
- `dim_assessment[assessment_id]` → `fact_marks[assessment_id]`
- `dim_assessment[assessment_id]` → `fact_student_sac[assessment_id]`
- `dim_question[question_uid]` → `fact_marks[question_uid]`{skill_rel}

## 3. Measures (New measure — paste each)
```DAX
Total Awarded   = SUM ( fact_marks[marks_awarded] )
Total Available = SUM ( fact_marks[marks_available] )
Facility %      = DIVIDE ( [Total Awarded], [Total Available] )
Class Average % = AVERAGE ( fact_student_sac[pct] )
Median %        = MEDIAN ( fact_student_sac[pct] )
Students        = DISTINCTCOUNT ( fact_student_sac[student_id] )
% At or Above 70 =
    DIVIDE (
        CALCULATE ( DISTINCTCOUNT ( fact_student_sac[student_id] ), fact_student_sac[pct] >= 70 ),
        [Students]
    )
% Below 50 =
    DIVIDE (
        CALCULATE ( DISTINCTCOUNT ( fact_student_sac[student_id] ), fact_student_sac[pct] < 50 ),
        [Students]
    )
Difficulty =
    SWITCH ( TRUE (),
        [Facility %] >= 0.8, "Easy",
        [Facility %] >= 0.5, "Moderate",
        "Difficult" )
```

## 4. Build the pages
Add a **Slicer** with `dim_assessment[topic]` at the top of each page so every
visual filters to the selected SAC.

### Overview
- **Cards**: `Class Average %`, `Median %`, `Students`, `% At or Above 70`, `% Below 50`.
- **Column chart** (score distribution): create a binned column on
  `fact_student_sac[pct]` (right-click the field → *New group* → bin size 10),
  axis = the bins, value = `Students`.
- **Clustered bar** (SAC comparison): axis `dim_assessment[topic]`, value `Class Average %`.

### Question analysis
- **Matrix**: Rows `dim_question[question_id]`, Values `Facility %` and `Difficulty`.
  Conditional-format `Facility %` on a green→red colour scale.
- Add a second matrix with Columns = a quartile field if you want the
  top/middle/bottom split (create it from `fact_student_sac[pct]` with a
  calculated column and RANKX).

### Student snapshot
- **Table**: `dim_student[student_name]`, `fact_student_sac[pct]`,
  `fact_student_sac[grade]`, filtered by the assessment slicer.
{skill_visual}
## Refresh
When you re-run `markable powerbi` on an updated workbook, the CSVs are
overwritten in place — in Power BI just **Home → Refresh** to pull the new
numbers. No re-modelling needed.

---
Generated by Markable · {len(res.fact_marks)} fact rows · {len(res.dim_student)} students ·
{len(res.dim_assessment)} assessments{" · study-design areas included" if skill else ""}.
"""
