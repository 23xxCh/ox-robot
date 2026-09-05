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


RECENT_LIMIT = 5
ABSENT_ALTS = (
    "又把我当摆件。走就走。",
    "他们一靠近就装死，烦。",
    "哼，旧账还记着。",
    "清静一会儿都不行。",
    "别以为我不记得被打断。",
)


class MemoryStore:
    def __init__(self, path: str | Path = ":memory:") -> None:
        raw = str(path)
        if raw == ":memory:":
            self.path = Path(":memory:")
            self._conn = sqlite3.connect(":memory:", check_same_thread=False)
        else:
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

    def _ensure(self, device_id: str) -> None:
        row = self._conn.execute(
            "SELECT device_id FROM character_state WHERE device_id = ?", (device_id,)
        ).fetchone()
        if row:
            return
        now = time.time()
        self._conn.execute(
            """
            INSERT INTO character_state(
                device_id, memory_generation, mama_count, pending_complaint,
                recent_line_ids_json, interrupted_goal_json, mood, last_event_id, updated_at
            ) VALUES (?,?,0,NULL,'[]',NULL,NULL,NULL,?)
            """,
            (device_id, 1, now),
        )
        self._conn.commit()

    def _next_seq(self, device_id: str) -> int:
        row = self._conn.execute(
            "SELECT COALESCE(MAX(event_seq), 0) AS n FROM device_events WHERE device_id = ?",
            (device_id,),
        ).fetchone()
        return int(row["n"]) + 1

    def bump_mama(self, device_id: str) -> int:
        now = time.time()
        self.commit_event(
            {
                "event_id": f"mama-{device_id}-{now:.6f}-{self._next_seq(device_id)}",
                "device_id": device_id,
                "boot_id": "wss",
                "event_seq": self._next_seq(device_id),
                "kind": MAMA_KIND,
            }
        )
        view = self.character(device_id)
        return int(view.mama_count) if view else 0

    def recent_lines(self, device_id: str) -> list[str]:
        row = self._conn.execute(
            "SELECT recent_line_ids_json FROM character_state WHERE device_id = ?",
            (device_id,),
        ).fetchone()
        if row is None:
            return []
        try:
            data = json.loads(row["recent_line_ids_json"] or "[]")
        except json.JSONDecodeError:
            return []
        if not isinstance(data, list):
            return []
        return [str(item).strip() for item in data if str(item).strip()]

    def remember_line(self, device_id: str, text: str) -> None:
        line = (text or "").strip()
        if not line:
            return
        self._ensure(device_id)
        lines = self.recent_lines(device_id)
        lines.append(line[:120])
        lines = lines[-RECENT_LIMIT:]
        now = time.time()
        self._conn.execute(
            """
            UPDATE character_state
            SET recent_line_ids_json=?, last_event_id=?, updated_at=?
            WHERE device_id=?
            """,
            (json.dumps(lines, ensure_ascii=False), f"line-{now:.6f}", now, device_id),
        )
        self._conn.commit()

    def note_interrupt(self, device_id: str, what: str) -> None:
        self._ensure(device_id)
        complaint = (what or "").strip()[:200] or "他们打断了我的独处"
        now = time.time()
        self._conn.execute(
            """
            UPDATE character_state
            SET pending_complaint=?, interrupted_goal_json=?, updated_at=?
            WHERE device_id=?
            """,
            (
                complaint,
                json.dumps({"what": complaint}, ensure_ascii=False),
                now,
                device_id,
            ),
        )
        self._conn.commit()

    def prompt_memory(self, device_id: str, presence: str) -> str:
        self._ensure(device_id)
        view = self.character(device_id)
        lines = self.recent_lines(device_id)
        parts: list[str] = []
        if view and view.mama_count:
            parts.append(f"被喊「妈妈」{view.mama_count}次")
        if view and view.pending_complaint:
            parts.append(f"上次被打断时在说：{view.pending_complaint}")
        if lines:
            parts.append("最近说过（不要重复）：" + "｜".join(lines[-RECENT_LIMIT:]))
        if presence == "ABSENT":
            parts.append("独处，翻旧账，不要客套")
        return "。".join(parts)

    def dedupe_line(self, device_id: str, text: str, *, presence: str) -> str:
        line = (text or "").strip()
        if not line:
            return line
        if presence != "ABSENT":
            return line
        recent = self.recent_lines(device_id)
        if line not in recent:
            return line
        for alt in ABSENT_ALTS:
            if alt not in recent:
                return alt
        return line + "……换一句。"
