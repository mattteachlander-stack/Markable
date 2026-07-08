"""AI test-upgrader tests — offline (request shape + injectable fake client)."""

import json
import zipfile

import pytest

from markable.improve import (
    IMPROVE_SCHEMA,
    INSTRUCTION_PACK,
    build_improve_request,
    extract_text,
    run_improve,
)


def test_request_shape_matches_api_surface():
    req = build_improve_request("## Q1 [mcq, 1]\nPick one")
    assert req["model"] == "claude-opus-4-8"
    assert req["thinking"] == {"type": "adaptive"}
    # instruction pack rides in a cached system block, shared across calls
    assert req["system"][0]["text"] == INSTRUCTION_PACK
    assert req["system"][0]["cache_control"] == {"type": "ephemeral"}
    assert req["output_config"]["format"] == {"type": "json_schema", "schema": IMPROVE_SCHEMA}
    assert "Pick one" in req["messages"][0]["content"]


def test_pack_encodes_the_readiness_rules():
    for rule in ("UNIQUE STABLE IDS", "MARKS", "ONE CONSTRUCT PER ITEM",
                 "PRESERVE THE ASSESSMENT", "CHANGE LOG"):
        assert rule in INSTRUCTION_PACK, rule
    # output contract matches the schema
    assert set(IMPROVE_SCHEMA["required"]) == {"improved_markdown", "changes", "summary"}


class _FakeMessages:
    def __init__(self, payload):
        self.payload = payload
        self.last_request = None

    def create(self, **kwargs):
        self.last_request = kwargs

        class Block:
            type = "text"
            text = json.dumps(self.payload)

        class Msg:
            stop_reason = "end_turn"
            content = [Block()]

        return Msg()


class _FakeClient:
    def __init__(self, payload):
        self.messages = _FakeMessages(payload)


def test_run_improve_round_trip():
    payload = {
        "improved_markdown": "# T\ntest_id: x\n\n## Q1 [mcq, 1]\n…",
        "changes": [{"question_id": "Q1", "change": "added marks", "reason": "none stated"}],
        "summary": "done",
    }
    client = _FakeClient(payload)
    out = run_improve("some draft", client=client)
    assert out == payload
    assert "some draft" in client.messages.last_request["messages"][0]["content"]


def test_empty_draft_rejected():
    with pytest.raises(ValueError):
        run_improve("   \n", client=_FakeClient({}))


def test_extract_text_docx(tmp_path):
    doc = tmp_path / "t.docx"
    xml = ('<?xml version="1.0"?><w:document xmlns:w="x"><w:body>'
           "<w:p><w:r><w:t>Q1 What is</w:t><w:t> a proton?</w:t></w:r></w:p>"
           "<w:p><w:r><w:t>(2 marks)</w:t></w:r></w:p>"
           "</w:body></w:document>")
    with zipfile.ZipFile(doc, "w") as z:
        z.writestr("word/document.xml", xml)
    text = extract_text(doc)
    assert "Q1 What is a proton?" in text and "(2 marks)" in text


def test_extract_text_rejects_unknown(tmp_path):
    p = tmp_path / "t.pdf"
    p.write_bytes(b"%PDF")
    with pytest.raises(ValueError):
        extract_text(p)
