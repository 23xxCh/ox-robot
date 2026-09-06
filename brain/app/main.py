from __future__ import annotations

import asyncio
import contextlib
import json
import logging
import random
import shutil
import time
from collections.abc import Callable
from typing import Any

from fastapi import FastAPI, WebSocket, WebSocketDisconnect

from brain.app.api import attach_rehearsal_state
from brain.app.api import router as rehearsal_router
from brain.app.brain import NiulaiBrain
from brain.app.im import router as im_router
from brain.app.lifecycle import ABSENT_HOLD_MS, Presence
from brain.app.media import send_opus_pcm, try_qwen_asr, tts_pcm
from pathlib import Path

from brain.app.llm import speak
from brain.app.models import ActionIntent
from brain.app.origin import DEFAULT_ORIGIN, normalize_origin
from brain.app.schemas import MAX_PERFORM_TTL_MS
from brain.app.scripting import motion_intents
from brain.app.persona import PersonaState
from brain.app.providers import looks_like_utf8
from brain.app.secret_life import SecretDirector

MAX_AUDIO_BYTES = 512 * 1024
MUTTER_INTERVAL_S = 12.0
DEFAULT_MEMORY = Path(__file__).resolve().parents[1] / "data" / "niulai-memory.sqlite"
logger = logging.getLogger(__name__)


def _device_id(ws: WebSocket) -> str:
    return (ws.headers.get("device-id") or "niu-1").strip() or "niu-1"


def _compose_line(
    brain: NiulaiBrain,
    device_id: str,
    presence: str,
    origin: dict[str, str],
    user_text: str,
) -> tuple[str, list[ActionIntent]]:
    mem = brain.memory
    notes = mem.prompt_memory(device_id, presence) if mem else ""
    line, _source = speak(origin, presence, user_text, memory=notes)
    line, intents = motion_intents(user_text, line)
    if mem:
        line = mem.dedupe_line(device_id, line, presence=presence)
        mem.remember_line(device_id, line)
    return line, intents


def _client_wants_opus(frame: dict[str, Any], ws: WebSocket) -> bool:
    params = frame.get("audio_params")
    if isinstance(params, dict) and str(params.get("format") or "").lower() == "opus":
        return True
    return bool(ws.headers.get("device-id"))


def _hello_audio_params(opus: bool) -> dict[str, Any]:
    # Xiaozhi firmware ParseServerHello uses sample_rate/frame_duration for the
    # Opus decoder. Board DAC is 24 kHz; official servers advertise 24 kHz 60 ms.
    if opus:
        return {
            "format": "opus",
            "sample_rate": 24000,
            "channels": 1,
            "frame_duration": 60,
        }
    return {
        "format": "mock-utf8",
        "sample_rate": 16000,
        "channels": 1,
        "frame_duration": 60,
    }


async def _send_opus_audio(
    ws: WebSocket,
    text: str,
    ffmpeg_path: str | None,
    still_current: Callable[[], bool] | None = None,
) -> None:
    if not ffmpeg_path:
        logger.warning("ffmpeg not found; Xiaozhi will see TTS text but no Opus frames")
        return
    try:
        pcm = await tts_pcm(text, ffmpeg_path)
        if still_current is not None and not still_current():
            return
        # Device only queues decode while in speaking; tts start is applied on
        # its main loop, so give it a tick before the first packet.
        await asyncio.sleep(0.05)
        if still_current is not None and not still_current():
            return
        await send_opus_pcm(ws.send_bytes, pcm, ffmpeg_path, alive=still_current)
    except asyncio.CancelledError:
        raise
    except Exception:
        logger.exception("Opus TTS encode failed")


async def _speak(
    ws: WebSocket,
    text: str,
    *,
    audio_format: str,
    ffmpeg_path: str | None,
    still_current: Callable[[], bool] | None = None,
) -> None:
    try:
        if still_current is not None and not still_current():
            return
        await ws.send_json({"type": "tts", "state": "start"})
        if still_current is not None and not still_current():
            return
        await ws.send_json({"type": "tts", "state": "sentence_start", "text": text})
        if audio_format == "opus":
            await _send_opus_audio(
                ws, text, ffmpeg_path, still_current=still_current
            )
        if still_current is not None and not still_current():
            return
        await ws.send_json({"type": "tts", "state": "stop"})
    except (WebSocketDisconnect, RuntimeError):
        return


async def _send_motion(
    ws: WebSocket, intents: list[ActionIntent], brain: NiulaiBrain
) -> None:
    if brain.mcp.block_motion:
        return
    for intent in intents:
        if intent.verb not in {"walk", "turn"}:
            continue
        ttl = int(intent.ttl_ms or 800)
        if ttl <= 0 and intent.args.get("dir") != "stop":
            ttl = 800
        if ttl > MAX_PERFORM_TTL_MS:
            ttl = MAX_PERFORM_TTL_MS
        await ws.send_json(
            {
                "type": "niulai",
                "motion": intent.verb,
                "dir": str(intent.args.get("dir") or "forward"),
                "ms": ttl,
            }
        )


