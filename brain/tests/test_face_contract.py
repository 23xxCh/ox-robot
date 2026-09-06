from __future__ import annotations

from fastapi.testclient import TestClient

from brain.app.brain import NiulaiBrain
from brain.app.main import create_app

LISTEN_FAMILY = {"listening", "neutral", "relaxed", "robot_2"}
SMILE_FAMILY = {"happy", "laughing", "loving", "funny", "cool"}
SECRET_FACES = {"sleepy", "winking", "thinking", "angry", "surprised", "confused", "shocked"}
DRAWN_STATES = 7


def test_seven_drawn_faces_and_alias_families() -> None:
    assert DRAWN_STATES == 7
    assert not (LISTEN_FAMILY & SMILE_FAMILY)
    assert not (LISTEN_FAMILY & SECRET_FACES)
    assert not (SMILE_FAMILY & SECRET_FACES)


def test_present_llm_emotion_is_public_smile_not_secret() -> None:
    client = TestClient(create_app(NiulaiBrain()))
    with client.websocket_connect("/xiaozhi/v1/") as ws:
        ws.send_json({"type": "hello", "version": 1})
        ws.receive_json()
        ws.send_json({"type": "listen", "state": "detect", "text": "牛来"})
        emotions: list[str] = []
        for _ in range(16):
            msg = ws.receive_json()
            if msg.get("type") == "llm" and msg.get("emotion"):
                emotions.append(str(msg["emotion"]))
            if msg.get("type") == "tts" and msg.get("state") == "stop":
                break
        assert emotions
        assert all(item in SMILE_FAMILY or item in LISTEN_FAMILY for item in emotions)
        assert all(item not in SECRET_FACES for item in emotions)


def test_absent_llm_emotion_is_secret_face() -> None:
    client = TestClient(create_app(NiulaiBrain()))
    with client.websocket_connect("/xiaozhi/v1/") as ws:
        ws.send_json({"type": "hello", "version": 1})
        ws.receive_json()
        ws.send_json({"type": "niulai", "presence": "ABSENT"})
        emotion = None
        for _ in range(16):
            msg = ws.receive_json()
            if msg.get("type") == "llm" and msg.get("emotion"):
                emotion = str(msg["emotion"])
            if msg.get("type") == "tts" and msg.get("state") == "stop":
                break
        assert emotion in SECRET_FACES
