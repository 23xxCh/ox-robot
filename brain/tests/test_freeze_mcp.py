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
