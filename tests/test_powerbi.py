"""Power BI cleaner tests — tidy star schema from a synthetic gradebook."""

import csv
from pathlib import Path

import pytest

openpyxl = pytest.importorskip("openpyxl")

from conftest import make_sac_sheet

from markable.gradebook import read_gradebook
from markable.powerbi import _assessment_id, clean, write_dataset


@pytest.fixture
def workbook(tmp_path):
    wb = openpyxl.Workbook()
    wb.remove(wb.active)
    make_sac_sheet(wb, "SAC A", 1, "Cells", 6,
                   [("1", 2), ("2", 4)],
                   [("1", "SMITH", "Ann", [2, 4]), ("2", "JONES", "Bob", [1, 2]),
                    ("3", "LEE", "Cara", [0, 0])])
    make_sac_sheet(wb, "SAC B", 2, "Immunity", 5,
                   [("1a", 2), ("1b", 3)],
                   [("1", "SMITH", "Ann", [2, 3]), ("2", "JONES", "Bob", [1, 1]),
                    ("3", "LEE", "Cara", [2, 2])])
    p = tmp_path / "gb.xlsx"
    wb.save(p)
    return p


def _rows(path):
    with path.open() as f:
        return list(csv.DictReader(f))


def test_star_schema_shapes(workbook, tmp_path):
    gb = read_gradebook(workbook)
    res = clean(gb)
    # grain: 3 students × (2 + 2) questions = 12 fact rows
    assert len(res.fact_marks) == 12
    assert len(res.fact_student_sac) == 6      # 3 students × 2 SACs
    assert len(res.dim_student) == 3           # names de-duplicated across SACs
    assert len(res.dim_question) == 4
    assert len(res.dim_assessment) == 2


def test_totals_grades_and_ids(workbook, tmp_path):
    gb = read_gradebook(workbook)
    res = clean(gb)
    out = tmp_path / "pbi"
    write_dataset(res, out)

    fss = {(r["assessment_id"], r["student_id"]): r for r in _rows(out / "fact_student_sac.csv")}
    aid = _assessment_id(gb.sacs[0])  # "Cells"
    ann = fss[(aid, "smithann")]
    assert float(ann["raw_score"]) == 6 and float(ann["pct"]) == 100.0 and ann["grade"] == "A+"
    cara = fss[(aid, "leecara")]
    assert float(cara["pct"]) == 0.0 and cara["grade"] == "E"

    # star-schema join keys line up
    facts = _rows(out / "fact_marks.csv")
    q_uids = {r["question_uid"] for r in _rows(out / "dim_question.csv")}
    assert {r["question_uid"] for r in facts} <= q_uids
    student_ids = {r["student_id"] for r in _rows(out / "dim_student.csv")}
    assert {r["student_id"] for r in facts} <= student_ids


def test_study_design_area_join_and_guide(workbook, tmp_path):
    gb = read_gradebook(workbook)
    aid = _assessment_id(gb.sacs[0])
    area_of = {(aid, "1"): "Key knowledge — Cells", (aid, "2"): "Key knowledge — Cells"}
    res = clean(gb, area_of=area_of)
    out = tmp_path / "pbi"
    info = write_dataset(res, out)

    assert info["has_skills"] and (out / "dim_skill.csv").exists()
    areas = {r["study_design_area"] for r in _rows(out / "dim_skill.csv")}
    assert "Key knowledge — Cells" in areas
    guide = (out / "POWER_BI_GUIDE.md").read_text()
    assert "star schema" in guide and "DAX" in guide and "dim_skill" in guide
    assert "Facility %" in guide and "Relationships" in guide


def test_quality_flags_missing_and_over_max(tmp_path):
    wb = openpyxl.Workbook(); wb.remove(wb.active)
    ws = make_sac_sheet(wb, "SAC A", 1, "Cells", 4, [("1", 2), ("2", 2)],
                        [("1", "SMITH", "Ann", [2, 2])])
    # blank out a mark and push one over max
    ws.cell(20, 8).value = None   # Ann Q1 missing (assign, don't pass None to cell())
    ws.cell(20, 9, 5)             # Ann Q2 = 5 > max 2
    p = tmp_path / "gb.xlsx"; wb.save(p)
    res = clean(read_gradebook(p))
    issues = {q.issue for q in res.quality}
    assert "missing_mark" in issues and "mark_over_max" in issues