def create_app(brain: NiulaiBrain | None = None) -> FastAPI:
    app = FastAPI(title="niulai-brain", version="0.1.0")
    app.state.brain = brain or NiulaiBrain(memory_path=DEFAULT_MEMORY)
    app.state.ffmpeg_path = shutil.which("ffmpeg")
    app.state.origin = dict(DEFAULT_ORIGIN)
    app.include_router(im_router)
    app.include_router(rehearsal_router)
    attach_rehearsal_state(app)

    @app.get("/health")
    async def health() -> dict[str, str]:
        return {"status": "ok", "version": app.version}

    @app.websocket("/xiaozhi/v1/")
    async def device_ws(ws: WebSocket) -> None:
        await ws.accept()
        audio = bytearray()
        packets: list[bytes] = []
        listening = False
        audio_format = "mock-utf8"
        session_presence = "UNKNOWN"
        current: NiulaiBrain = ws.app.state.brain
        ffmpeg_path: str | None = ws.app.state.ffmpeg_path
        mutter_task: asyncio.Task[None] | None = None
        device_id = _device_id(ws)
        last_spoken = ""
        speech_generation = 0
        director = SecretDirector(min_cooldown_ms=int(MUTTER_INTERVAL_S * 1000))

        def speak_guard() -> Callable[[], bool]:
            token = speech_generation
            return lambda: speech_generation == token

        async def mutter_loop() -> None:
            nonlocal last_spoken
            while True:
                await asyncio.sleep(director.next_delay_s())
                still_current = speak_guard()
                beat = director.decide(int(time.time() * 1000), wss_ok=True)
                if beat.kind != "speak":
                    continue
                origin = normalize_origin(getattr(ws.app.state, "origin", None))
                line, _intents = _compose_line(current, device_id, "ABSENT", origin, "")
                last_spoken = line
                director.remember(line)
                if not still_current():
                    continue
                await ws.send_json(
                    {
                        "type": "llm",
                        "text": line,
                        "emotion": random.choice(
                            ["sleepy", "winking", "thinking", "angry", "surprised"]
                        ),
                    }
                )
                await _speak(
                    ws,
                    line,
                    audio_format=audio_format,
                    ffmpeg_path=ffmpeg_path,
                    still_current=still_current,
                )

        def ensure_mutter() -> None:
            nonlocal mutter_task
            if mutter_task is None or mutter_task.done():
                mutter_task = asyncio.create_task(mutter_loop())

        def stop_mutter() -> None:
            nonlocal mutter_task, speech_generation
            speech_generation += 1
            if mutter_task is not None:
                mutter_task.cancel()
                mutter_task = None

        async def speak_absent() -> None:
            nonlocal last_spoken
            still_current = speak_guard()
            origin = normalize_origin(getattr(ws.app.state, "origin", None))
            line, _intents = _compose_line(current, device_id, "ABSENT", origin, "")
            last_spoken = line
            director.note_spoken(int(time.time() * 1000))
            director.remember(line)
            if not still_current():
                return
            await ws.send_json(
                {
                    "type": "llm",
                    "text": line,
                    "emotion": random.choice(
                        ["sleepy", "winking", "thinking", "angry", "surprised"]
                    ),
                }
            )
            await _speak(
                ws,
                line,
                audio_format=audio_format,
                ffmpeg_path=ffmpeg_path,
                still_current=still_current,
            )
            if still_current():
                ensure_mutter()

        try:
            while True:
                message = await ws.receive()
                if message.get("type") == "websocket.disconnect":
                    break
                data = message.get("bytes")
                if data is not None:
                    if listening:
                        room = MAX_AUDIO_BYTES - len(audio)
                        if room > 0:
                            chunk = bytes(data[:room])
                            audio.extend(chunk)
                            packets.append(chunk)
                    continue
                text = message.get("text")
                if not text:
                    continue
                try:
                    frame = json.loads(text)
                except json.JSONDecodeError:
                    await ws.send_json({"type": "system", "code": "invalid-json"})
                    continue
                if not isinstance(frame, dict):
                    await ws.send_json({"type": "system", "code": "invalid-json"})
                    continue
                kind = frame.get("type")
                if kind == "hello":
                    audio_format = "opus" if _client_wants_opus(frame, ws) else "mock-utf8"
                    await ws.send_json(
                        {
                            "type": "hello",
                            "transport": "websocket",
                            "version": 1,
                            "audio_params": _hello_audio_params(audio_format == "opus"),
                            "features": {"mcp": True},
                            "session": "sim",
                            "session_id": "sim",
                        }
                    )
                    now_ms = int(time.time() * 1000)
                    current.lifecycle.tick(now_ms)
                    if current.persona.state == PersonaState.SECRET_ALIVE:
                        await speak_absent()
                    continue
                if kind == "abort":
                    if last_spoken and current.memory:
                        current.memory.note_interrupt(device_id, last_spoken)
                    stop_mutter()
                    continue
                if kind == "niulai":
                    presence = str(frame.get("presence") or "")
                    now_ms = int(time.time() * 1000)
                    if presence == "PRESENT":
                        if session_presence == "ABSENT" and last_spoken and current.memory:
                            current.memory.note_interrupt(device_id, last_spoken)
                        session_presence = "PRESENT"
                        current.lifecycle.set_presence(
                            Presence.PRESENT, source="device", now_ms=now_ms
                        )
                        stop_mutter()
                        continue
                    if presence == "ABSENT":
                        already_absent = session_presence == "ABSENT"
                        mutter_alive = mutter_task is not None and not mutter_task.done()
                        session_presence = "ABSENT"
                        current.lifecycle.set_presence(
                            Presence.ABSENT,
                            source="device",
                            now_ms=now_ms - ABSENT_HOLD_MS,
                        )
                        current.lifecycle.tick(now_ms)
                        if already_absent and mutter_alive:
                            continue
                        await speak_absent()
                        continue
                    continue
                if kind == "listen":
                    state = frame.get("state")
                    if state == "start":
                        listening = True
                        audio.clear()
                        packets.clear()
                        continue
                    if state == "detect":
                        stop_mutter()
                        session_presence = "PRESENT"
                        heard = str(frame.get("text") or "牛来")
                        current.handle_utterance(heard, now_ms=int(time.time() * 1000))
                        if current.memory and "牛来" in heard:
                            current.memory.bump_mama(device_id)
                        origin = normalize_origin(getattr(ws.app.state, "origin", None))
                        line, _intents = _compose_line(
                            current, device_id, "PRESENT", origin, heard
                        )
                        last_spoken = line
                        still_current = speak_guard()
                        await ws.send_json({"type": "stt", "text": heard})
                        await ws.send_json({"type": "llm", "text": line, "emotion": "happy"})
                        await _speak(
                            ws,
                            line,
                            audio_format=audio_format,
                            ffmpeg_path=ffmpeg_path,
                            still_current=still_current,
                        )
                        continue
                    if state == "stop":
                        listening = False
                        payload = bytes(audio)
                        frame_packets = list(packets)
                        audio.clear()
                        packets.clear()
                        transcript = current.providers.transcribe(payload)
                        if not transcript and payload and not looks_like_utf8(payload):
                            if ffmpeg_path:
                                try:
                                    transcript = (
                                        await try_qwen_asr(frame_packets, ffmpeg_path)
                                    ) or ""
                                except Exception:
                                    logger.exception("ASR failed")
                                    transcript = ""
                        still_current = speak_guard()
                        await ws.send_json({"type": "stt", "text": transcript})
                        current.handle_utterance(transcript, now_ms=int(time.time() * 1000))
                        presence = session_presence if session_presence in {"PRESENT", "ABSENT"} else "PRESENT"
                        origin = normalize_origin(getattr(ws.app.state, "origin", None))
                        intents: list[ActionIntent] = []
                        if presence == "ABSENT":
                            reply, intents = _compose_line(
                                current, device_id, "ABSENT", origin, transcript or ""
                            )
                        elif transcript:
                            reply, intents = _compose_line(
                                current, device_id, "PRESENT", origin, transcript
                            )
                        elif payload:
                            reply = "我在，你再说一次。"
                        else:
                            reply = ""
                        if reply:
                            last_spoken = reply
                        emotion = (
                            random.choice(["sleepy", "winking", "thinking", "angry", "surprised"])
                            if presence == "ABSENT"
                            else "happy"
                        )
                        await ws.send_json({"type": "llm", "text": reply, "emotion": emotion})
                        if reply:
                            await _speak(
                                ws,
                                reply,
                                audio_format=audio_format,
                                ffmpeg_path=ffmpeg_path,
                                still_current=still_current,
                            )
                        else:
                            await ws.send_json({"type": "tts", "state": "start"})
                            await ws.send_json({"type": "tts", "state": "stop"})
                        await _send_motion(ws, intents, current)
                        continue
        except WebSocketDisconnect:
            return
        finally:
            pending = mutter_task
            stop_mutter()
            if pending is not None:
                with contextlib.suppress(asyncio.CancelledError):
                    await pending

    return app


class _LazyApp:
    def __init__(self) -> None:
        self._app: FastAPI | None = None

    def _unwrap(self) -> FastAPI:
        if self._app is None:
            self._app = create_app()
        return self._app

    def __getattr__(self, name: str) -> Any:
        return getattr(self._unwrap(), name)

    async def __call__(self, scope: Any, receive: Any, send: Any) -> None:
        await self._unwrap()(scope, receive, send)


app = _LazyApp()
