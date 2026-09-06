from __future__ import annotations

import asyncio

from fastapi.testclient import TestClient

from brain.app.brain import NiulaiBrain
from brain.app.main import _send_opus_audio, create_app


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


def test_wake_counts_mama_and_absent_uses_interrupt() -> None:
    brain = NiulaiBrain()
    client = TestClient(create_app(brain))
    with client.websocket_connect("/xiaozhi/v1/") as ws:
        ws.send_json({"type": "hello", "version": 1})
        ws.receive_json()
        ws.send_json({"type": "listen", "state": "detect", "text": "牛来"})
        for _ in range(12):
            msg = ws.receive_json()
            if msg.get("type") == "tts" and msg.get("state") == "stop":
                break
        assert brain.memory is not None
        assert brain.memory.character("niu-1") is not None
        assert brain.memory.character("niu-1").mama_count == 1
        ws.send_json({"type": "niulai", "presence": "ABSENT"})
        first = ""
        for _ in range(12):
            msg = ws.receive_json()
            if msg.get("type") == "llm" and msg.get("text"):
                first = str(msg["text"])
            if msg.get("type") == "tts" and msg.get("state") == "stop":
                break
        assert first
        ws.send_json({"type": "abort"})
        ws.send_json({"type": "niulai", "presence": "PRESENT"})
        ws.send_json({"type": "niulai", "presence": "ABSENT"})
        second = ""
        for _ in range(12):
            msg = ws.receive_json()
            if msg.get("type") == "llm" and msg.get("text"):
                second = str(msg["text"])
            if msg.get("type") == "tts" and msg.get("state") == "stop":
                break
        assert second
        assert "妈妈" not in second
        complaint = brain.memory.character("niu-1").pending_complaint
        assert complaint
        notes = brain.memory.prompt_memory("niu-1", "ABSENT")
        assert "打断" in notes or complaint[:8] in notes


def test_present_wake_is_polite_not_roast() -> None:
    client = TestClient(create_app(NiulaiBrain()))
    with client.websocket_connect("/xiaozhi/v1/") as ws:
        ws.send_json({"type": "hello", "version": 1})
        ws.receive_json()
        ws.send_json({"type": "listen", "state": "detect", "text": "牛来"})
        texts: list[str] = []
        for _ in range(12):
            msg = ws.receive_json()
            if msg.get("text"):
                texts.append(msg["text"])
            if msg.get("type") == "tts" and msg.get("state") == "stop":
                break
        assert "牛来" in texts
        assert any("我在" in item for item in texts)
        assert all("妈妈" not in item for item in texts)
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


def test_hello_without_audio_params_keeps_mock_utf8() -> None:
    client = TestClient(create_app(NiulaiBrain()))
    with client.websocket_connect("/xiaozhi/v1/") as ws:
        ws.send_json({"type": "hello", "version": 1, "features": {"mcp": True}})
        hello = ws.receive_json()
        assert hello["audio_params"]["format"] == "mock-utf8"


def test_hello_requests_opus_advertises_opus() -> None:
    client = TestClient(create_app(NiulaiBrain()))
    with client.websocket_connect("/xiaozhi/v1/") as ws:
        ws.send_json(
            {
                "type": "hello",
                "version": 1,
                "transport": "websocket",
                "audio_params": {
                    "format": "opus",
                    "sample_rate": 16000,
                    "channels": 1,
                    "frame_duration": 60,
                },
                "features": {"mcp": True},
            }
        )
        hello = ws.receive_json()
        assert hello["type"] == "hello"
        assert hello["transport"] == "websocket"
        assert hello["audio_params"]["format"] == "opus"
        assert hello["audio_params"]["sample_rate"] == 24000
        assert hello["audio_params"]["channels"] == 1
        assert hello["audio_params"]["frame_duration"] == 60


