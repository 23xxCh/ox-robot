from __future__ import annotations

from brain.app.models import ActionIntent, CallResult

PERFORM_VERBS = {"walk", "turn", "stop", "snore", "eyes"}
ALL_VERBS = PERFORM_VERBS | {"say", "sleep", "get_state"}


class McpBroker:
    def __init__(self) -> None:
        self._queue: list[ActionIntent] = []
        self.device_calls: list[dict] = []

    def enqueue(self, intent: ActionIntent) -> None:
        self._queue.append(intent)

    def queued(self) -> list[ActionIntent]:
        return list(self._queue)

    def drop_motion(self) -> None:
        self._queue = [item for item in self._queue if item.verb not in {"walk", "turn"}]

    def call_perform(self, arguments: dict) -> CallResult:
        verb = arguments.get("verb")
        ttl_ms = arguments.get("ttl_ms")
        if verb not in PERFORM_VERBS:
            return CallResult(ok=False, error="unknown-verb")
        if ttl_ms is None:
            return CallResult(ok=False, error="missing-ttl")
        try:
            ttl = int(ttl_ms)
        except (TypeError, ValueError):
            return CallResult(ok=False, error="bad-ttl")
        if ttl < 0:
            return CallResult(ok=False, error="bad-ttl")
        intent = ActionIntent(
            verb=str(verb),
            args={k: v for k, v in arguments.items() if k not in {"verb", "ttl_ms"}},
            ttl_ms=ttl,
        )
        self.device_calls.append(
            {
                "name": "niu.perform",
                "arguments": {"verb": intent.verb, "ttl_ms": ttl, **intent.args},
            }
        )
        self.enqueue(intent)
        return CallResult(ok=True, intent=intent)
