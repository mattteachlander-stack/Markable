from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
FIXTURES = REPO_ROOT / "fixtures"


@pytest.fixture
def draft_path() -> Path:
    return FIXTURES / "drafts" / "y9-chem-test.md"


@pytest.fixture
def draft_text(draft_path: Path) -> str:
    return draft_path.read_text(encoding="utf-8")


def make_sac_sheet(wb, title, sac_num, topic, total, questions, students):
    """Build a synthetic SAC sheet matching the teacher-gradebook layout.

    questions: [(label, max)]; students: [(id, surname, first, [marks...])].
    Shared by the gradebook and powerbi tests.
    """
    ws = wb.create_sheet(title)
    ws.cell(2, 2, "SAC #:"); ws.cell(2, 4, sac_num)
    ws.cell(3, 2, "TOPIC:"); ws.cell(3, 4, topic)
    ws.cell(4, 2, "TOTAL MARKS:"); ws.cell(4, 4, total)
    h = 19
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
