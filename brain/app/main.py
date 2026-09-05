from __future__ import annotations

import json
import time

from fastapi import FastAPI, WebSocket, WebSocketDisconnect

from brain.app.api import attach_rehearsal_state
from brain.app.api import router as rehearsal_router
from brain.app.brain import NiulaiBrain
from brain.app.im import router as im_router
from brain.app.persona import PersonaState

MAX_AUDIO_BYTES = 512 * 1024


async def _speak(ws: WebSocket, text: str) -> None:
    await ws.send_json({"type": "tts", "state": "start"})
    await ws.send_json({"type": "tts", "state": "sentence_start", "text": text})
    await ws.send_json({"type": "tts", "state": "stop"})


def create_app(brain: NiulaiBrain | None = None) -> FastAPI:
    app = FastAPI(title="niulai-brain", version="0.1.0")
    app.state.brain = brain or NiulaiBrain()
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
        current: NiulaiBrain = ws.app.state.brain
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
                    await ws.send_json(
                        {
                            "type": "hello",
                            "transport": "websocket",
                            "version": 1,
                            "audio_params": {
                                "format": "mock-utf8",
                                "sample_rate": 16000,
                                "channels": 1,
                                "frame_duration": 60,
                            },
                            "features": {"mcp": True},
                            "session": "sim",
                        }
                    )
                    now_ms = int(time.time() * 1000)
                    ticked = current.lifecycle.tick(now_ms)
                    if current.persona.state == PersonaState.SECRET_ALIVE:
                        spoken = [
                            str(item.args.get("text") or "")
                            for item in (ticked or current.autonomy_intents())
                            if item.verb == "say" and item.args.get("text")
                        ]
                        await _speak(ws, spoken[0] if spoken else "哼，又没人理我")
                    continue
                if kind == "listen":
                    state = frame.get("state")
                    if state == "start":
                        listening = True
                        audio.clear()
                        continue
                    if state == "stop":
                        listening = False
                        transcript = current.providers.transcribe(bytes(audio))
                        audio.clear()
                        await ws.send_json({"type": "stt", "text": transcript})
                        result = current.handle_utterance(transcript)
                        reply = result.text
                        await ws.send_json({"type": "llm", "text": reply})
                        if reply:
                            await _speak(ws, reply)
                        else:
                            await ws.send_json({"type": "tts", "state": "start"})
                            await ws.send_json({"type": "tts", "state": "stop"})
                        continue
        except WebSocketDisconnect:
            return

    return app


app = create_app()
