from __future__ import annotations

from brain.app.brain import NiulaiBrain
from brain.app.mcp_broker import McpBroker
from brain.app.models import ActionIntent
from brain.app.persona import PersonaState


def test_late_perform_after_freeze_is_rejected() -> None:
    brain = NiulaiBrain()
    first = brain.mcp.call_perform(
        {"verb": "walk", "dir": "forward", "ttl_ms": 800}
    )
    assert first.ok is True
    assert len(brain.mcp.device_calls) == 1

    brain.ingest_distance(8)

    late = brain.mcp.call_perform(
        {"verb": "walk", "dir": "forward", "ttl_ms": 800}
    )
    assert late.ok is False
    assert late.error == "frozen"
    assert brain.mcp.queued() == []
    assert len(brain.mcp.device_calls) == 1


def test_walk_after_proximity_freeze_is_not_sent() -> None:
    from fastapi.testclient import TestClient

    from brain.app.main import create_app

    brain = NiulaiBrain()
    brain.ingest_distance(8)
    client = TestClient(create_app(brain))
    with client.websocket_connect("/xiaozhi/v1/") as ws:
        ws.send_json({"type": "hello", "version": 1})
        ws.receive_json()
        ws.send_json({"type": "listen", "state": "start"})
        ws.send_bytes("往前走".encode("utf-8"))
        ws.send_json({"type": "listen", "state": "stop"})
        messages: list[dict] = []
        for _ in range(20):
            msg = ws.receive_json()
            messages.append(msg)
            if msg.get("type") == "tts" and msg.get("state") == "stop":
                break
        assert all(
            not (item.get("type") == "niulai" and item.get("motion"))
            for item in messages
        )


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
