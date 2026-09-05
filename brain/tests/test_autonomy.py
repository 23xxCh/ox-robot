from __future__ import annotations

from fastapi.testclient import TestClient

from brain.app.brain import NiulaiBrain
from brain.app.main import create_app
from brain.app.persona import PersonaState


def test_secret_alive_pushes_tts_without_user_audio() -> None:
    brain = NiulaiBrain()
    brain.persona.set(PersonaState.SECRET_ALIVE)
    client = TestClient(create_app(brain))
    with client.websocket_connect("/xiaozhi/v1/") as ws:
        ws.send_json({"type": "hello", "version": 1})
        assert ws.receive_json()["type"] == "hello"

        types: list[str] = []
        tts_texts: list[str] = []
        for _ in range(12):
            msg = ws.receive_json()
            types.append(msg["type"])
            if msg["type"] == "tts" and msg.get("text"):
                tts_texts.append(msg["text"])
            if msg["type"] == "tts" and msg.get("state") == "stop":
                break

        assert "tts" in types
        assert any(text.strip() for text in tts_texts)
