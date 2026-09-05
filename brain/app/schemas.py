from __future__ import annotations

from typing import Any

PERFORM_VERBS = frozenset({"walk", "turn", "stop", "snore", "eyes"})
MOTION_VERBS = frozenset({"walk", "turn"})
ALLOWED_DIRS = frozenset({"forward", "back", "left", "right", "stop"})
PERFORM_FIELDS = frozenset({"verb", "ttl_ms", "dir"})
MAX_PERFORM_TTL_MS = 2000


def validate_perform_arguments(arguments: Any) -> str | None:
    """Return a CallResult error code, or None when the perform payload is valid."""
    if not isinstance(arguments, dict):
        return "bad-schema"
    extra = set(arguments) - PERFORM_FIELDS
    if extra:
        return "unknown-field"
    verb = arguments.get("verb")
    if verb not in PERFORM_VERBS:
        return "unknown-verb"
    if "dir" in arguments:
        if verb not in MOTION_VERBS:
            return "unknown-field"
        if arguments.get("dir") not in ALLOWED_DIRS:
            return "bad-dir"
    if "ttl_ms" not in arguments or arguments.get("ttl_ms") is None:
        return "missing-ttl"
    ttl_ms = arguments["ttl_ms"]
    # bool is a subclass of int; TTL must be a real, finite integer.
    if isinstance(ttl_ms, bool) or not isinstance(ttl_ms, int):
        return "bad-ttl"
    if ttl_ms < 0 or ttl_ms > MAX_PERFORM_TTL_MS:
        return "bad-ttl"
    return None