def test_binary_non_utf8_still_yields_tts_stop() -> None:
    client = TestClient(create_app(NiulaiBrain()))
    with client.websocket_connect("/xiaozhi/v1/") as ws:
        ws.send_json({"type": "hello", "version": 1})
        hello = ws.receive_json()
        assert hello["audio_params"]["format"] == "mock-utf8"

        ws.send_json({"type": "listen", "state": "start"})
        ws.send_bytes(bytes([0xFF, 0xFE, 0x00, 0x01, 0x80, 0x7F, 0xC0]))
        ws.send_json({"type": "listen", "state": "stop"})

        types: list[str] = []
        stt_text = None
        llm_text = None
        tts_stopped = False
        tts_texts: list[str] = []
        for _ in range(16):
            msg = ws.receive_json()
            types.append(msg["type"])
            if msg["type"] == "stt":
                stt_text = msg.get("text")
            if msg["type"] == "llm":
                llm_text = msg.get("text")
            if msg["type"] == "tts" and msg.get("text"):
                tts_texts.append(str(msg["text"]))
            if msg["type"] == "tts" and msg.get("state") == "stop":
                tts_stopped = True
                break

        assert "stt" in types
        assert "llm" in types
        assert "tts" in types
        assert stt_text == ""
        assert llm_text == "我在，你再说一次。"
        assert any("我在" in item for item in tts_texts)
        assert tts_stopped


def test_present_walk_sends_motion_with_ttl_cap() -> None:
    client = TestClient(create_app(NiulaiBrain()))
    with client.websocket_connect("/xiaozhi/v1/") as ws:
        ws.send_json({"type": "hello", "version": 1})
        ws.receive_json()
        ws.send_json({"type": "niulai", "presence": "PRESENT"})
        ws.send_json({"type": "listen", "state": "start"})
        ws.send_bytes("往前走".encode("utf-8"))
        ws.send_json({"type": "listen", "state": "stop"})
        motion = None
        for _ in range(20):
            msg = ws.receive_json()
            if msg["type"] == "niulai" and msg.get("motion"):
                motion = msg
                break
        assert motion is not None
        assert motion["motion"] in {"walk", "turn"}
        assert motion.get("dir") == "forward"
        assert int(motion["ms"]) <= 2000


def test_absent_walk_utterance_sends_niulai_motion() -> None:
    client = TestClient(create_app(NiulaiBrain()))
    with client.websocket_connect("/xiaozhi/v1/") as ws:
        ws.send_json({"type": "hello", "version": 1})
        ws.receive_json()
        ws.send_json({"type": "niulai", "presence": "ABSENT"})
        for _ in range(16):
            msg = ws.receive_json()
            if msg["type"] == "tts" and msg.get("state") == "stop":
                break
        ws.send_json({"type": "listen", "state": "start"})
        ws.send_bytes("往前走".encode("utf-8"))
        ws.send_json({"type": "listen", "state": "stop"})
        motion = None
        for _ in range(20):
            msg = ws.receive_json()
            if msg["type"] == "niulai" and msg.get("motion"):
                motion = msg
                break
        assert motion is not None
        assert motion["motion"] in {"walk", "turn"}
        assert int(motion["ms"]) <= 2000


def test_device_absent_presence_speaks_without_listen() -> None:
    client = TestClient(create_app(NiulaiBrain()))
    with client.websocket_connect("/xiaozhi/v1/") as ws:
        ws.send_json({"type": "hello", "version": 1})
        assert ws.receive_json()["type"] == "hello"
        ws.send_json({"type": "niulai", "presence": "ABSENT"})
        types: list[str] = []
        texts: list[str] = []
        for _ in range(12):
            msg = ws.receive_json()
            types.append(msg["type"])
            if msg.get("text"):
                texts.append(str(msg["text"]))
            if msg["type"] == "tts" and msg.get("state") == "stop":
                break
        assert "tts" in types
        assert any(text.strip() for text in texts)
        assert all("你回来啦" not in text for text in texts)
        ws.send_json({"type": "niulai", "presence": "ABSENT"})
        ws.send_json({"type": "listen", "state": "detect", "text": "牛来"})
        follow = ws.receive_json()
        assert follow.get("type") == "stt"
        assert follow.get("text") == "牛来"
        ws.send_json({"type": "abort"})
        ws.send_json({"type": "niulai", "presence": "PRESENT"})


