"""Gradebook + study-design mapping tests.

A synthetic workbook mirroring the real SAC-sheet layout is built in-memory, so
the suite stays self-contained (no bundled xlsx).
"""

from pathlib import Path

import pytest

openpyxl = pytest.importorskip("openpyxl")

from markable.curriculum import load_pack
from markable.gradebook import read_gradebook
from markable.gradebook_html import render_gradebook
from markable.studydesign import compute_skills, map_sac

VCE_PACK = Path(__file__).resolve().parents[1] / "fixtures" / "curricula" / "vce-biology-u34" / "pack.yaml"


def _sac_sheet(wb, title, sac_num, topic, total, questions, students):
    """questions: [(label, max)]; students: [(id, surname, first, [marks...])]."""
    ws = wb.create_sheet(title)
    ws.cell(2, 4, sac_num)   # SAC #:
    ws.cell(2, 2, "SAC #:")
    ws.cell(3, 4, topic)
    ws.cell(3, 2, "TOPIC:")
    ws.cell(4, 4, total)
    ws.cell(4, 2, "TOTAL MARKS:")
    h = 19
    # header row + labels one above
    ws.cell(h, 2, "ID"); ws.cell(h, 3, "VCAA Number"); ws.cell(h, 4, "Surname"); ws.cell(h, 5, "First Name")
    for i, (label, mx) in enumerate(questions):
        c = 8 + i
        ws.cell(h - 1, c, label)
        ws.cell(h, c, f"/{mx:g}")
    ws.cell(h - 1, 8 + len(questions), "TOTAL")
    ws.cell(h, 8 + len(questions), f"/{total:g}")
    for r, (sid, surname, first, marks) in enumerate(students, start=h + 1):
        ws.cell(r, 2, sid); ws.cell(r, 4, surname); ws.cell(r, 5, first)
        for i, m in enumerate(marks):
            ws.cell(r, 8 + i, m)
    return ws


@pytest.fixture
def workbook(tmp_path):
    wb = openpyxl.Workbook()
    wb.remove(wb.active)
    _sac_sheet(wb, "Unit 3 AoS 1 SAC", 1, "Unit 3 AoS 1", 8,
               [("1", 2), ("2", 3), ("3a", 2), ("3b", 1)],
               [("1", "SMITH", "Ann", [2, 3, 2, 1]),
                ("2", "JONES", "Bob", [1, 1, 0, 0]),
                ("3", "LEE", "Cara", [2, 2, 1, 1]),
                ("4", "NG", "Dan", [0, 0, 0, 0])])
    _sac_sheet(wb, "Prac SAC", 5, "Prac Investigation", 6,
               [("Research Q", 2), ("Results Table", 2), ("Discussion - Evaluates Hypothesis", 2)],
               [("1", "SMITH", "Ann", [2, 2, 2]),
                ("2", "JONES", "Bob", [1, 1, 0]),
                ("3", "LEE", "Cara", [2, 1, 1]),
                ("4", "NG", "Dan", [0, 1, 0])])
    path = tmp_path / "gb.xlsx"
    wb.save(path)
    return path


def test_parses_sacs_and_marks(workbook):
    gb = read_gradebook(workbook)
    assert [s.number for s in gb.sacs] == ["1", "5"]
    sac1 = gb.sacs[0]
    assert sac1.topic == "Unit 3 AoS 1" and sac1.total_marks == 8
    assert [q.id for q in sac1.questions] == ["1", "2", "3a", "3b"]  # TOTAL excluded
    assert sac1.questions[1].max_marks == 3
    assert len(sac1.students) == 4
    ann = next(s for s in sac1.students if s.surname == "SMITH")
    assert ann.name == "SMITH, Ann"
    assert sac1.total_for(ann) == 8  # 2+3+2+1


def test_prac_criteria_auto_map_to_key_science_skills(workbook):
    gb = read_gradebook(workbook)
    pack = load_pack(str(VCE_PACK))
    prac = next(s for s in gb.sacs if s.number == "5")
    maps = {m.question_id: m for m in map_sac(prac, pack)}
    # criterion names map to key-science-skills outcomes by keyword, no map file
    assert maps["Research Q"].codes and maps["Research Q"].source == "auto"
    assert maps["Results Table"].codes[0].startswith("VCE-BIO-KSS")
    assert "VCE-BIO-KSS-04" in maps["Discussion - Evaluates Hypothesis"].codes  # analyse & evaluate


def test_teacher_map_beats_auto_and_rolls_up(workbook):
    gb = read_gradebook(workbook)
    pack = load_pack(str(VCE_PACK))
    sac1 = gb.sacs[0]
    tmap = {"1": {"1": ["VCE-BIO-U3A1-01"], "2": ["VCE-BIO-U3A1-02"],
                  "3a": ["VCE-BIO-U3A1-01"], "3b": ["VCE-BIO-U3A1-01"]}}
    sk = compute_skills(sac1, pack, tmap)
    # all four questions share the "Cellular processes" strand
    area = "U3 AoS1 · Cellular processes"
    assert area in sk.cohort_area
    # Ann got full marks (8/8) → 100% in that area
    assert sk.per_student_area[("SMITH, Ann", area)] == [8.0, 8.0]
    # Dan got 0/8 → 0%
    assert sk.per_student_area[("NG, Dan", area)] == [0.0, 8.0]
    assert sk.unmapped == []


def test_render_gradebook_is_self_contained(workbook):
    gb = read_gradebook(workbook)
    pack = load_pack(str(VCE_PACK))
    skills = [compute_skills(s, pack) for s in gb.sacs]
    html = render_gradebook(gb, skills, "VCE Biology")
    assert html.startswith("<!DOCTYPE html>")
    assert "<script src" not in html and "https://" not in html.split("</title>")[1]
    for needle in ("Overview", "SAC 1", "SAC 5", "Skills &amp; content",
                   "Question performance by cohort quartile", "SMITH, Ann"):
        assert needle in html, needle


def test_no_sac_sheets_errors(tmp_path):
    wb = openpyxl.Workbook()
    wb.active["A1"] = "nothing here"
    p = tmp_path / "empty.xlsx"
    wb.save(p)
    with pytest.raises(ValueError, match="no SAC sheets"):
        read_gradebook(p)
