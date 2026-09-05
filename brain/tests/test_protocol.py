from __future__ import annotations

from fastapi.testclient import TestClient

from brain.app.brain import NiulaiBrain
from brain.app.main import create_app


def test_hello_listen_roundtrip_emits_stt_llm_tts() -> None:
    client = TestClient(create_app(NiulaiBrain()))
    with client.websocket_connect("/xiaozhi/v1/") as ws:
        ws.send_json({"type": "hello", "version": 1, "features": {"mcp": True}})
        hello = ws.receive_json()
        assert hello["type"] == "hello"
        assert hello.get("features", {}).get("mcp") is True

        ws.send_json({"type": "listen", "state": "start"})
        ws.send_bytes("你好牛来".encode("utf-8"))
        ws.send_json({"type": "listen", "state": "stop"})

        types: list[str] = []
        stt_text = None
        tts_stopped = False
        for _ in range(16):
            msg = ws.receive_json()
            types.append(msg["type"])
            if msg["type"] == "stt":
                stt_text = msg.get("text")
            if msg["type"] == "tts" and msg.get("state") == "stop":
                tts_stopped = True
                break

        assert "stt" in types
        assert "llm" in types
        assert "tts" in types
        assert stt_text == "你好牛来"
        assert tts_stopped


def test_mechanical_wake_speaks_mama_not_chat() -> None:
    client = TestClient(create_app(NiulaiBrain()))
    with client.websocket_connect("/xiaozhi/v1/") as ws:
        ws.send_json({"type": "hello", "version": 1})
        ws.receive_json()
        ws.send_json({"type": "listen", "state": "start"})
        ws.send_bytes("牛来牛来".encode("utf-8"))
        ws.send_json({"type": "listen", "state": "stop"})
        texts: list[str] = []
        for _ in range(12):
            msg = ws.receive_json()
            if msg.get("text"):
                texts.append(msg["text"])
            if msg.get("type") == "tts" and msg.get("state") == "stop":
                break
        assert "牛来牛来" in texts
        assert "妈妈" in texts
        assert all("吐槽" not in item for item in texts)


def test_non_object_json_does_not_drop_socket() -> None:
    client = TestClient(create_app(NiulaiBrain()))
    with client.websocket_connect("/xiaozhi/v1/") as ws:
        ws.send_json({"type": "hello", "version": 1})
        assert ws.receive_json()["type"] == "hello"
        ws.send_text("[]")
        msg = ws.receive_json()
        assert msg["type"] == "system"
        assert msg["code"] == "invalid-json"
        ws.send_json({"type": "listen", "state": "start"})
        ws.send_bytes("牛来".encode("utf-8"))
        ws.send_json({"type": "listen", "state": "stop"})
        kinds = [ws.receive_json()["type"] for _ in range(3)]
        assert "stt" in kinds
