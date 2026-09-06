from __future__ import annotations

from brain.app.lifecycle import ABSENT_HOLD_MS, Lifecycle, Presence
from brain.app.main import _compose_line
from brain.app.memory import MemoryStore
from brain.app.origin import DEFAULT_ORIGIN, mock_speak
from brain.app.secret_life import (
    LOCAL_SECRET_CLIPS,
    SECRET_LINES,
    SecretDirector,
    pick_absent_line,
)


def _say_texts(intents) -> list[str]:
    return [
        str(item.args.get("text") or "")
        for item in intents
        if item.verb == "say" and str(item.args.get("text") or "").strip()
    ]


def test_director_cools_down_allows_quiet_and_rotates_local_clips() -> None:
    director = SecretDirector(min_cooldown_ms=100)
    first = director.decide(0, wss_ok=True)
    assert first.kind == "speak"
    assert first.text
    assert director.decide(50, wss_ok=True).kind == "wait"

    kinds: list[str] = []
    spoken: list[str] = []
    now = 200
    for _ in range(6):
        beat = director.decide(now, wss_ok=True)
        kinds.append(beat.kind)
        if beat.kind == "speak":
            spoken.append(beat.text)
        now += 200
    assert "quiet" in kinds
    assert "speak" in kinds
    for i, line in enumerate(spoken):
        assert line not in spoken[max(0, i - 5) : i]

    offline = SecretDirector(min_cooldown_ms=100)
    clips: list[str] = []
    kinds_off: list[str] = []
    t = 0
    for _ in range(6):
        beat = offline.decide(t, wss_ok=False)
        kinds_off.append(beat.kind)
        if beat.kind == "local":
            clips.append(beat.clip)
        t += 200
    assert "quiet" in kinds_off
    assert "local" in kinds_off
    assert "speak" not in kinds_off
    assert set(clips) <= set(LOCAL_SECRET_CLIPS)
    assert len(set(clips)) >= min(3, len(clips))
    for i, clip in enumerate(clips):
        if i:
            assert clip != clips[i - 1]


def test_pick_absent_line_skips_last_five() -> None:
    recent = list(SECRET_LINES[:5])
    picked = pick_absent_line(recent)
    assert picked == SECRET_LINES[5]
    assert picked not in recent
    assert "妈妈" not in picked


def test_mock_absent_does_not_repeat_or_say_mama() -> None:
    memory = "被喊「妈妈」3次。最近说过（不要重复）：" + "｜".join(SECRET_LINES[:5])
    line = mock_speak(DEFAULT_ORIGIN, "ABSENT", "", memory=memory)
    assert line
    assert "妈妈" not in line
    assert line not in SECRET_LINES[:5]


def test_compose_absent_lines_do_not_repeat_last_five() -> None:
    from brain.app.brain import NiulaiBrain

    brain = NiulaiBrain()
    lines: list[str] = []
    for _ in range(6):
        line, _intents = _compose_line(brain, "niu-1", "ABSENT", DEFAULT_ORIGIN, "")
        assert "妈妈" not in line
        lines.append(line)
    for i, line in enumerate(lines):
        assert line not in lines[max(0, i - 5) : i]
    store: MemoryStore = brain.memory
    assert len(store.recent_lines("niu-1")) == 5


def test_lifecycle_tick_can_be_quiet_and_does_not_repeat() -> None:
    life = Lifecycle(autonomy_interval_ms=100)
    life.set_presence(Presence.ABSENT, source="operator_demo", now_ms=0)
    spoken: list[str] = []
    empty = 0
    for i in range(8):
        texts = _say_texts(life.tick(ABSENT_HOLD_MS + i * 100))
        if texts:
            spoken.extend(texts)
        else:
            empty += 1
    assert spoken
    assert empty >= 1
    for i, line in enumerate(spoken):
        assert line not in spoken[max(0, i - 5) : i]


def test_present_stops_new_secret_ticks() -> None:
    life = Lifecycle(autonomy_interval_ms=100)
    life.set_presence(Presence.ABSENT, source="operator_demo", now_ms=0)
    first = _say_texts(life.tick(ABSENT_HOLD_MS + 100))
    assert first
    life.set_presence(Presence.PRESENT, source="proximity", now_ms=ABSENT_HOLD_MS + 200)
    assert _say_texts(life.tick(ABSENT_HOLD_MS + 400)) == []
    assert _say_texts(life.tick(ABSENT_HOLD_MS + 800)) == []
