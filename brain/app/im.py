from __future__ import annotations

import json
from typing import Any

from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse

from brain.app.brain import NiulaiBrain
from brain.app.auth import require_im_token
from brain.app.clawbot import clawbot_configured, clawbot_event_id, parse_clawbot_text, send_clawbot_text

router = APIRouter(dependencies=[Depends(require_im_token)])


def _brain(request: Request) -> NiulaiBrain:
    return request.app.state.brain


def _seen_event_ids(request: Request) -> set[str]:
    seen = getattr(request.app.state, "im_seen_event_ids", None)
    if seen is None:
        seen = set()
        request.app.state.im_seen_event_ids = seen
    return seen


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
    if _already_seen(request, "feishu", feishu_event_id(payload)):
        return JSONResponse({"ok": True})
    parsed = parse_feishu_text(payload)
    if parsed:
        chat_id, text = parsed
        _brain(request).handle_user_text(text, channel="feishu", chat_id=chat_id)
    return JSONResponse({"ok": True})


@router.post("/im/wechat/callback")
async def wechat_callback(request: Request) -> JSONResponse:
    payload = await request.json()
    if _already_seen(request, "wechat", wechat_event_id(payload)):
        return JSONResponse({"ok": True})
    parsed = parse_wechat_text(payload)
    if parsed:
        chat_id, text = parsed
        _brain(request).handle_user_text(text, channel="wechat", chat_id=chat_id)
    return JSONResponse({"ok": True})


@router.post("/im/clawbot/event")
async def clawbot_event(request: Request) -> JSONResponse:
    payload = await request.json()
    if not isinstance(payload, dict):
        return JSONResponse({"ok": False, "error": "invalid-json"}, status_code=400)
    if _already_seen(request, "clawbot", clawbot_event_id(payload)):
        return JSONResponse({"ok": True, "deduped": True})
    parsed = parse_clawbot_text(payload)
    if not parsed:
        return JSONResponse({"ok": True, "ignored": True})
    chat_id, text = parsed
    outbound = _brain(request).handle_user_text(text, channel="clawbot", chat_id=chat_id)
    delivered = False
    if clawbot_configured() and outbound.text:
        delivered = send_clawbot_text(chat_id, outbound.text)
    return JSONResponse(
        {
            "ok": True,
            "channel": "clawbot",
            "delivered": delivered,
            "configured": clawbot_configured(),
        }
    )
