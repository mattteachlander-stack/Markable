"""Pseudonymisation tests — the privacy guarantee for cloud/AI marking.

Aliases must be random (not derivable from the student), stable across runs
(persisted key file), local-only (owner-only permissions, never in transmitted
payloads), and reversible only via the local key.
"""

import json
import os
import stat

import yaml

from markable.anon import ANON_KEY_FILE, Pseudonymiser


def test_alias_random_stable_and_reversible(tmp_path):
    p = Pseudonymiser(tmp_path)
    a1 = p.alias("23173583X")
    # random alias, nothing of the real ID leaks into it
    assert a1.startswith("anon-") and "23173583X" not in a1
    # stable within a run and reversible
    assert p.alias("23173583X") == a1
    assert p.real(a1) == "23173583X"
    # distinct students get distinct aliases
    assert p.alias("other") != a1
    # unknown values pass through (blank judgements are created locally)
    assert p.real("S9") == "S9"


def test_key_persisted_locally_and_private(tmp_path):
    a1 = Pseudonymiser(tmp_path).alias("S1")
    key_file = tmp_path / ANON_KEY_FILE
    assert key_file.exists()
    # owner-only: this file IS the re-identification key
    assert stat.S_IMODE(os.stat(key_file).st_mode) == 0o600
    assert "LOCAL ONLY" in key_file.read_text(encoding="utf-8")
    # a fresh instance (new run) reuses the same alias — audit trail holds
    p2 = Pseudonymiser(tmp_path)
    assert p2.alias("S1") == a1
    assert p2.real(a1) == "S1"


def test_two_students_never_collide(tmp_path):
    p = Pseudonymiser(tmp_path)
    aliases = {p.alias(f"S{i}") for i in range(50)}
    assert len(aliases) == 50


def test_batch_custom_ids_carry_no_real_id(tmp_path):
    """The Batches API custom_id is the one place a student ID used to travel:
    with run_mark aliasing items first, the wire payload holds only aliases."""
    from markable.mark import MarkItem
    from markable.mark.anthropic_marker import AnthropicMarker
    from markable.models import KeyEntry, Question, QuestionType

    import io
    from PIL import Image
    buf = io.BytesIO()
    Image.new("L", (8, 8), 255).save(buf, format="PNG")
    crop = tmp_path / "Q1.png"
    crop.write_bytes(buf.getvalue())

    p = Pseudonymiser(tmp_path)
    marker = AnthropicMarker(client=object())  # request-building only
    q = Question(id="Q1", type=QuestionType.mcq, marks=1, stem="Pick", options={"A": "x", "B": "y"})
    entry = KeyEntry(id="Q1", type=QuestionType.mcq, marks=1, correct="A")

    item = MarkItem(student_id=p.alias("23173583X"), crop_path=crop)
    req = marker.build_request(q, entry, item)
    custom_id = f"{q.id}--{item.student_id}"  # what _mark_via_batch sends

    wire = json.dumps({"custom_id": custom_id, "params": req})
    assert "23173583X" not in wire
    assert "anon-" in custom_id
