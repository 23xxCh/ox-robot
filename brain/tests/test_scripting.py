from __future__ import annotations

import pytest

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


@pytest.mark.parametrize(
    "user_text",
    ["你好", "右边有什么", "怎么走", "会不会动", "不要走", "不要向左转", "我刚才往前走了", "你会走吗", "走？", "停止是什么意思", "别停"],
)
@pytest.mark.parametrize("model_lua", ["", '\nLUA niu.walk("forward", 800)'])
def test_description_question_or_negation_never_authorizes_motion(user_text, model_lua):
    spoken, intents = motion_intents(user_text, "我听着。" + model_lua)
    assert spoken == "我听着。"
    assert intents == []


@pytest.mark.parametrize(
    "user_text,verb,direction,ttl",
    [
        ("走", "walk", "forward", 800),
        ("往前走两步", "walk", "forward", 800),
        ("向左转", "turn", "left", 800),
        ("向右转", "turn", "right", 800),
        ("往后走", "walk", "back", 800),
        ("停", "walk", "stop", 0),
        ("不要动", "walk", "stop", 0),
        ("别动", "walk", "stop", 0),
    ],
)
def test_user_command_controls_motion_instead_of_model_lua(user_text, verb, direction, ttl):
    spoken, intents = motion_intents(user_text, '收到。\nLUA niu.walk("back", 9000)')
    assert spoken == "收到。"
    assert len(intents) == 1
    assert (intents[0].verb, intents[0].args["dir"], intents[0].ttl_ms) == (verb, direction, ttl)
