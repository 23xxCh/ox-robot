from __future__ import annotations

import re
from pathlib import Path

from brain.app.models import ActionIntent

ALLOWED = {"walk", "turn", "say", "sleep", "snore", "get_state"}
FORBIDDEN = re.compile(
    r"(?<![\w])(os|io|package|dofile|loadfile|require|debug|loadstring|load)\s*[\.\(]"
)
CALL = re.compile(r"niu\.([A-Za-z_][A-Za-z0-9_]*)\s*\((.*)\)\s*$")
MAX_STEPS = 16
MAX_SLEEP_MS = 2000


class LuaSandboxError(RuntimeError):
    pass


def _split_args(raw: str) -> list[str]:
    parts: list[str] = []
    buf: list[str] = []
    quote = None
    i = 0
    while i < len(raw):
        ch = raw[i]
        if quote:
            if ch == "\\" and i + 1 < len(raw):
                buf.append(raw[i + 1])
                i += 2
                continue
            if ch == quote:
                quote = None
            buf.append(ch)
            i += 1
            continue
        if ch in {'"', "'"}:
            quote = ch
            buf.append(ch)
            i += 1
            continue
        if ch == ",":
            parts.append("".join(buf).strip())
            buf = []
            i += 1
            continue
        buf.append(ch)
        i += 1
    if buf:
        parts.append("".join(buf).strip())
    return [p for p in parts if p]


def _parse_value(token: str):
    if token.startswith('"') and token.endswith('"'):
        return token[1:-1]
    if token.startswith("'") and token.endswith("'"):
        return token[1:-1]
    if token in {"true", "false"}:
        return token == "true"
    try:
        if "." in token:
            return float(token)
        return int(token)
    except ValueError:
        return token


def _intent_from_call(verb: str, args: list) -> ActionIntent:
    if verb == "say":
        text = str(args[0]) if args else ""
        return ActionIntent(verb="say", args={"text": text})
    if verb == "walk":
        direction = str(args[0]) if args else "forward"
        ttl = int(args[1]) if len(args) > 1 else 0
        return ActionIntent(verb="walk", args={"dir": direction}, ttl_ms=ttl)
    if verb == "turn":
        direction = str(args[0]) if args else "left"
        ttl = int(args[1]) if len(args) > 1 else 0
        return ActionIntent(verb="turn", args={"dir": direction}, ttl_ms=ttl)
    if verb == "sleep":
        ttl = int(args[0]) if args else 0
        return ActionIntent(verb="sleep", args={}, ttl_ms=min(ttl, MAX_SLEEP_MS))
    if verb == "snore":
        on = True if not args else bool(args[0])
        return ActionIntent(verb="snore", args={"on": on}, ttl_ms=0)
    if verb == "get_state":
        return ActionIntent(verb="get_state", args={})
    raise LuaSandboxError(f"unknown host function niu.{verb}")


class LuaSandbox:
    def run_file(self, path: Path) -> list[ActionIntent]:
        return self.run_source(Path(path).read_text(encoding="utf-8"))

    def run_source(self, source: str) -> list[ActionIntent]:
        if FORBIDDEN.search(source):
            raise LuaSandboxError("forbidden lua capability")
        intents: list[ActionIntent] = []
        for raw_line in source.splitlines():
            line = raw_line.split("--", 1)[0].strip()
            if not line:
                continue
            match = CALL.match(line)
            if not match:
                raise LuaSandboxError(f"unsupported lua: {line}")
            verb = match.group(1)
            if verb not in ALLOWED:
                raise LuaSandboxError(f"unknown host function niu.{verb}")
            args = [_parse_value(token) for token in _split_args(match.group(2))]
            intents.append(_intent_from_call(verb, args))
            if len(intents) > MAX_STEPS:
                raise LuaSandboxError("too many steps")
        return intents
