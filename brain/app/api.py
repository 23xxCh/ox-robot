from __future__ import annotations

import time
import uuid
from pathlib import Path
from typing import Any

from fastapi import APIRouter, FastAPI, Request
from fastapi.responses import FileResponse, JSONResponse

router = APIRouter()
WEB_DIR = Path(__file__).resolve().parent / "web"
MAX_EVENT_LIMIT = 200
DEFAULT_EVENT_LIMIT = 50
MAX_STORED_EVENTS = 500
MAX_EVENT_TEXT = 4096
PRESENCE_VALUES = {"PRESENT", "ABSENT", "UNKNOWN"}

_MODULE_REHEARSAL: dict[str, Any] | None = None


def new_rehearsal_state() -> dict[str, Any]:
    return {
        "connection": "sim",
        "persona": "MECHANICAL",
        "presence": "UNKNOWN",
        "safety": "READY",
        "paused": False,
        "scene_id": None,
        "stale": False,
        "mode": "sim",
        "events": [],
        "next_event_id": 1,
        "memory_generation": 1,
        "memory_items": [],
        "mama_count": 0,
        "pending_complaint": None,
        "mood": None,
        "stop_request_ids": [],
    }


def attach_rehearsal_state(app: FastAPI) -> None:
    app.state.rehearsal = new_rehearsal_state()


def _rehearsal(request: Request) -> dict[str, Any]:
    state = getattr(request.app.state, "rehearsal", None)
    if isinstance(state, dict):
        return state
    global _MODULE_REHEARSAL
    if _MODULE_REHEARSAL is None:
        _MODULE_REHEARSAL = new_rehearsal_state()
    return _MODULE_REHEARSAL


def _public_state(state: dict[str, Any]) -> dict[str, Any]:
    return {
        "connection": state["connection"],
        "persona": state["persona"],
        "presence": state["presence"],
        "safety": state["safety"],
        "paused": bool(state["paused"]),
        "scene_id": state["scene_id"],
        "stale": bool(state["stale"]),
        "mode": state["mode"],
    }


def _clamp_limit(raw: int) -> int:
    try:
        value = int(raw)
    except (TypeError, ValueError):
        value = DEFAULT_EVENT_LIMIT
    if value < 1:
        value = DEFAULT_EVENT_LIMIT
    return min(value, MAX_EVENT_LIMIT)


def _parse_cursor(raw: str | None) -> int:
    if raw is None or raw == "":
        return 0
    try:
        return max(int(raw), 0)
    except (TypeError, ValueError):
        return 0


def _clip_text(value: Any) -> str:
    text = str(value or "")
    if len(text) > MAX_EVENT_TEXT:
        return text[:MAX_EVENT_TEXT]
    return text


def _apply_presence(state: dict[str, Any], presence: str) -> None:
    state["presence"] = presence
    if state["paused"] or presence != "ABSENT" or state.get("safety") != "READY":
        state["persona"] = "MECHANICAL"
        if presence != "ABSENT":
            state["scene_id"] = None
        return
    state["persona"] = "SECRET"
    state["scene_id"] = state.get("scene_id") or "rehearsal_secret"


def _append_event(state: dict[str, Any], **fields: Any) -> dict[str, Any]:
    event_id = int(state["next_event_id"])
    state["next_event_id"] = event_id + 1
    event = {
        "id": event_id,
        "ts": time.time(),
        "simulated": True,
        **fields,
    }
    events = state["events"]
    events.append(event)
    overflow = len(events) - MAX_STORED_EVENTS
    if overflow > 0:
        del events[:overflow]
    return event


def _memory_payload(state: dict[str, Any]) -> dict[str, Any]:
    return {
        "generation": int(state["memory_generation"]),
        "items": list(state["memory_items"]),
        "mama_count": int(state["mama_count"]),
        "pending_complaint": state.get("pending_complaint"),
        "mood": state.get("mood"),
    }


@router.get("/")
async def rehearsal_page() -> FileResponse:
    return FileResponse(WEB_DIR / "index.html", media_type="text/html; charset=utf-8")


@router.get("/web/rehearsal.css")
async def rehearsal_css() -> FileResponse:
    return FileResponse(WEB_DIR / "rehearsal.css", media_type="text/css")


@router.get("/web/rehearsal.js")
async def rehearsal_js() -> FileResponse:
    return FileResponse(WEB_DIR / "rehearsal.js", media_type="application/javascript")


@router.get("/api/v1/state")
async def get_state(request: Request) -> dict[str, Any]:
    return _public_state(_rehearsal(request))


@router.get("/api/v1/events")
async def get_events(
    request: Request,
    cursor: str = "",
    limit: int = DEFAULT_EVENT_LIMIT,
) -> dict[str, Any]:
    state = _rehearsal(request)
    applied = _clamp_limit(limit)
    after = _parse_cursor(cursor)
    selected = [event for event in state["events"] if int(event["id"]) > after][:applied]
    next_cursor = selected[-1]["id"] if selected else after
    return {
        "events": selected,
        "cursor": next_cursor,
        "limit": applied,
    }


@router.post("/api/v1/control/stop")
async def control_stop(request: Request) -> JSONResponse:
    state = _rehearsal(request)
    request_id = uuid.uuid4().hex
    state["stop_request_ids"].append(request_id)
    state["paused"] = True
    state["persona"] = "MECHANICAL"
    state["scene_id"] = None
    _append_event(
        state,
        type="stop_request",
        text="pause requested; physical stop is not claimed",
        request_id=request_id,
    )
    return JSONResponse({"request_id": request_id}, status_code=202)


@router.get("/api/v1/memory")
async def get_memory(request: Request) -> dict[str, Any]:
    return _memory_payload(_rehearsal(request))


@router.delete("/api/v1/memory")
async def delete_memory(request: Request) -> dict[str, Any]:
    state = _rehearsal(request)
    state["memory_generation"] = int(state["memory_generation"]) + 1
    state["memory_items"] = []
    state["mama_count"] = 0
    state["pending_complaint"] = None
    state["mood"] = None
    _append_event(
        state,
        type="memory_reset",
        text="semantic memory cleared",
        generation=state["memory_generation"],
    )
    return _memory_payload(state)


@router.post("/api/v1/rehearsal/events")
async def post_rehearsal_event(request: Request) -> JSONResponse:
    state = _rehearsal(request)
    if state.get("mode") != "sim":
        return JSONResponse({"error": "rehearsal_events_only_in_sim"}, status_code=403)
    try:
        payload = await request.json()
    except Exception:
        return JSONResponse({"error": "invalid_json"}, status_code=400)
    if not isinstance(payload, dict):
        return JSONResponse({"error": "invalid_body"}, status_code=400)

    raw_type = _clip_text(payload.get("type")).strip()
    if not raw_type:
        return JSONResponse({"error": "type_required"}, status_code=400)

    presence_in = payload.get("presence")
    kind = raw_type
    presence: str | None = None
    if presence_in is not None:
        presence = str(presence_in).strip().upper()
        if presence not in PRESENCE_VALUES:
            return JSONResponse({"error": "invalid_presence"}, status_code=400)
        kind = "presence"
    elif raw_type.upper() in PRESENCE_VALUES:
        presence = raw_type.upper()
        kind = "presence"

    text = payload.get("text")
    event_fields: dict[str, Any] = {
        "type": kind,
        "simulated": True,
    }
    if text is not None:
        event_fields["text"] = _clip_text(text)
    if presence is not None:
        event_fields["presence"] = presence
        _apply_presence(state, presence)

    event = _append_event(state, **event_fields)
    return JSONResponse({"ok": True, "simulated": True, "event": event})
