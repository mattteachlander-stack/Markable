"""Local pseudonymisation — no identifiable student data leaves this machine.

Before anything is sent to a cloud/AI marker, every student identifier is
replaced with a random alias (``anon-3f9c2b1a``). The alias→student key is
written **only** to ``anon_key.yaml`` inside the package folder (owner-only
file permissions) and is used to re-identify results locally the moment they
come back. What the marker sees:

- the answer-zone crop image (never the student-ID box zone), and
- a random alias in batch ``custom_id``s — nothing derivable from the student.

Aliases are random, not hashes: a hash of a student ID could be reversed by
anyone who can enumerate the school's ID space. ``secrets.token_hex`` cannot.

The key file is a package-local artifact (``packages/`` is gitignored) and is
never copied into ``export/`` or any report. Deleting it permanently breaks the
link between aliases and students — nothing transmitted can then be re-linked.
"""

from __future__ import annotations

import os
import secrets
from pathlib import Path

import yaml

ANON_KEY_FILE = "anon_key.yaml"

_HEADER = (
    "# Markable pseudonymisation key — LOCAL ONLY, never share or upload.\n"
    "# Maps the random aliases sent to the AI marker back to real student IDs.\n"
    "# Deleting this file permanently unlinks transmitted data from students.\n"
)


class Pseudonymiser:
    """Stable alias ↔ student-ID mapping backed by a local key file."""

    def __init__(self, package_dir: Path):
        self.path = Path(package_dir) / ANON_KEY_FILE
        self._to_alias: dict[str, str] = {}
        self._to_real: dict[str, str] = {}
        if self.path.exists():
            data = yaml.safe_load(self.path.read_text(encoding="utf-8")) or {}
            for alias, real in (data.get("aliases") or {}).items():
                self._to_alias[str(real)] = str(alias)
                self._to_real[str(alias)] = str(real)

    def alias(self, student_id: str) -> str:
        """Return the alias for a student, minting (and persisting) one on first use."""
        existing = self._to_alias.get(student_id)
        if existing is not None:
            return existing
        while True:
            candidate = f"anon-{secrets.token_hex(4)}"
            if candidate not in self._to_real:
                break
        self._to_alias[student_id] = candidate
        self._to_real[candidate] = student_id
        self._save()
        return candidate

    def real(self, alias: str) -> str:
        """Re-identify an alias locally. Unknown values pass through unchanged,
        so already-local identifiers (e.g. blank judgements) are never mangled."""
        return self._to_real.get(alias, alias)

    def _save(self) -> None:
        body = yaml.safe_dump({"aliases": dict(sorted(self._to_real.items()))},
                              sort_keys=False, allow_unicode=True)
        self.path.write_text(_HEADER + body, encoding="utf-8")
        os.chmod(self.path, 0o600)  # owner-only: it's the re-identification key
