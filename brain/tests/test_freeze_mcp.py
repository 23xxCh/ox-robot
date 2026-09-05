from __future__ import annotations

from brain.app.brain import NiulaiBrain
from brain.app.mcp_broker import McpBroker
from brain.app.models import ActionIntent
from brain.app.persona import PersonaState


def test_close_distance_drops_walk_and_forces_snore() -> None:
    brain = NiulaiBrain()
    brain.persona.set(PersonaState.SECRET_ALIVE)
    brain.mcp.enqueue(ActionIntent(verb="walk", args={"dir": "forward"}, ttl_ms=800))

    outbound = brain.ingest_distance(8)

    assert brain.persona.state == PersonaState.FREEZE
    assert all(item.verb != "walk" for item in outbound)
    assert any(item.verb == "snore" for item in outbound)
    assert brain.mcp.queued() == []


def test_unknown_or_ttl_less_perform_is_not_sent_to_device() -> None:
    broker = McpBroker()
    unknown = broker.call_perform({"verb": "fly", "ttl_ms": 500})
    missing_ttl = broker.call_perform({"verb": "walk", "dir": "forward"})
    assert unknown.ok is False
    assert missing_ttl.ok is False
    assert broker.device_calls == []


def test_valid_walk_with_ttl_is_sent_to_device() -> None:
    broker = McpBroker()
    result = broker.call_perform({"verb": "walk", "ttl_ms": 800})
    assert result.ok is True
    assert result.intent is not None
    assert result.intent.verb == "walk"
    assert result.intent.ttl_ms == 800
    assert broker.device_calls == [
        {"name": "niu.perform", "arguments": {"verb": "walk", "ttl_ms": 800}}
    ]
    directed = broker.call_perform({"verb": "walk", "dir": "forward", "ttl_ms": 2000})
    assert directed.ok is True
    assert directed.intent is not None
    assert directed.intent.args.get("dir") == "forward"
    assert directed.intent.ttl_ms == 2000


def test_pulse_us_perform_is_not_sent_to_device() -> None:
    broker = McpBroker()
    result = broker.call_perform(
        {"verb": "walk", "dir": "forward", "ttl_ms": 800, "pulse_us": 2500}
    )
    assert result.ok is False
    assert result.error == "unknown-field"
    assert broker.device_calls == []
    assert broker.queued() == []


def test_huge_ttl_perform_is_not_sent_to_device() -> None:
    broker = McpBroker()
    huge = broker.call_perform({"verb": "walk", "dir": "forward", "ttl_ms": 999999999})
    over_max = broker.call_perform({"verb": "walk", "ttl_ms": 2001})
    negative = broker.call_perform({"verb": "walk", "ttl_ms": -1})
    assert huge.ok is False
    assert over_max.ok is False
    assert negative.ok is False
    assert broker.device_calls == []
    assert broker.queued() == []


def test_invalid_dir_perform_is_not_sent_to_device() -> None:
    broker = McpBroker()
    invalid = broker.call_perform({"verb": "walk", "dir": "invalid", "ttl_ms": 0})
    turn = broker.call_perform({"verb": "turn", "dir": "up", "ttl_ms": 400})
    assert invalid.ok is False
    assert invalid.error == "bad-dir"
    assert turn.ok is False
    assert broker.device_calls == []
    assert broker.queued() == []


def test_boolean_or_nan_ttl_perform_is_not_sent_to_device() -> None:
    broker = McpBroker()
    as_true = broker.call_perform({"verb": "walk", "ttl_ms": True})
    as_false = broker.call_perform({"verb": "stop", "ttl_ms": False})
    as_nan = broker.call_perform({"verb": "walk", "ttl_ms": float("nan")})
    as_float = broker.call_perform({"verb": "walk", "ttl_ms": 800.0})
    assert as_true.ok is False
    assert as_false.ok is False
    assert as_nan.ok is False
    assert as_float.ok is False
    assert broker.device_calls == []
    assert broker.queued() == []
