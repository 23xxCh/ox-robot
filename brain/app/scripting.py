from __future__ import annotations

import re

from brain.app.lua_sandbox import LuaSandbox, LuaSandboxError
from brain.app.models import ActionIntent
from brain.app.schemas import MAX_PERFORM_TTL_MS

LUA_LINE = re.compile(r"^(?:LUA\s+)?(niu\.[A-Za-z_]+\(.*\))\s*$")
FENCE = re.compile(r"```(?:lua)?\s*([\s\S]*?)```", re.I)


def split_speech_and_lua(text: str) -> tuple[str, str]:
    spoken_lines: list[str] = []
    lua_lines: list[str] = []
    for raw in (text or "").splitlines():
        line = raw.strip()
        match = LUA_LINE.match(line)
        if match and line.startswith(("LUA", "niu.")):
            lua_lines.append(match.group(1))
            continue
        spoken_lines.append(raw)
    spoken = "\n".join(spoken_lines).strip()
    fences = FENCE.findall(text or "")
    for block in fences:
        for raw in block.splitlines():
            line = raw.strip()
            match = LUA_LINE.match(line)
            if match:
                lua_lines.append(match.group(1))
        spoken = FENCE.sub("", spoken).strip()
    return spoken, "\n".join(lua_lines)


def lua_from_user(text: str) -> str:
    spoken = (text or "").strip().rstrip("。！!").strip()
    if not spoken:
        return ""
    if spoken in {"停", "停下", "停止", "不要动", "别动"}:
        return 'niu.walk("stop", 0)'
    # ponytail: fixed whole-utterance commands; extend only with verified phrases.
    if re.fullmatch(r"(?:向|往)?左转(?:一下)?", spoken):
        return 'niu.turn("left", 800)'
    if re.fullmatch(r"(?:向|往)?右转(?:一下)?", spoken):
        return 'niu.turn("right", 800)'
    if re.fullmatch(r"(?:(?:向|往)后走|后退)(?:一步|两步|一下)?", spoken):
        return 'niu.walk("back", 800)'
    if re.fullmatch(r"(?:(?:向|往)前)?走(?:一步|两步|一下)?", spoken):
        return 'niu.walk("forward", 800)'
    return ""


def intents_from_lua(source: str) -> list[ActionIntent]:
    if not source.strip():
        return []
    try:
        intents = LuaSandbox().run_source(source)
    except (LuaSandboxError, ValueError):
        return []
    out: list[ActionIntent] = []
    for intent in intents:
        ttl = int(intent.ttl_ms or 0)
        if ttl > MAX_PERFORM_TTL_MS:
            intent.ttl_ms = MAX_PERFORM_TTL_MS
        if intent.verb == "walk" and not intent.args.get("dir"):
            intent.args["dir"] = "forward"
        out.append(intent)
    return out


def motion_intents(user_text: str, model_text: str) -> tuple[str, list[ActionIntent]]:
    spoken, _model_lua = split_speech_and_lua(model_text)
    return spoken, intents_from_lua(lua_from_user(user_text))
