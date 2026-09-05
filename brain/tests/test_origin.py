from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient

from brain.app.api import attach_rehearsal_state, router


def _client() -> TestClient:
    app = FastAPI()
    app.include_router(router)
    attach_rehearsal_state(app)
    return TestClient(app)


def test_default_origin_has_niulai_name() -> None:
    body = _client().get("/api/v1/origin").json()
    assert body["origin"]["name"] == "牛来"
    assert "llm" in body


def test_put_origin_then_chat_uses_custom_name() -> None:
    client = _client()
    saved = client.put(
        "/api/v1/origin",
        json={
            "name": "阿黄",
            "backstory": "从杂物柜里逃出来的牛。",
            "alone": "没人时爱翻旧账。",
            "public": "有人时假装乖。",
            "secret": "其实我会记仇。",
        },
    )
    assert saved.status_code == 200
    assert saved.json()["origin"]["name"] == "阿黄"
    talked = client.post(
        "/api/v1/chat",
        json={"text": "你是谁", "presence": "PRESENT"},
    )
    assert talked.status_code == 200
    assert "阿黄" in talked.json()["reply"]
    assert talked.json()["source"] in {"mock", "llm"}


def test_absent_chat_is_not_the_public_greeting() -> None:
    client = _client()
    talked = client.post("/api/v1/chat", json={"text": "", "presence": "ABSENT"})
    assert talked.status_code == 200
    reply = talked.json()["reply"]
    assert reply
    assert "你回来啦" not in reply


def test_life_page_has_origin_fields() -> None:
    html = _client().get("/life").text
    assert 'id="origin-backstory"' in html
    assert 'id="chat-text"' in html
    assert "/web/life.js" in html
