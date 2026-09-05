from __future__ import annotations

import math
from dataclasses import dataclass, field
from enum import Enum

from brain.app.models import ActionIntent
from brain.app.persona import PersonaFSM, PersonaState

ABSENT_HOLD_MS = 8000
AUTONOMY_INTERVAL_MS = 12000
NEAR_CM = 20
WAKE_WORD = "牛来"
MAMA_TEXT = "妈妈"
PRIVATE_LINE = "终于清静了，我得偷偷吐槽两句。"
AUTONOMY_LINE = "哼，又没人理我"


class Presence(str, Enum):
    PRESENT = "PRESENT"
    ABSENT = "ABSENT"
    UNKNOWN = "UNKNOWN"


class SafetyState(str, Enum):
    BOOT_SAFE = "BOOT_SAFE"
    READY = "READY"
    SAFE_STOP = "SAFE_STOP"
    E_STOP_LATCHED = "E_STOP_LATCHED"


class ProximityKind(str, Enum):
    NEAR = "NEAR"
    FAR = "FAR"
    UNKNOWN = "UNKNOWN"


@dataclass(frozen=True)
class PresenceSnapshot:
    value: Presence
    source: str
    observed_at_ms: int

    def freshness_ms(self, now_ms: int) -> int:
        return max(0, now_ms - self.observed_at_ms)


@dataclass(frozen=True)
class ProximityReading:
    kind: ProximityKind
    cm: float | None
    source: str
    observed_at_ms: int


@dataclass
class UtteranceResult:
    text: str
    intents: list[ActionIntent] = field(default_factory=list)


class Lifecycle:
    def __init__(
        self,
        *,
        absent_hold_ms: int = ABSENT_HOLD_MS,
        autonomy_interval_ms: int = AUTONOMY_INTERVAL_MS,
        safety: SafetyState = SafetyState.READY,
    ) -> None:
        self.persona = PersonaFSM(PersonaState.FREEZE)
        self._absent_hold_ms = absent_hold_ms
        self._autonomy_interval_ms = autonomy_interval_ms
        self._safety = SafetyState(safety)
        self._presence = Presence.UNKNOWN
        self._presence_source = "boot"
        self._presence_at_ms = 0
        self._absent_since_ms: int | None = None
        self._last_autonomy_ms: int | None = None
        self._proximity = ProximityReading(
            kind=ProximityKind.UNKNOWN,
            cm=None,
            source="ultrasonic",
            observed_at_ms=0,
        )
        self.persona_epoch = 0

    @property
    def presence(self) -> PresenceSnapshot:
        return PresenceSnapshot(
            value=self._presence,
            source=self._presence_source,
            observed_at_ms=self._presence_at_ms,
        )

    @property
    def proximity(self) -> ProximityReading:
        return self._proximity

    @property
    def safety(self) -> SafetyState:
        return self._safety

    def set_safety(self, value: SafetyState | str, *, now_ms: int) -> None:
        self._safety = value if isinstance(value, SafetyState) else SafetyState(value)
        if self._safety != SafetyState.READY:
            self._enter_mechanical()
            return
        self._maybe_enter_secret(now_ms)

    def set_presence(
        self,
        value: Presence | str,
        *,
        source: str = "operator_demo",
        now_ms: int,
    ) -> None:
        presence = value if isinstance(value, Presence) else Presence(value)
        self._presence = presence
        self._presence_source = source
        self._presence_at_ms = now_ms
        if presence in {Presence.PRESENT, Presence.UNKNOWN}:
            self._absent_since_ms = None
            self._enter_mechanical()
            return
        if self._absent_since_ms is None:
            self._absent_since_ms = now_ms
        self._maybe_enter_secret(now_ms)

    def ingest_proximity(
        self,
        cm: float | None = None,
        *,
        now_ms: int,
        timeout: bool = False,
        source: str = "ultrasonic",
    ) -> ProximityReading:
        kind = ProximityKind.UNKNOWN
        distance: float | None = None
        if not timeout and cm is not None:
            try:
                value = float(cm)
            except (TypeError, ValueError):
                value = math.nan
            if math.isfinite(value) and value >= 0:
                distance = value
                kind = ProximityKind.NEAR if value < NEAR_CM else ProximityKind.FAR
        self._proximity = ProximityReading(
            kind=kind,
            cm=distance,
            source=source,
            observed_at_ms=now_ms,
        )
        # Distance is proximity only: never promote or demote presence to ABSENT.
        return self._proximity

    def tick(self, now_ms: int) -> list[ActionIntent]:
        self._maybe_enter_secret(now_ms)
        if not self.persona.allows_secret_speech():
            return []
        if (
            self._last_autonomy_ms is not None
            and now_ms - self._last_autonomy_ms < self._autonomy_interval_ms
        ):
            return []
        self._last_autonomy_ms = now_ms
        return [ActionIntent(verb="say", args={"text": AUTONOMY_LINE})]

    def handle_utterance(self, text: str, now_ms: int) -> UtteranceResult:
        spoken = text or ""
        if WAKE_WORD in spoken:
            self.set_presence(Presence.PRESENT, source="wake", now_ms=now_ms)
            if self._safety != SafetyState.READY:
                return UtteranceResult(text="", intents=[])
            return UtteranceResult(text=MAMA_TEXT, intents=[])
        if self.persona.allows_secret_speech():
            return UtteranceResult(text=PRIVATE_LINE, intents=[])
        return UtteranceResult(text="", intents=[])

    def _enter_mechanical(self) -> None:
        if self.persona.state != PersonaState.FREEZE:
            self.persona_epoch += 1
        self.persona.set(PersonaState.FREEZE)
        self._last_autonomy_ms = None

    def _enter_secret(self) -> None:
        if self.persona.state == PersonaState.SECRET_ALIVE:
            return
        self.persona.set(PersonaState.SECRET_ALIVE)
        self.persona_epoch += 1
        self._last_autonomy_ms = None

    def _maybe_enter_secret(self, now_ms: int) -> None:
        if self._presence != Presence.ABSENT:
            return
        if self._safety != SafetyState.READY:
            return
        if self._absent_since_ms is None:
            return
        if now_ms - self._absent_since_ms < self._absent_hold_ms:
            return
        self._enter_secret()
