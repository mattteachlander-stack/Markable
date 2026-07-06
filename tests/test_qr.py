import pytest

from markable.qr import make_payload, parse_payload


def test_payload_round_trip():
    payload = make_payload("2026-T3-Y9-chem", "abc123", 3)
    data = parse_payload(payload)
    assert data == {"test_id": "2026-T3-Y9-chem", "version_hash": "abc123", "page_number": 3}


def test_payload_is_deterministic():
    a = make_payload("t", "h", 1)
    b = make_payload("t", "h", 1)
    assert a == b


def test_parse_rejects_incomplete_payload():
    with pytest.raises(ValueError):
        parse_payload('{"test_id": "t"}')
