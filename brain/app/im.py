from __future__ import annotations

import json
import os
from typing import Any

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from brain.app.brain import NiulaiBrain

router = APIRouter()


def _brain(request: Request) -> NiulaiBrain:
    return request.app.state.brain


def _seen_event_ids(request: Request) -> set[str]:
    seen = getattr(request.app.state, "im_seen_event_ids", None)
    if seen is None:
        seen = set()
        request.app.state.im_seen_event_ids = seen
    return seen


def _missing_token_response(request: Request) -> JSONResponse | None:
    if not os.environ.get("NIULAI_IM_REQUIRE_TOKEN"):
        return None
    if request.headers.get("token"):
        return None
    return JSONResponse({"ok": False, "error": "missing-token"}, status_code=401)


def _already_seen(request: Request, channel: str, event_id: str | None) -> bool:
    if not event_id:
        return False
    key = f"{channel}:{event_id}"
    seen = _seen_event_ids(request)
    if key in seen:
        return True
    seen.add(key)
    return False


def parse_feishu_text(payload: dict[str, Any]) -> tuple[str, str] | None:
    event = payload.get("event") or {}
    message = event.get("message") or {}
    if message.get("message_type") != "text":
        return None
    chat_id = str(message.get("chat_id") or "")
    raw = message.get("content") or "{}"
    if isinstance(raw, dict):
        text = str(raw.get("text") or "")
    else:
        try:
            text = str(json.loads(raw).get("text") or "")
        except (TypeError, json.JSONDecodeError):
            text = str(raw)
    if not chat_id or not text:
        return None
    return chat_id, text


def parse_wechat_text(payload: dict[str, Any]) -> tuple[str, str] | None:
    if str(payload.get("MsgType") or "").lower() != "text":
        return None
    chat_id = str(payload.get("FromUserName") or "")
    text = str(payload.get("Content") or "")
    if not chat_id or not text:
        return None
    return chat_id, text


def feishu_event_id(payload: dict[str, Any]) -> str | None:
    header = payload.get("header") if isinstance(payload.get("header"), dict) else {}
    event_id = header.get("event_id")
    if event_id:
        return str(event_id)
    event = payload.get("event") if isinstance(payload.get("event"), dict) else {}
    message = event.get("message") if isinstance(event.get("message"), dict) else {}
    message_id = message.get("message_id")
    if message_id:
        return str(message_id)
    return None


def wechat_event_id(payload: dict[str, Any]) -> str | None:
    msg_id = payload.get("MsgId")
    if msg_id is None or msg_id == "":
        return None
    return str(msg_id)


@router.post("/im/feishu/event")
async def feishu_event(request: Request) -> JSONResponse:
    payload = await request.json()
    if payload.get("type") == "url_verification":
        return JSONResponse({"challenge": payload.get("challenge")})
    denied = _missing_token_response(request)
    if denied is not None:
        return denied
    if _already_seen(request, "feishu", feishu_event_id(payload)):
        return JSONResponse({"ok": True})
    parsed = parse_feishu_text(payload)
    if parsed:
        chat_id, text = parsed
        _brain(request).handle_user_text(text, channel="feishu", chat_id=chat_id)
    return JSONResponse({"ok": True})


@router.post("/im/wechat/callback")
async def wechat_callback(request: Request) -> JSONResponse:
    denied = _missing_token_response(request)
    if denied is not None:
        return denied
    payload = await request.json()
    if _already_seen(request, "wechat", wechat_event_id(payload)):
        return JSONResponse({"ok": True})
    parsed = parse_wechat_text(payload)
    if parsed:
        chat_id, text = parsed
        _brain(request).handle_user_text(text, channel="wechat", chat_id=chat_id)
    return JSONResponse({"ok": True})
