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
