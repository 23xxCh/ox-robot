from __future__ import annotations

from brain.app.scripting import lua_from_user, motion_intents, split_speech_and_lua


def test_walk_request_compiles_lua_walk() -> None:
    spoken, intents = motion_intents("往前走两步", "好，我挪一下。")
    assert "挪" in spoken
    assert intents
    assert intents[0].verb == "walk"
    assert intents[0].args.get("dir") == "forward"
    assert intents[0].ttl_ms <= 2000


def test_llm_lua_line_is_stripped_from_speech() -> None:
    spoken, lua = split_speech_and_lua('行，我走。\nLUA niu.walk("forward", 800)')
    assert spoken == "行，我走。"
    assert "niu.walk" in lua
    _, intents = motion_intents("走", '行，我走。\nLUA niu.walk("forward", 800)')
    assert intents[0].verb == "walk"


def test_lua_from_user_turn_left() -> None:
    assert "left" in lua_from_user("向左转")
