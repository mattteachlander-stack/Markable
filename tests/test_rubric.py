"""Rubric builder tests — offline (request shape, Key conversion, guards)."""

import json

import pytest
import yaml

from markable.models import Key, QuestionType
from markable.rubric import (
    RUBRIC_PACK,
    RUBRIC_SCHEMA,
    build_rubric_request,
    marks_check,
    run_rubric,
    to_key,
    write_key,
)

PAYLOAD = {
    "test_id": "2026-T3-Y9-chem",
    "total_marks": 3,
    "questions": [
        {
            "id": "Q1", "type": "mcq", "marks": 1, "correct": "C",
            "distractor_notes": [{"option": "A", "note": "confuses charge signs"}],
            "criteria": [], "accept": [], "reject": [],
            "final_answer": None, "tolerance": None, "rubric": [],
        },
        {
            "id": "Q2", "type": "numerical", "marks": 2, "correct": None,
            "distractor_notes": [],
            "criteria": [{"point": "moles formula used", "marks": 1},
                          {"point": "correct final answer", "marks": 1}],
            "accept": ["2 mol"], "reject": ["36 mol"],
            "final_answer": "2 mol", "tolerance": 0.01, "rubric": [],
        },
    ],
    "verify": [{"question_id": "Q1", "note": "correct answer inferred — confirm C"}],
}


def test_request_shape():
    req = build_rubric_request("## Q1 [mcq, 1]\nPick")
    assert req["model"] == "claude-opus-4-8"
    assert req["thinking"] == {"type": "adaptive"}
    assert req["system"][0]["text"] == RUBRIC_PACK
    assert req["system"][0]["cache_control"] == {"type": "ephemeral"}
    assert req["output_config"]["format"] == {"type": "json_schema", "schema": RUBRIC_SCHEMA}


def test_pack_encodes_rubric_rules():
    for rule in ("MARKS", "distractor_notes", "final_answer", "rubric", "verify",
                 "GROUND EVERYTHING IN THE TEST"):
        assert rule in RUBRIC_PACK, rule


def test_to_key_matches_marking_schema(tmp_path):
    key = to_key(PAYLOAD)
    assert isinstance(key, Key)
    q1, q2 = key.questions
    assert q1.type is QuestionType.mcq and q1.correct == "C"
    assert q1.distractor_notes == {"A": "confuses charge signs"}
    assert q2.final_answer == "2 mol" and q2.tolerance == 0.01
    assert sum(c.marks for c in q2.criteria) == q2.marks
    assert q1.review_threshold == 0.85
    # round-trips through yaml into the same authoritative model `mark` loads
    path = write_key(key, tmp_path / "key.yaml")
    reloaded = Key.model_validate(yaml.safe_load(path.read_text(encoding="utf-8")))
    assert reloaded == key


def test_extended_gets_higher_review_threshold():
    p = dict(PAYLOAD)
    p["questions"] = [dict(PAYLOAD["questions"][1], id="Q4", type="extended",
                           rubric=[{"band": "full", "descriptor": "all points"}])]
    key = to_key(p)
    assert key.questions[0].review_threshold == 0.9


def test_marks_check_flags_bad_sums():
    bad = json.loads(json.dumps(PAYLOAD))
    bad["questions"][1]["criteria"][0]["marks"] = 5
    problems = marks_check(bad)
    assert len(problems) == 1 and "Q2" in problems[0]
    assert marks_check(PAYLOAD) == []


class _FakeClient:
    def __init__(self, payload):
        class Block:
            type = "text"
            text = json.dumps(payload)

        class Msg:
            stop_reason = "end_turn"
            content = [Block()]

        class Messages:
            def create(self, **kw):
                self.last = kw
                return Msg()

        self.messages = Messages()


def test_run_rubric_round_trip():
    out = run_rubric("some test", client=_FakeClient(PAYLOAD))
    assert out == PAYLOAD


def test_empty_test_rejected():
    with pytest.raises(ValueError):
        run_rubric("  ", client=_FakeClient(PAYLOAD))
