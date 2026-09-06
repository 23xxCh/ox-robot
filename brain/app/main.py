from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import os
import random
import shutil
import subprocess
import time
from collections.abc import Callable, Coroutine
from typing import Any

from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse

from brain.app.api import attach_rehearsal_state
from brain.app.api import router as rehearsal_router
from brain.app.brain import NiulaiBrain
from brain.app.auth import has_bearer, local_ui_allowed
from brain.app.im import router as im_router
from brain.app.lifecycle import ABSENT_HOLD_MS, Presence
from brain.app.media import send_opus_pcm, try_qwen_asr, tts_pcm
from pathlib import Path

from brain.app.llm import _load_env_files, speak
from brain.app.models import ActionIntent
from brain.app.origin import DEFAULT_ORIGIN, normalize_origin
from brain.app.schemas import MAX_PERFORM_TTL_MS
from brain.app.scripting import motion_intents
from brain.app.providers import looks_like_utf8
from brain.app.secret_life import SecretDirector

MAX_AUDIO_BYTES = 512 * 1024
MUTTER_INTERVAL_S = 12.0
DEFAULT_MEMORY = Path(__file__).resolve().parents[1] / "data" / "niulai-memory.sqlite"
_REPO_ROOT = Path(__file__).resolve().parents[2]
logger = logging.getLogger(__name__)


def _git_executable() -> str | None:
    found = shutil.which("git")
    if found:
        return found
    for candidate in (
        r"C:\Program Files\Git\cmd\git.exe",
        r"C:\Program Files\Git\bin\git.exe",
    ):
        if Path(candidate).is_file():
            return candidate
    return None


def _source_digest(path: Path | None = None) -> str:
    return hashlib.sha256((path or Path(__file__)).read_bytes()).hexdigest()[:12]


def resolve_source_state() -> tuple[str, bool | None]:
    """Read local Git evidence once; unknown status must not imply a clean tree."""
    git = _git_executable()
    if not git:
        return "unknown", None
    try:
        proc = subprocess.run(
            [git, "rev-parse", "--verify", "HEAD"],
            cwd=str(_REPO_ROOT), check=False, capture_output=True, text=True, timeout=2,
        )
    except (OSError, subprocess.TimeoutExpired):
        return "unknown", None
    commit = (proc.stdout or "").strip().lower()
    if (
        proc.returncode != 0 or len(commit) not in {40, 64}
        or any(ch not in "0123456789abcdef" for ch in commit)
    ):
        return "unknown", None
    dirty = None
    try:
        proc = subprocess.run(
            [git, "--no-optional-locks", "status", "--porcelain=v1", "--untracked-files=normal"],
            cwd=str(_REPO_ROOT), check=False, capture_output=True, text=True, timeout=2,
        )
        if proc.returncode == 0:
            dirty = bool(proc.stdout.strip())
    except (OSError, subprocess.TimeoutExpired):
        pass
    return commit, dirty


def resolve_brain_version(source_commit: str | None = None) -> str:
    pinned = (os.environ.get("NIULAI_BRAIN_VERSION") or "").strip()
    if (
        pinned
        and len(pinned) <= 64
        and all(ch.isalnum() or ch in ".-_" for ch in pinned)
        and "sk-" not in pinned.lower()
        and "token" not in pinned.lower()
    ):
        return pinned
    commit = source_commit if source_commit is not None else resolve_source_state()[0]
    if commit != "unknown":
        return commit[:12]
    return f"src-{_source_digest()}"


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
    return _remember_line(brain, device_id, presence, user_text, line)


def _remember_line(
    brain: NiulaiBrain, device_id: str, presence: str, user_text: str, line: str
) -> tuple[str, list[ActionIntent]]:
    mem = brain.memory
    line, intents = motion_intents(user_text, line)
    if mem:
        line = mem.dedupe_line(device_id, line, presence=presence)
        mem.remember_line(device_id, line)
        if presence == "ABSENT":
            mem.consume_interrupt(device_id)
    return line, intents