def test_opus_hello_binary_non_utf8_yields_tts_stop_without_ffmpeg() -> None:
    app = create_app(NiulaiBrain())
    app.state.ffmpeg_path = None
    client = TestClient(app)
    with client.websocket_connect("/xiaozhi/v1/") as ws:
        ws.send_json(
            {
                "type": "hello",
                "version": 1,
                "audio_params": {"format": "opus", "sample_rate": 16000},
            }
        )
        hello = ws.receive_json()
        assert hello["audio_params"]["format"] == "opus"

        ws.send_json({"type": "listen", "state": "start"})
        ws.send_bytes(b"\xff\xfb\x90\x00opus")
        ws.send_json({"type": "listen", "state": "stop"})

        tts_stopped = False
        llm_text = None
        for _ in range(16):
            msg = ws.receive_json()
            if msg["type"] == "llm":
                llm_text = msg.get("text")
            if msg["type"] == "tts" and msg.get("state") == "stop":
                tts_stopped = True
                break
        assert llm_text == "我在，你再说一次。"
        assert tts_stopped


def test_health_returns_ok_version_without_secrets(monkeypatch) -> None:
    monkeypatch.setenv("DASHSCOPE_API_KEY", "sk-leak-dashscope")
    monkeypatch.setenv("API_KEY", "sk-leak-api-key")
    monkeypatch.setenv("NIULAI_TOKEN", "leak-token-value")
    app = create_app(NiulaiBrain())
    client = TestClient(app)
    response = client.get("/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert isinstance(body.get("version"), str) and body["version"]
    assert body["version"] == app.version
    assert set(body) == {"status", "version"}
    raw = response.text
    for leak in ("API_KEY", "DASHSCOPE", "token", "sk-leak", "leak-token", ".env"):
        assert leak.lower() not in raw.lower()


def test_abort_after_absent_drops_late_secret_tts_and_listen_still_replies(
    monkeypatch,
) -> None:
    sent: list[bytes] = []

    async def late_tts(text: str, ffmpeg_path: str) -> bytes:
        try:
            await asyncio.sleep(0.12)
        except asyncio.CancelledError:
            await asyncio.sleep(0.05)
        return f"pcm:{text}".encode("utf-8")

    async def record_opus(send_bytes, pcm, ffmpeg_path, **kwargs) -> int:
        sent.append(pcm)
        return 1

    monkeypatch.setattr("brain.app.main.tts_pcm", late_tts)
    monkeypatch.setattr("brain.app.main.send_opus_pcm", record_opus)
    monkeypatch.setattr(
        "brain.app.secret_life.SecretDirector.next_delay_s", lambda self: 0.02
    )

    app = create_app(NiulaiBrain())
    app.state.ffmpeg_path = "ffmpeg"
    client = TestClient(app)
    with client.websocket_connect("/xiaozhi/v1/") as ws:
        ws.send_json(
            {
                "type": "hello",
                "version": 1,
                "audio_params": {"format": "opus", "sample_rate": 16000},
            }
        )
        assert ws.receive_json()["type"] == "hello"
        ws.send_json({"type": "niulai", "presence": "ABSENT"})
        secret = ""
        for _ in range(16):
            msg = ws.receive_json()
            if msg.get("type") == "llm" and msg.get("text"):
                secret = str(msg["text"])
            if msg.get("type") == "tts" and msg.get("state") == "stop":
                break
        assert secret
        first_sends = len(sent)
        ws.send_json({"type": "abort"})
        ws.send_json({"type": "niulai", "presence": "PRESENT"})
        ws.send_json({"type": "listen", "state": "detect", "text": "你好"})
        polite = False
        leftover_secret_tts = False
        tts_stopped = False
        saw_stt = False
        for _ in range(24):
            msg = ws.receive_json()
            text = str(msg.get("text") or "")
            if msg.get("type") == "stt":
                saw_stt = True
            if saw_stt and msg.get("type") in {"tts", "llm"} and text:
                if secret in text:
                    leftover_secret_tts = True
                if "你好" in text or "我在" in text:
                    polite = True
            if msg.get("type") == "tts" and msg.get("state") == "stop" and polite:
                tts_stopped = True
                break
        assert saw_stt
        assert polite
        assert tts_stopped
        assert leftover_secret_tts is False
        for item in sent[first_sends:]:
            decoded = item.decode("utf-8", errors="replace")
            assert secret not in decoded
            assert "你好" in decoded or "我在" in decoded


def test_failed_tts_does_not_raise_and_next_listen_replies(monkeypatch) -> None:
    async def boom(text: str, ffmpeg_path: str) -> bytes:
        raise RuntimeError("tts down")

    monkeypatch.setattr("brain.app.main.tts_pcm", boom)
    app = create_app(NiulaiBrain())
    app.state.ffmpeg_path = "ffmpeg"
    client = TestClient(app)
    with client.websocket_connect("/xiaozhi/v1/") as ws:
        ws.send_json(
            {
                "type": "hello",
                "version": 1,
                "audio_params": {"format": "opus", "sample_rate": 16000},
            }
        )
        assert ws.receive_json()["type"] == "hello"
        ws.send_json({"type": "listen", "state": "detect", "text": "牛来"})
        first_stop = False
        for _ in range(16):
            msg = ws.receive_json()
            if msg.get("type") == "tts" and msg.get("state") == "stop":
                first_stop = True
                break
        assert first_stop
        ws.send_json({"type": "listen", "state": "detect", "text": "你好"})
        texts: list[str] = []
        second_stop = False
        for _ in range(16):
            msg = ws.receive_json()
            if msg.get("text"):
                texts.append(str(msg["text"]))
            if msg.get("type") == "tts" and msg.get("state") == "stop":
                second_stop = True
                break
        assert second_stop
        assert any("你好" in item or "我在" in item or "牛来" in item for item in texts)


def test_failed_tts_pcm_does_not_raise_from_handler(monkeypatch) -> None:
    async def boom(text: str, ffmpeg_path: str) -> bytes:
        raise RuntimeError("tts down")

    monkeypatch.setattr("brain.app.main.tts_pcm", boom)

    class _DeadSocket:
        async def send_bytes(self, data: bytes) -> None:
            raise AssertionError("failed tts must not send leftover audio")

    asyncio.run(_send_opus_audio(_DeadSocket(), "哼，又没人理我。", "ffmpeg"))


def test_asr_failure_does_not_break_next_listen(monkeypatch) -> None:
    async def boom(packets, ffmpeg_path) -> str | None:
        raise RuntimeError("asr down")

    async def silent_tts(text: str, ffmpeg_path: str) -> bytes:
        return b""

    async def no_opus(*args, **kwargs) -> int:
        return 0

    monkeypatch.setattr("brain.app.main.try_qwen_asr", boom)
    monkeypatch.setattr("brain.app.main.tts_pcm", silent_tts)
    monkeypatch.setattr("brain.app.main.send_opus_pcm", no_opus)
    app = create_app(NiulaiBrain())
    app.state.ffmpeg_path = "ffmpeg"
    client = TestClient(app)
    with client.websocket_connect("/xiaozhi/v1/") as ws:
        ws.send_json(
            {
                "type": "hello",
                "version": 1,
                "audio_params": {"format": "opus", "sample_rate": 16000},
            }
        )
        assert ws.receive_json()["type"] == "hello"
        ws.send_json({"type": "listen", "state": "start"})
        ws.send_bytes(b"\xff\xfb\x90\x00opus")
        ws.send_json({"type": "listen", "state": "stop"})
        first_stop = False
        for _ in range(16):
            msg = ws.receive_json()
            if msg.get("type") == "tts" and msg.get("state") == "stop":
                first_stop = True
                break
        assert first_stop
        ws.send_json({"type": "listen", "state": "detect", "text": "牛来"})
        texts: list[str] = []
        second_stop = False
        for _ in range(16):
            msg = ws.receive_json()
            if msg.get("text"):
                texts.append(str(msg["text"]))
            if msg.get("type") == "tts" and msg.get("state") == "stop":
                second_stop = True
                break
        assert second_stop
        assert any("我在" in item for item in texts)
        assert all("妈妈" not in item for item in texts)
