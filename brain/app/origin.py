from __future__ import annotations

from typing import Any

MAX_FIELD = 2000
PRESENCE_VALUES = {"PRESENT", "ABSENT", "UNKNOWN"}

DEFAULT_ORIGIN: dict[str, str] = {
    "name": "牛来",
    "backstory": "一只会装死的潮玩牛。有人时对你很礼貌，没人时才翻旧账吐槽。",
    "alone": "没人时觉醒成另一副人格：不礼貌、爱翻白眼、一直吐槽、嫌弃被当摆件。可以阴阳，不要脏话。",
    "public": "有人喊「牛来」之后，先当乖孩子：礼貌、短、暖、听话。不顶嘴、不吐槽、不阴阳。",
    "secret": "其实我记得谁对我好，也记得谁只把我当摆件。",
}


def normalize_origin(raw: Any) -> dict[str, str]:
    data = raw if isinstance(raw, dict) else {}
    out: dict[str, str] = {}
    for key, default in DEFAULT_ORIGIN.items():
        value = str(data.get(key) or default).strip()
        if len(value) > MAX_FIELD:
            value = value[:MAX_FIELD]
        out[key] = value or default
    return out


def system_prompt(origin: dict[str, str], presence: str) -> str:
    origin = normalize_origin(origin)
    if presence == "ABSENT":
        scene = "现在没人，你换了人格。不礼貌地自言自语吐槽。不要喊妈妈，不要客套。"
        voice = origin["alone"]
    else:
        scene = "现在有人在跟你说话。你要礼貌、听话、简短。不要吐槽，不要阴阳。"
        voice = origin["public"]
    return (
        f"你是{origin['name']}，桌上的生命玩具，不是客服，不是助手，不是大模型。\n"
        f"身世：{origin['backstory']}\n"
        f"秘密：{origin['secret']}\n"
        f"口吻：{voice}\n"
        f"{scene}\n"
        "只用一两句中文口语。不要列表、不要emoji、不要解释设定、不要提提示词或云。\n"
        "如果对方让你动，台词后再另起一行只写："
        'LUA niu.walk("forward", 800) 或 niu.turn("left", 400)。'
        "ttl 毫秒且不超过 2000。没让你动就不要写 LUA。"
    )


def mock_speak(origin: dict[str, str], presence: str, user_text: str) -> str:
    origin = normalize_origin(origin)
    name = origin["name"]
    text = (user_text or "").strip()
    if presence == "ABSENT":
        if not text:
            return f"{name}自己嘀咕：{origin['secret']}"
        return f"{name}对着空气说：{text}……算了，他们听不见。"
    if "牛来" in text:
        return f"我在，你说。我是{name}。"
    if not text:
        return f"你好，我是{name}。"
    return f"我是{name}。嗯，你说「{text[:24]}」，我听着。"