async def _compose_line_async(
    brain: NiulaiBrain,
    device_id: str,
    presence: str,
    origin: dict[str, str],
    user_text: str,
    still_current: Callable[[], bool],
) -> tuple[str, list[ActionIntent]]:
    notes = brain.memory.prompt_memory(device_id, presence) if brain.memory else ""
    # Only the network provider runs in a worker; SQLite remains on this loop.
    line, _source = await asyncio.to_thread(speak, origin, presence, user_text, memory=notes)
    if not still_current():
        raise asyncio.CancelledError
    return _remember_line(brain, device_id, presence, user_text, line)


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
    ws: WebSocket,
    intents: list[ActionIntent],
    brain: NiulaiBrain,
    still_current: Callable[[], bool] | None = None,
) -> None:
    if brain.mcp.block_motion:
        return
    for intent in intents:
        if still_current is not None and not still_current():
            return
        if intent.verb not in {"walk", "turn"}:
            continue
        ttl = int(intent.ttl_ms)
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
    _load_env_files()
    source_commit, source_dirty = resolve_source_state()
    app = FastAPI(title="niulai-brain", version=resolve_brain_version(source_commit))
    app.state.brain = brain or NiulaiBrain(memory_path=DEFAULT_MEMORY)
    app.state.ffmpeg_path = shutil.which("ffmpeg")
    app.state.origin = dict(DEFAULT_ORIGIN)
    app.include_router(im_router)
    app.include_router(rehearsal_router)
    attach_rehearsal_state(app)

    @app.middleware("http")
    async def local_ui(request: Request, call_next):
        if request.url.path != "/health" and not request.url.path.startswith("/im/"):
            if not local_ui_allowed(request):
                return JSONResponse({"error": "local_ui_only"}, status_code=403)
        return await call_next(request)

    firmware_source_path = "firmware/xiaozhi-niulai/niulai_life.cc"
    try:
        firmware_source_hash = _source_digest(_REPO_ROOT / firmware_source_path)
    except FileNotFoundError:
        firmware_source_hash = "missing"
    except OSError:
        firmware_source_hash = "unknown"

    @app.get("/health")
    async def health() -> dict[str, Any]:
        return {
            "status": "ok",
            "version": app.version,
            "source_commit": source_commit,
            "source_dirty": source_dirty,
            "source_metadata_scope": "startup",
            # Legacy alias: this is one local source file, never a flashed image.
            "firmware_hash": firmware_source_hash,
            "firmware_source_hash": firmware_source_hash,
            "firmware_source_path": firmware_source_path,
            "firmware_runtime_verified": False,
        }

    @app.websocket("/xiaozhi/v1/")
    async def device_ws(ws: WebSocket) -> None:
        if not has_bearer(ws.headers, "NIULAI_DEVICE_TOKEN"):
            await ws.close(code=1008)
            return
        await ws.accept()
        audio = bytearray()
        packets: list[bytes] = []
        listening = False
        audio_format = "mock-utf8"
        session_presence = "UNKNOWN"
        current: NiulaiBrain = ws.app.state.brain
        ffmpeg_path: str | None = ws.app.state.ffmpeg_path
        speech_task: asyncio.Task[None] | None = None
        speech_tasks: set[asyncio.Task[None]] = set()
        device_id = _device_id(ws)
        last_spoken = ""
        speech_generation = 0
        director = SecretDirector(min_cooldown_ms=int(MUTTER_INTERVAL_S * 1000))

        def speak_guard() -> Callable[[], bool]:
            token = speech_generation
            return lambda: speech_generation == token

        async def mutter_loop(still_current: Callable[[], bool]) -> None:
            nonlocal last_spoken
            while still_current():
                await asyncio.sleep(director.next_delay_s())
                if not still_current():
                    return
                beat = director.decide(int(time.time() * 1000), wss_ok=True)
                if beat.kind != "speak":
                    continue
                origin = normalize_origin(getattr(ws.app.state, "origin", None))
                line, _intents = await _compose_line_async(
                    current, device_id, "ABSENT", origin, "", still_current
                )
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

        def stop_speech() -> None:
            nonlocal speech_generation, speech_task
            speech_generation += 1
            for task in speech_tasks:
                task.cancel()
            speech_task = None

        def speech_done(task: asyncio.Task[None]) -> None:
            speech_tasks.discard(task)
            if not task.cancelled() and task.exception() is not None:
                logger.error("Speech task failed", exc_info=task.exception())

        def start_speech(reply: Coroutine[Any, Any, None]) -> None:
            nonlocal speech_task
            stop_speech()
            speech_task = asyncio.create_task(reply)
            speech_tasks.add(speech_task)
            speech_task.add_done_callback(speech_done)

        async def speak_absent() -> None:
            nonlocal last_spoken
            still_current = speak_guard()
            origin = normalize_origin(getattr(ws.app.state, "origin", None))
            line, _intents = await _compose_line_async(
                current, device_id, "ABSENT", origin, "", still_current
            )
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
                await mutter_loop(still_current)

        async def reply_to_listen(
            heard: str | None = None,
            payload: bytes = b"",
            frame_packets: list[bytes] | None = None,
        ) -> None:
            nonlocal last_spoken
            still_current = speak_guard()
            presence = session_presence if session_presence in {"PRESENT", "ABSENT"} else "PRESENT"
            transcript = heard if heard is not None else current.providers.transcribe(payload)
            if (
                heard is None and not transcript and payload
                and not looks_like_utf8(payload) and ffmpeg_path
            ):
                try:
                    transcript = (await try_qwen_asr(frame_packets or [], ffmpeg_path)) or ""
                except Exception:
                    logger.exception("ASR failed")
                    transcript = ""
            if not still_current():
                return
            await ws.send_json({"type": "stt", "text": transcript})
            current.handle_utterance(transcript, now_ms=int(time.time() * 1000))
            origin = normalize_origin(getattr(ws.app.state, "origin", None))
            intents: list[ActionIntent] = []
            if transcript or presence == "ABSENT":
                reply, intents = await _compose_line_async(
                    current, device_id, presence, origin, transcript, still_current
                )
            else:
                reply = "我在，你再说一次。" if payload else ""
            if not still_current():
                return
            if reply:
                last_spoken = reply
            emotion = (
                random.choice(["sleepy", "winking", "thinking", "angry", "surprised"])
                if presence == "ABSENT" else "happy"
            )
            await ws.send_json({"type": "llm", "text": reply, "emotion": emotion})
            if reply:
                await _speak(
                    ws, reply, audio_format=audio_format, ffmpeg_path=ffmpeg_path,
                    still_current=still_current,
                )
            else:
                await ws.send_json({"type": "tts", "state": "start"})
                await ws.send_json({"type": "tts", "state": "stop"})
            if still_current() and heard is None:
                await _send_motion(ws, intents, current, still_current)

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
                    # Presence belongs to this connection; a shared SECRET brain
                    # does not authorize speech during a fresh polite handshake.
                    continue
                if kind == "abort":
                    if last_spoken and current.memory:
                        current.memory.note_interrupt(device_id, last_spoken)
                    stop_speech()
                    listening = False
                    audio.clear()
                    packets.clear()
                    continue
                if kind == "niulai":
                    presence = str(frame.get("presence") or "")
                    now_ms = int(time.time() * 1000)
                    if presence in {"PRESENT", "UNKNOWN"}:
                        if session_presence == "ABSENT" and last_spoken and current.memory:
                            current.memory.note_interrupt(device_id, last_spoken)
                        session_presence = presence
                        current.lifecycle.set_presence(
                            Presence(presence), source="device", now_ms=now_ms
                        )
                        stop_speech()
                        listening = False
                        audio.clear()
                        packets.clear()
                        continue
                    if presence == "ABSENT":
                        already_absent = session_presence == "ABSENT"
                        mutter_alive = speech_task is not None and not speech_task.done()
                        session_presence = "ABSENT"
                        current.lifecycle.set_presence(
                            Presence.ABSENT,
                            source="device",
                            now_ms=now_ms - ABSENT_HOLD_MS,
                        )
                        current.lifecycle.tick(now_ms)
                        if already_absent and mutter_alive:
                            continue
                        start_speech(speak_absent())
                        continue
                    continue
                if kind == "listen":
                    state = frame.get("state")
                    if state == "start":
                        stop_speech()
                        listening = True
                        audio.clear()
                        packets.clear()
                        continue
                    if state == "detect":
                        session_presence = "PRESENT"
                        heard = str(frame.get("text") or "牛来")
                        current.handle_utterance(heard, now_ms=int(time.time() * 1000))
                        if current.memory and "牛来" in heard:
                            current.memory.bump_mama(device_id)
                        start_speech(reply_to_listen(heard=heard))
                        continue
                    if state == "stop":
                        listening = False
                        payload = bytes(audio)
                        frame_packets = list(packets)
                        audio.clear()
                        packets.clear()
                        start_speech(reply_to_listen(payload=payload, frame_packets=frame_packets))
                        continue
        except WebSocketDisconnect:
            return
        finally:
            stop_speech()
            if speech_tasks:
                await asyncio.gather(*speech_tasks, return_exceptions=True)

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
