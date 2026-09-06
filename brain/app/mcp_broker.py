from __future__ import annotations

from brain.app.models import ActionIntent, CallResult
from brain.app.schemas import MOTION_VERBS, PERFORM_VERBS, validate_perform_arguments

ALL_VERBS = set(PERFORM_VERBS) | {"say", "sleep", "get_state"}


class McpBroker:
    def __init__(self) -> None:
        self._queue: list[ActionIntent] = []
        self.device_calls: list[dict] = []
        self.block_motion = False

    def enqueue(self, intent: ActionIntent) -> None:
        self._queue.append(intent)

    def queued(self) -> list[ActionIntent]:
        return list(self._queue)

    def drop_motion(self) -> None:
        self._queue = [item for item in self._queue if item.verb not in {"walk", "turn"}]
        self.block_motion = True

    def allow_motion(self) -> None:
        self.block_motion = False

    def call_perform(self, arguments: dict) -> CallResult:
        error = validate_perform_arguments(arguments)
        if error:
            return CallResult(ok=False, error=error)
        verb = str(arguments["verb"])
        if verb in MOTION_VERBS and self.block_motion:
            return CallResult(ok=False, error="frozen")
        ttl = int(arguments["ttl_ms"])
        args: dict = {}
        if verb in MOTION_VERBS and "dir" in arguments:
            args["dir"] = arguments["dir"]
        intent = ActionIntent(verb=verb, args=args, ttl_ms=ttl)
        self.device_calls.append(
            {
                "name": "niu.perform",
                "arguments": {"verb": intent.verb, "ttl_ms": ttl, **intent.args},
            }
        )
        self.enqueue(intent)
        return CallResult(ok=True, intent=intent)
