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
