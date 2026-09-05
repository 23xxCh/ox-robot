from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class ActionIntent:
    verb: str
    args: dict = field(default_factory=dict)
    ttl_ms: int | None = None

    def to_dict(self) -> dict:
        payload = {"verb": self.verb, "args": dict(self.args)}
        if self.ttl_ms is not None:
            payload["ttl_ms"] = self.ttl_ms
        return payload


@dataclass
class CallResult:
    ok: bool
    error: str | None = None
    intent: ActionIntent | None = None


@dataclass
class ImOutbound:
    channel: str
    chat_id: str
    text: str
    intents: list[ActionIntent]
