from __future__ import annotations

import json
from typing import Any

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from brain.app.brain import NiulaiBrain

router = APIRouter()


def _brain(request: Request) -> NiulaiBrain:
    return request.app.state.brain


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


@router.post("/im/feishu/event")
async def feishu_event(request: Request) -> JSONResponse:
    payload = await request.json()
    if payload.get("type") == "url_verification":
        return JSONResponse({"challenge": payload.get("challenge")})
    parsed = parse_feishu_text(payload)
    if parsed:
        chat_id, text = parsed
        _brain(request).handle_user_text(text, channel="feishu", chat_id=chat_id)
    return JSONResponse({"ok": True})


@router.post("/im/wechat/callback")
async def wechat_callback(request: Request) -> JSONResponse:
    payload = await request.json()
    parsed = parse_wechat_text(payload)
    if parsed:
        chat_id, text = parsed
        _brain(request).handle_user_text(text, channel="wechat", chat_id=chat_id)
    return JSONResponse({"ok": True})
