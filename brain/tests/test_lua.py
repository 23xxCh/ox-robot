from __future__ import annotations

from pathlib import Path

from brain.app.lua_sandbox import LuaSandbox, LuaSandboxError

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts" / "lua"
ALLOWED = {"walk", "turn", "say", "sleep", "snore", "get_state"}


def test_wander_lua_emits_whitelist_intents_without_pulse() -> None:
    sandbox = LuaSandbox()
    intents = sandbox.run_file(SCRIPTS / "wander.lua")
    assert intents
    for intent in intents:
        assert intent.verb in ALLOWED
        assert "pulse_us" not in intent.to_dict()
        assert "pulse_us" not in (intent.args or {})


def test_lua_os_or_io_is_rejected_with_empty_intents() -> None:
    sandbox = LuaSandbox()
    evil = 'os.execute("calc")\nio.open("C:/Windows/win.ini")\nniu.walk("forward", 800)\n'
    try:
        intents = sandbox.run_source(evil)
    except LuaSandboxError:
        intents = []
    assert intents == []
