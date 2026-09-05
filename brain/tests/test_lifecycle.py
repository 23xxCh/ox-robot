from __future__ import annotations

import math

from brain.app.lifecycle import Lifecycle, Presence
from brain.app.persona import PersonaState


ABSENT_HOLD_MS = 8000
AUTONOMY_INTERVAL_MS = 12000
SECRET_MARKERS = ("吐槽", "终于清静", "没人理我")


def _say_texts(intents) -> list[str]:
    return [
        str(item.args.get("text") or "")
        for item in intents
        if item.verb == "say" and str(item.args.get("text") or "").strip()
    ]


def test_persona_aliases_keep_old_enum_values() -> None:
    assert PersonaState.FREEZE.value == "FREEZE"
    assert PersonaState.SECRET_ALIVE.value == "SECRET_ALIVE"
    assert PersonaState.MECHANICAL is PersonaState.FREEZE
    assert PersonaState.SECRET is PersonaState.SECRET_ALIVE


def test_t01_mechanical_blocks_secret_speech_and_walk_wake_is_mama() -> None:
    life = Lifecycle()
    assert life.persona.state == PersonaState.FREEZE
    assert life.persona.state == PersonaState.MECHANICAL
    assert not life.persona.allows_secret_speech()
    assert not life.persona.allows_motion()

    hello = life.handle_utterance("你好", now_ms=0)
    assert all(marker not in (hello.text or "") for marker in SECRET_MARKERS)
    assert all(item.verb != "walk" for item in hello.intents)
    assert hello.intents == []

    mama = life.handle_utterance("嘿，牛来", now_ms=10)
    assert mama.text == "妈妈"
    assert all(item.verb != "walk" for item in mama.intents)
    assert all(marker not in mama.text for marker in SECRET_MARKERS)
    assert life.persona.state == PersonaState.FREEZE
    assert not life.persona.allows_secret_speech()


def test_t02_proximity_and_unknown_never_become_absent_or_secret() -> None:
    life = Lifecycle()
    life.ingest_proximity(100, now_ms=0)
    assert life.presence.value != Presence.ABSENT
    assert life.persona.state != PersonaState.SECRET_ALIVE

    life.ingest_proximity(now_ms=5, timeout=True)
    assert life.presence.value != Presence.ABSENT
    assert life.persona.state == PersonaState.FREEZE

    life.ingest_proximity(float("nan"), now_ms=10)
    assert life.presence.value != Presence.ABSENT
    assert not math.isfinite(float("nan"))

    life.ingest_proximity(float("inf"), now_ms=11)
    assert life.presence.value != Presence.ABSENT

    life.set_presence(Presence.UNKNOWN, source="operator_demo", now_ms=20)
    later = life.tick(20 + ABSENT_HOLD_MS)
    assert later == []
    assert life.presence.value == Presence.UNKNOWN
    assert life.presence.source == "operator_demo"
    assert life.persona.state == PersonaState.FREEZE
    assert life.persona.state != PersonaState.SECRET
    assert not life.persona.allows_secret_speech()


def test_t03_absent_hold_enters_secret_and_tick_emits_autonomy_without_hello() -> None:
    life = Lifecycle()
    life.set_presence(Presence.ABSENT, source="operator_demo", now_ms=0)
    assert life.presence.value == Presence.ABSENT
    assert life.persona.state == PersonaState.FREEZE

    assert life.tick(ABSENT_HOLD_MS - 1) == []
    assert life.persona.state == PersonaState.FREEZE
    assert not life.persona.allows_secret_speech()

    life.tick(ABSENT_HOLD_MS)
    assert life.persona.state == PersonaState.SECRET_ALIVE
    assert life.persona.state == PersonaState.SECRET
    assert life.persona.allows_secret_speech()

    spoken: list[str] = []
    for now in (ABSENT_HOLD_MS, ABSENT_HOLD_MS + AUTONOMY_INTERVAL_MS, ABSENT_HOLD_MS + 2 * AUTONOMY_INTERVAL_MS):
        spoken.extend(_say_texts(life.tick(now)))
    assert any(text.strip() for text in spoken)


def test_present_during_secret_immediately_freezes_and_autonomy_is_empty() -> None:
    life = Lifecycle()
    life.set_presence(Presence.ABSENT, source="operator_demo", now_ms=0)
    life.tick(ABSENT_HOLD_MS)
    assert life.persona.state == PersonaState.SECRET_ALIVE

    secret = life.handle_utterance("你好", now_ms=ABSENT_HOLD_MS + 1)
    assert any(marker in secret.text for marker in SECRET_MARKERS)
    assert secret.text != "妈妈"

    life.set_presence(Presence.PRESENT, source="operator_demo", now_ms=ABSENT_HOLD_MS + 50)
    assert life.persona.state == PersonaState.FREEZE
    assert life.persona.state == PersonaState.MECHANICAL
    assert not life.persona.allows_secret_speech()
    assert life.tick(ABSENT_HOLD_MS + AUTONOMY_INTERVAL_MS) == []
    assert life.tick(ABSENT_HOLD_MS + 2 * AUTONOMY_INTERVAL_MS) == []

    hello = life.handle_utterance("你好", now_ms=ABSENT_HOLD_MS + 100)
    assert all(marker not in (hello.text or "") for marker in SECRET_MARKERS)
    assert hello.intents == []
