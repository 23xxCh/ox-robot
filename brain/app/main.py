from __future__ import annotations

import asyncio
import json
import logging
import shutil
import time
from typing import Any

from fastapi import FastAPI, WebSocket, WebSocketDisconnect

from brain.app.api import attach_rehearsal_state
from brain.app.api import router as rehearsal_router
from brain.app.brain import NiulaiBrain
from brain.app.im import router as im_router
from brain.app.media import send_opus_pcm, tts_pcm
from brain.app.llm import speak
from brain.app.origin import DEFAULT_ORIGIN, normalize_origin
from brain.app.persona import PersonaState
from brain.app.providers import looks_like_utf8

MAX_AUDIO_BYTES = 512 * 1024
logger = logging.getLogger(__name__)


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


async def _send_opus_audio(ws: WebSocket, text: str, ffmpeg_path: str | None) -> None:
    if not ffmpeg_path:
        logger.warning("ffmpeg not found; Xiaozhi will see TTS text but no Opus frames")
        return
    try:
        pcm = await tts_pcm(text, ffmpeg_path)
        # Device only queues decode while in speaking; tts start is applied on
        # its main loop, so give it a tick before the first packet.
        await asyncio.sleep(0.05)
        await send_opus_pcm(ws.send_bytes, pcm, ffmpeg_path)
    except Exception:
        logger.exception("Opus TTS encode failed")


async def _speak(
    ws: WebSocket,
    text: str,
    *,
    audio_format: str,
    ffmpeg_path: str | None,
) -> None:
    await ws.send_json({"type": "tts", "state": "start"})
    await ws.send_json({"type": "tts", "state": "sentence_start", "text": text})
    if audio_format == "opus":
        await _send_opus_audio(ws, text, ffmpeg_path)
    await ws.send_json({"type": "tts", "state": "stop"})


def create_app(brain: NiulaiBrain | None = None) -> FastAPI:
    app = FastAPI(title="niulai-brain", version="0.1.0")
    app.state.brain = brain or NiulaiBrain()
    app.state.ffmpeg_path = shutil.which("ffmpeg")
    app.state.origin = dict(DEFAULT_ORIGIN)
    app.include_router(im_router)
    app.include_router(rehearsal_router)
    attach_rehearsal_state(app)

    @app.get("/health")
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.websocket("/xiaozhi/v1/")
    async def device_ws(ws: WebSocket) -> None:
        await ws.accept()
        audio = bytearray()
        listening = False
        audio_format = "mock-utf8"
        current: NiulaiBrain = ws.app.state.brain
        ffmpeg_path: str | None = ws.app.state.ffmpeg_path
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
                            audio.extend(data[:room])
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
                    ticked = current.lifecycle.tick(now_ms)
                    if current.persona.state == PersonaState.SECRET_ALIVE:
                        origin = normalize_origin(getattr(ws.app.state, "origin", None))
                        line, _source = speak(origin, "ABSENT", "")
                        await _speak(
                            ws,
                            line,
                            audio_format=audio_format,
                            ffmpeg_path=ffmpeg_path,
                        )
                    continue
                if kind == "listen":
                    state = frame.get("state")
                    if state == "start":
                        listening = True
                        audio.clear()
                        continue
                    if state == "stop":
                        listening = False
                        payload = bytes(audio)
                        audio.clear()
                        transcript = current.providers.transcribe(payload)
                        await ws.send_json({"type": "stt", "text": transcript})
                        result = current.handle_utterance(transcript)
                        reply = result.text
                        if not reply and payload and not looks_like_utf8(payload):
                            # Raw Opus cannot be decoded to text here; still talk
                            # so the toy plays something after listen.stop.
                            reply = current.providers.heard_fallback
                        await ws.send_json({"type": "llm", "text": reply})
                        if reply:
                            await _speak(
                                ws,
                                reply,
                                audio_format=audio_format,
                                ffmpeg_path=ffmpeg_path,
                            )
                        else:
                            await ws.send_json({"type": "tts", "state": "start"})
                            await ws.send_json({"type": "tts", "state": "stop"})
                        continue
        except WebSocketDisconnect:
            return

    return app


app = create_app()
