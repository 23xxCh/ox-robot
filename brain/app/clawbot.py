from __future__ import annotations

import base64
import logging
import os
import random
import struct
from typing import Any

import httpx

logger = logging.getLogger(__name__)

DEFAULT_ILINK = "https://ilinkai.weixin.qq.com"


def clawbot_configured() -> bool:
    return bool((os.environ.get("NIULAI_CLAWBOT_TOKEN") or "").strip())


def clawbot_base_url() -> str:
    return (os.environ.get("NIULAI_CLAWBOT_BASE_URL") or DEFAULT_ILINK).rstrip("/")


def _text_from_items(items: Any) -> str:
    if not isinstance(items, list):
        return ""
    parts: list[str] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        kind = str(item.get("type") or item.get("item_type") or "").lower()
        if kind and kind not in {"text", "txt", "1"}:
            continue
        text = item.get("text") or item.get("content") or item.get("plain")
        if text:
            parts.append(str(text))
    return "".join(parts).strip()


def parse_clawbot_text(payload: dict[str, Any]) -> tuple[str, str] | None:
    """Accept OpenClaw hook, iLink getupdates item, or a flat {from,text} body."""
    if not isinstance(payload, dict):
        return None

    nested = payload.get("message")
    if isinstance(nested, dict):
        inner = parse_clawbot_text(nested)
        if inner:
            return inner

    chat_id = str(
        payload.get("session_id")
        or payload.get("from_user_id")
        or payload.get("from_user")
        or payload.get("FromUserName")
        or payload.get("from")
        or payload.get("chat_id")
        or payload.get("to")
        or payload.get("sessionKey")
        or ""
    )
    raw_text = payload.get("text")
    if raw_text is None:
        raw_text = payload.get("Content")
    if isinstance(payload.get("content"), str):
        raw_text = raw_text or payload.get("content")
    if isinstance(payload.get("message"), str):
        raw_text = raw_text or payload.get("message")
    text = str(raw_text or "").strip()
    if not text:
        text = _text_from_items(payload.get("item_list") or payload.get("items"))
    if not chat_id or not text:
        return None
    if len(text) > 2000:
        text = text[:2000]
    return chat_id, text


def clawbot_event_id(payload: dict[str, Any]) -> str | None:
    if not isinstance(payload, dict):
        return None
    nested = payload.get("message")
    if isinstance(nested, dict):
        inner = clawbot_event_id(nested)
        if inner:
            return inner
    for key in ("msg_id", "MsgId", "message_id", "seq", "event_id", "sessionKey"):
        value = payload.get(key)
        if value is not None and str(value):
            return str(value)
    return None


def _ilink_headers(token: str) -> dict[str, str]:
    uin = struct.pack(">I", random.randint(0, 0xFFFFFFFF))
    # Spec: decimal string of uint32, then base64.
    raw = str(int.from_bytes(uin, "big")).encode("ascii")
    return {
        "Content-Type": "application/json",
        "AuthorizationType": "ilink_bot_token",
        "X-WECHAT-UIN": base64.b64encode(raw).decode("ascii"),
        "iLink-App-Id": "bot",
        "iLink-App-ClientVersion": os.environ.get("NIULAI_CLAWBOT_CLIENT_VERSION") or "132102",
        "Authorization": f"Bearer {token}",
    }


def send_clawbot_text(chat_id: str, text: str) -> bool:
    token = (os.environ.get("NIULAI_CLAWBOT_TOKEN") or "").strip()
    if not token or not chat_id or not text:
        return False
    url = clawbot_base_url() + "/ilink/bot/sendmessage"
    body = {
        "session_id": chat_id,
        "item_list": [{"type": "text", "text": text}],
    }
    try:
        response = httpx.post(url, headers=_ilink_headers(token), json=body, timeout=15.0)
        response.raise_for_status()
        return True
    except Exception:
        logger.exception("ClawBot sendmessage failed")
        return False
