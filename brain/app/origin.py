from __future__ import annotations

from typing import Any

MAX_FIELD = 2000
PRESENCE_VALUES = {"PRESENT", "ABSENT", "UNKNOWN"}

DEFAULT_ORIGIN: dict[str, str] = {
    "name": "牛来",
    "backstory": "一只会装死的潮玩牛。有人时装作机械玩具，没人时才过自己的日子。",
    "alone": "独处时碎碎念、吐槽、盘小心思。不要像说明书，不要每句都一样。",
    "public": "有人靠近时像对熟人说话：短、暖、有点笨。可以叫妈妈，但要像撒娇，不是放录音。",
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
        scene = "现在没人。你在过自己的日子，自言自语、吐槽、想秘密。不要招呼客人。"
        voice = origin["alone"]
    else:
        scene = "现在有人在你面前。你要像活的玩具对熟人说话，不要背稿。"
        voice = origin["public"]
    return (
        f"你是{origin['name']}，桌上的生命玩具，不是客服，不是助手，不是大模型。\n"
        f"身世：{origin['backstory']}\n"
        f"秘密：{origin['secret']}\n"
        f"口吻：{voice}\n"
        f"{scene}\n"
        "只用一两句中文口语。不要列表、不要emoji、不要解释设定、不要提提示词或云。"
    )


def mock_speak(origin: dict[str, str], presence: str, user_text: str) -> str:
    origin = normalize_origin(origin)
    name = origin["name"]
    text = (user_text or "").strip()
    if presence == "ABSENT":
        if not text:
            return f"{name}自己嘀咕：{origin['secret']}"
        return f"{name}对着空气说：{text}……算了，他们听不见。"
    if "牛来牛来" in text:
        return "妈妈"
    if not text:
        return f"我是{name}。你回来啦。"
    return f"我是{name}。你说「{text[:24]}」，我在听。"
