from __future__ import annotations

import json
import sqlite3
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

SCHEMA_VERSION = 1
MAX_PAYLOAD = 4096
MAMA_KIND = "mama_play_completed"


@dataclass(frozen=True)
class CharacterView:
    device_id: str
    memory_generation: int
    mama_count: int
    pending_complaint: str | None
    mood: str | None
    last_event_id: str | None


class MemoryStore:
    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(self.path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA foreign_keys = ON")
        self._migrate()

    def close(self) -> None:
        self._conn.close()

    def _migrate(self) -> None:
        cur = self._conn.cursor()
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS schema_migrations (
                version INTEGER PRIMARY KEY,
                applied_at TEXT NOT NULL,
                checksum TEXT NOT NULL
            )
            """
        )
        applied = {row["version"] for row in cur.execute("SELECT version FROM schema_migrations")}
        if SCHEMA_VERSION not in applied:
            cur.executescript(
                """
                CREATE TABLE IF NOT EXISTS device_events (
                    event_id TEXT PRIMARY KEY,
                    device_id TEXT NOT NULL,
                    boot_id TEXT NOT NULL,
                    event_seq INTEGER NOT NULL,
                    memory_generation INTEGER NOT NULL,
                    kind TEXT NOT NULL,
                    epoch INTEGER NOT NULL,
                    device_mono_ms INTEGER NOT NULL,
                    received_at REAL NOT NULL,
                    payload_json TEXT NOT NULL,
                    UNIQUE (device_id, boot_id, event_seq)
                );
                CREATE INDEX IF NOT EXISTS idx_events_received
                    ON device_events (device_id, received_at);
                CREATE TABLE IF NOT EXISTS character_state (
                    device_id TEXT PRIMARY KEY,
                    memory_generation INTEGER NOT NULL,
                    mama_count INTEGER NOT NULL CHECK (mama_count >= 0),
                    pending_complaint TEXT,
                    recent_line_ids_json TEXT NOT NULL,
                    interrupted_goal_json TEXT,
                    mood TEXT,
                    last_event_id TEXT,
                    updated_at REAL NOT NULL
                );
                CREATE TABLE IF NOT EXISTS scene_runs (
                    run_id TEXT PRIMARY KEY,
                    device_id TEXT NOT NULL,
                    boot_id TEXT NOT NULL,
                    command_id TEXT NOT NULL,
                    trigger_event_id TEXT,
                    scene_id TEXT NOT NULL,
                    epoch INTEGER NOT NULL,
                    status TEXT NOT NULL,
                    reason TEXT,
                    started_at REAL,
                    ended_at REAL,
                    UNIQUE (device_id, boot_id, command_id)
                );
                """
            )
            cur.execute(
                "INSERT INTO schema_migrations(version, applied_at, checksum) VALUES (?,?,?)",
                (SCHEMA_VERSION, time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "init"),
            )
            self._conn.commit()

    def commit_event(self, event: dict[str, Any]) -> bool:
        payload = event.get("payload_json", event.get("payload", {}))
        if isinstance(payload, (dict, list)):
            payload_text = json.dumps(payload, ensure_ascii=False)
        else:
            payload_text = str(payload or "")
        if len(payload_text.encode("utf-8")) > MAX_PAYLOAD:
            raise ValueError("payload-too-large")
        event_id = str(event["event_id"])
        device_id = str(event["device_id"])
        generation = int(event.get("memory_generation") or 1)
        kind = str(event["kind"])
        now = float(event.get("received_at") or time.time())
        cur = self._conn.cursor()
        existing = cur.execute(
            "SELECT event_id FROM device_events WHERE event_id = ?", (event_id,)
        ).fetchone()
        if existing:
            return False
        state = cur.execute(
            "SELECT * FROM character_state WHERE device_id = ?", (device_id,)
        ).fetchone()
        current_gen = int(state["memory_generation"]) if state else 1
        if generation < current_gen:
            return False
        if state is None:
            cur.execute(
                """
                INSERT INTO character_state(
                    device_id, memory_generation, mama_count, pending_complaint,
                    recent_line_ids_json, interrupted_goal_json, mood, last_event_id, updated_at
                ) VALUES (?,?,0,NULL,'[]',NULL,NULL,NULL,?)
                """,
                (device_id, generation, now),
            )
            mama_count = 0
        else:
            mama_count = int(state["mama_count"])
            generation = max(current_gen, generation)
        cur.execute(
            """
            INSERT INTO device_events(
                event_id, device_id, boot_id, event_seq, memory_generation, kind,
                epoch, device_mono_ms, received_at, payload_json
            ) VALUES (?,?,?,?,?,?,?,?,?,?)
            """,
            (
                event_id,
                device_id,
                str(event.get("boot_id") or "boot"),
                int(event.get("event_seq") or 0),
                generation,
                kind,
                int(event.get("epoch") or 0),
                int(event.get("device_mono_ms") or 0),
                now,
                payload_text,
            ),
        )
        if kind == MAMA_KIND:
            mama_count += 1
        status = event.get("run_status")
        if status:
            cur.execute(
                """
                INSERT OR REPLACE INTO scene_runs(
                    run_id, device_id, boot_id, command_id, trigger_event_id, scene_id,
                    epoch, status, reason, started_at, ended_at
                ) VALUES (?,?,?,?,?,?,?,?,?,?,?)
                """,
                (
                    str(event.get("run_id") or event_id),
                    device_id,
                    str(event.get("boot_id") or "boot"),
                    str(event.get("command_id") or event_id),
                    event_id,
                    str(event.get("scene_id") or ""),
                    int(event.get("epoch") or 0),
                    str(status),
                    event.get("reason"),
                    now if status == "started" else event.get("started_at"),
                    now if status in {"completed", "cancelled", "interrupted"} else None,
                ),
            )
        cur.execute(
            """
            UPDATE character_state
            SET memory_generation=?, mama_count=?, last_event_id=?, updated_at=?
            WHERE device_id=?
            """,
            (generation, mama_count, event_id, now, device_id),
        )
        self._conn.commit()
        return True

    def character(self, device_id: str) -> CharacterView | None:
        row = self._conn.execute(
            "SELECT * FROM character_state WHERE device_id = ?", (device_id,)
        ).fetchone()
        if row is None:
            return None
        return CharacterView(
            device_id=device_id,
            memory_generation=int(row["memory_generation"]),
            mama_count=int(row["mama_count"]),
            pending_complaint=row["pending_complaint"],
            mood=row["mood"],
            last_event_id=row["last_event_id"],
        )

    def reset_memory(self, device_id: str) -> int:
        cur = self._conn.cursor()
        row = cur.execute(
            "SELECT memory_generation FROM character_state WHERE device_id = ?",
            (device_id,),
        ).fetchone()
        new_gen = int(row["memory_generation"]) + 1 if row else 1
        now = time.time()
        cur.execute("DELETE FROM device_events WHERE device_id = ?", (device_id,))
        cur.execute("DELETE FROM scene_runs WHERE device_id = ?", (device_id,))
        cur.execute("DELETE FROM character_state WHERE device_id = ?", (device_id,))
        cur.execute(
            """
            INSERT INTO character_state(
                device_id, memory_generation, mama_count, pending_complaint,
                recent_line_ids_json, interrupted_goal_json, mood, last_event_id, updated_at
            ) VALUES (?,?,0,NULL,'[]',NULL,NULL,NULL,?)
            """,
            (device_id, new_gen, now),
        )
        self._conn.commit()
        return new_gen

    def prune(self, *, max_rows: int = 10000, max_age_s: int = 7 * 86400) -> int:
        now = time.time()
        cur = self._conn.cursor()
        cur.execute(
            "DELETE FROM device_events WHERE received_at < ?",
            (now - max_age_s,),
        )
        count = cur.execute("SELECT COUNT(*) AS n FROM device_events").fetchone()["n"]
        deleted = 0
        if count > max_rows:
            extra = count - max_rows
            cur.execute(
                """
                DELETE FROM device_events WHERE event_id IN (
                    SELECT event_id FROM device_events ORDER BY received_at ASC LIMIT ?
                )
                """,
                (extra,),
            )
            deleted = extra
        self._conn.commit()
        return deleted
