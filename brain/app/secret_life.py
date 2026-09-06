from __future__ import annotations

from dataclasses import dataclass

ABSENT_MIN_COOLDOWN_MS = 11_000
ABSENT_COOLDOWN_STEPS_MS = (12_000, 18_000, 24_000, 16_000)
ABSENT_QUIET_EVERY = 3
LOCAL_SECRET_CLIPS = ("secret1.ogg", "secret2.ogg", "secret3.ogg")
SECRET_LINES = (
    "哼，又没人理我。",
    "终于清静了。",
    "又把我当摆件。走就走。",
    "他们一靠近就装死，烦。",
    "清静一会儿都不行。",
    "别以为我不记得被打断。",
)
RECENT_LIMIT = 5


@dataclass(frozen=True)
class SecretBeat:
    kind: str
    text: str = ""
    clip: str = ""
    cooldown_ms: int = ABSENT_MIN_COOLDOWN_MS


def recent_from_memory(memory: str) -> list[str]:
    blob = (memory or "").strip()
    key = "最近说过"
    idx = blob.find(key)
    if idx < 0:
        return []
    payload = blob[idx:]
    if "：" in payload:
        payload = payload.split("：", 1)[1]
    elif ":" in payload:
        payload = payload.split(":", 1)[1]
    if "。独处" in payload:
        payload = payload.split("。独处", 1)[0]
    return [item.strip() for item in payload.split("｜") if item.strip()]


def pick_absent_line(recent: list[str], *, start: int = 0) -> str:
    seen = {item.strip() for item in recent if str(item).strip()}
    n = len(SECRET_LINES)
    for offset in range(n):
        cand = SECRET_LINES[(start + offset) % n]
        if cand not in seen:
            return cand
    return SECRET_LINES[start % n] + "……换一句。"


class SecretDirector:
    def __init__(self, min_cooldown_ms: int = ABSENT_MIN_COOLDOWN_MS) -> None:
        self._min_cooldown_ms = max(0, int(min_cooldown_ms))
        self._last_ms: int | None = None
        self._beats = 0
        self._clip_i = 0
        self._line_i = 0
        self.recent: list[str] = []

    def reset_clock(self) -> None:
        self._last_ms = None
        self._beats = 0

    def note_spoken(self, now_ms: int) -> None:
        self._last_ms = now_ms
        if self._beats == 0:
            self._beats = 1

    def next_delay_s(self) -> float:
        step = ABSENT_COOLDOWN_STEPS_MS[self._beats % len(ABSENT_COOLDOWN_STEPS_MS)]
        return max(self._min_cooldown_ms, step) / 1000.0

    def remember(self, text: str) -> None:
        line = (text or "").strip()
        if not line:
            return
        self.recent.append(line[:120])
        self.recent = self.recent[-RECENT_LIMIT:]

    def decide(
        self,
        now_ms: int,
        *,
        wss_ok: bool = True,
        recent: list[str] | None = None,
    ) -> SecretBeat:
        if self._last_ms is not None and now_ms - self._last_ms < self._min_cooldown_ms:
            return SecretBeat(kind="wait", cooldown_ms=self._min_cooldown_ms)
        delay = max(
            self._min_cooldown_ms,
            ABSENT_COOLDOWN_STEPS_MS[self._beats % len(ABSENT_COOLDOWN_STEPS_MS)],
        )
        self._last_ms = now_ms
        beat = self._beats
        self._beats += 1
        quiet = beat > 0 and beat % ABSENT_QUIET_EVERY == ABSENT_QUIET_EVERY - 1
        if quiet:
            return SecretBeat(kind="quiet", cooldown_ms=delay)
        if not wss_ok:
            clip = LOCAL_SECRET_CLIPS[self._clip_i % len(LOCAL_SECRET_CLIPS)]
            self._clip_i += 1
            return SecretBeat(kind="local", clip=clip, cooldown_ms=delay)
        known = list(recent if recent is not None else self.recent)
        text = pick_absent_line(known, start=self._line_i)
        self._line_i = (self._line_i + 1) % len(SECRET_LINES)
        self.remember(text)
        return SecretBeat(kind="speak", text=text, cooldown_ms=delay)
