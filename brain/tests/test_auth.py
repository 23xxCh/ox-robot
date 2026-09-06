from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

from brain.app.brain import NiulaiBrain
from brain.app.main import create_app

DEVICE_TOKEN = "test-device-token"
IM_TOKEN = "test-im-token"


def client(peer="192.168.18.200", host="127.0.0.1"):
    return TestClient(create_app(NiulaiBrain()), base_url=f"http://{host}", client=(peer, 12345))


@pytest.mark.parametrize("method,path", [
    ("GET", "/"), ("GET", "/life"), ("GET", "/docs"),
    ("GET", "/api/v1/state"), ("GET", "/api/v1/events"), ("GET", "/api/v1/memory"),
    ("POST", "/api/v1/chat"), ("POST", "/api/v1/control/stop"),
    ("POST", "/api/v1/rehearsal/events"), ("DELETE", "/api/v1/memory"),
    ("PUT", "/api/v1/origin"),
])
def test_remote_ui_is_denied_even_with_device_key_or_forwarded_loopback(monkeypatch, method, path):
    monkeypatch.setenv("NIULAI_DEVICE_TOKEN", DEVICE_TOKEN)
    response = client().request(method, path, json={}, headers={
        "Authorization": f"Bearer {DEVICE_TOKEN}",
        "X-Forwarded-For": "127.0.0.1", "X-Real-IP": "127.0.0.1",
    })
    assert response.status_code == 403


@pytest.mark.parametrize("origin", [None, "http://127.0.0.1"])
def test_local_chat_remains_usable_without_credentials(origin):
    headers = {} if origin is None else {"Origin": origin}
    response = client("127.0.0.1").post("/api/v1/chat", json={"text": "你好"}, headers=headers)
    assert response.status_code == 200
    assert response.json()["reply"]


@pytest.mark.parametrize("origin", ["https://evil.example", "null", "http://127.0.0.1:9999"])
def test_local_ui_rejects_cross_origin_mutation(origin):
    response = client("127.0.0.1").post("/api/v1/control/stop", headers={"Origin": origin})
    assert response.status_code == 403


def test_local_ui_rejects_a_non_loopback_host_without_origin():
    assert client("127.0.0.1", "rebound.example").get("/api/v1/memory", headers={}).status_code == 403


@pytest.mark.parametrize("path,payload", [
    ("/im/feishu/event", {"type": "url_verification", "challenge": "probe"}),
    ("/im/wechat/callback", {"MsgType": "text", "FromUserName": "probe", "Content": "你好"}),
    ("/im/clawbot/event", {"from": "probe", "text": "你好"}),
])
def test_im_requires_its_own_real_token_before_processing(monkeypatch, path, payload):
    monkeypatch.setenv("NIULAI_DEVICE_TOKEN", DEVICE_TOKEN)
    monkeypatch.setenv("NIULAI_IM_TOKEN", IM_TOKEN)
    monkeypatch.setattr("brain.app.im.clawbot_configured", lambda: False)
    app_client = client()
    for headers in ({}, {"token": "anything"}, {"Authorization": "Bearer wrong"},
                    {"Authorization": f"Bearer {DEVICE_TOKEN}"}):
        response = app_client.post(path, json=payload, headers=headers)
        assert response.status_code == 401
        assert app_client.app.state.brain.im_outbox == []
    assert app_client.post(path, json=payload, headers={"Authorization": f"Bearer {IM_TOKEN}"}).status_code == 200


@pytest.mark.parametrize("headers", [{}, {"Authorization": "Bearer wrong"}, {"Authorization": f"Bearer {IM_TOKEN}"}])
def test_ws_rejects_unauthorized_upgrade_even_on_loopback(monkeypatch, headers):
    monkeypatch.setenv("NIULAI_DEVICE_TOKEN", DEVICE_TOKEN)
    app_client = client("127.0.0.1")
    with pytest.raises(WebSocketDisconnect) as denied:
        with app_client.websocket_connect(f"/xiaozhi/v1/?token={DEVICE_TOKEN}", headers=headers):
            pytest.fail("unauthorized WebSocket was accepted")
    assert denied.value.code == 1008


def test_ws_accepts_device_bearer_from_lan(monkeypatch):
    monkeypatch.setenv("NIULAI_DEVICE_TOKEN", DEVICE_TOKEN)
    with client().websocket_connect("/xiaozhi/v1/", headers={"Authorization": f"Bearer {DEVICE_TOKEN}"}) as ws:
        ws.send_json({"type": "hello"})
        assert ws.receive_json()["type"] == "hello"


def test_missing_config_fails_closed_and_health_stays_read_only(monkeypatch):
    monkeypatch.delenv("NIULAI_DEVICE_TOKEN", raising=False)
    monkeypatch.delenv("NIULAI_IM_TOKEN", raising=False)
    app_client = client()
    with pytest.raises(WebSocketDisconnect):
        with app_client.websocket_connect("/xiaozhi/v1/", headers={"Authorization": f"Bearer {DEVICE_TOKEN}"}):
            pytest.fail("unconfigured WebSocket auth was accepted")
    assert app_client.post("/im/feishu/event", json={"type": "url_verification"}, headers={"Authorization": f"Bearer {IM_TOKEN}"}).status_code == 401
    health = app_client.get("/health", headers={})
    assert health.status_code == 200
    assert DEVICE_TOKEN not in health.text and IM_TOKEN not in health.text
