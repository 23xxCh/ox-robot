from __future__ import annotations

from pathlib import Path

import pytest

from brain.app.memory import MemoryStore


def _store(tmp_path: Path) -> MemoryStore:
    return MemoryStore(tmp_path / "niulai.db")


def _event(event_id: str, kind: str, seq: int, generation: int = 1, **extra):
    payload = {"event_id": event_id, "device_id": "niu-1", "boot_id": "boot-a",
               "event_seq": seq, "memory_generation": generation, "kind": kind,
               "epoch": 1, "device_mono_ms": seq * 10, "payload": extra.get("payload", {})}
    payload.update({k: v for k, v in extra.items() if k != "payload"})
    return payload


def test_duplicate_event_id_does_not_double_mama_count(tmp_path: Path) -> None:
    store = _store(tmp_path)
    assert store.commit_event(_event("e1", "mama_play_completed", 1))
    assert store.commit_event(_event("e1", "mama_play_completed", 1)) is False
    assert store.character("niu-1").mama_count == 1


def test_wake_does_not_count_as_mama(tmp_path: Path) -> None:
    store = _store(tmp_path)
    store.commit_event(_event("w1", "wake", 1))
    store.commit_event(_event("m1", "mama_play_completed", 2))
    assert store.character("niu-1").mama_count == 1


def test_reset_rejects_old_generation(tmp_path: Path) -> None:
    store = _store(tmp_path)
    store.commit_event(_event("m1", "mama_play_completed", 1))
    new_gen = store.reset_memory("niu-1")
    assert new_gen >= 2
    assert store.character("niu-1").mama_count == 0
    store.commit_event(_event("m1-old", "mama_play_completed", 9, generation=1))
    assert store.character("niu-1").mama_count == 0


def test_restart_restores_counts(tmp_path: Path) -> None:
    path = tmp_path / "niulai.db"
    store = MemoryStore(path)
    store.commit_event(_event("m1", "mama_play_completed", 1))
    store.close()
    restored = MemoryStore(path)
    assert restored.character("niu-1").mama_count == 1


def test_interrupted_run_is_not_completed(tmp_path: Path) -> None:
    store = _store(tmp_path)
    store.commit_event(
        _event("r1", "scene", 1, run_status="interrupted", scene_id="s1", run_id="run-1",
               command_id="cmd-1")
    )
    row = store._conn.execute("SELECT status FROM scene_runs WHERE run_id='run-1'").fetchone()
    assert row["status"] == "interrupted"


def test_oversize_payload_rejected(tmp_path: Path) -> None:
    store = _store(tmp_path)
    with pytest.raises(ValueError):
        store.commit_event(_event("big", "note", 1, payload={"x": "a" * 5000}))


def test_wss_helpers_track_mama_interrupt_and_dedupe(tmp_path: Path) -> None:
    store = _store(tmp_path)
    assert store.bump_mama("niu-1") == 1
    assert store.bump_mama("niu-1") == 2
    store.note_interrupt("niu-1", "正要吐槽")
    store.remember_line("niu-1", "哼，又没人理我")
    notes = store.prompt_memory("niu-1", "ABSENT")
    assert "妈妈" in notes
    assert "2" in notes
    assert "正要吐槽" in notes
    assert "哼，又没人理我" in notes
    again = store.dedupe_line("niu-1", "哼，又没人理我", presence="ABSENT")
    assert again != "哼，又没人理我"
    polite = store.dedupe_line("niu-1", "我在，你说。我是牛来。", presence="PRESENT")
    assert polite == "我在，你说。我是牛来。"


def test_prune_keeps_newest(tmp_path: Path) -> None:
    store = _store(tmp_path)
    for i in range(5):
        store.commit_event(_event(f"e{i}", "note", i, payload={"i": i}))
    store.prune(max_rows=2, max_age_s=7 * 86400)
    n = store._conn.execute("SELECT COUNT(*) AS n FROM device_events").fetchone()["n"]
    assert n == 2
