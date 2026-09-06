from __future__ import annotations

import asyncio
import threading

import httpx
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from brain.app.api import attach_rehearsal_state, router


@pytest.mark.parametrize("change", ["PRESENT", "UNKNOWN", "stop"])
def test_chat_does_not_block_control_or_publish_a_stale_reply(monkeypatch, change):
    async def check():
        entered, release, finished = threading.Event(), threading.Event(), threading.Event()

        def provider(*args, **kwargs):
            entered.set()
            release.wait(2)
            finished.set()
            return "PRIVATE_PROBE", "mock"

        monkeypatch.setattr("brain.app.api.speak", provider)
        app = FastAPI()
        app.include_router(router)
        attach_rehearsal_state(app)
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
            chat = asyncio.create_task(client.post("/api/v1/chat", json={"presence": "ABSENT"}))
            try:
                assert await asyncio.to_thread(entered.wait, 1)
                state = await asyncio.wait_for(client.get("/api/v1/state"), 1)
                assert state.status_code == 200
                assert not finished.is_set(), "chat blocked the shared event loop"
                if change == "stop":
                    response = await client.post("/api/v1/control/stop")
                    assert response.status_code == 202
                else:
                    response = await client.post("/api/v1/rehearsal/events", json={"type": change})
                    assert response.status_code == 200
                release.set()
                result = await asyncio.wait_for(chat, 1)
                assert result.status_code == 409
                assert result.json() == {"error": "stale_chat", "simulated": True}
                state = (await client.get("/api/v1/state")).json()
                assert state["persona"] == "MECHANICAL"
                assert state["connection"] == state["mode"] == "sim"
                assert state["paused"] if change == "stop" else state["presence"] == change
                assert app.state.rehearsal["chat"] == []
                assert "PRIVATE_PROBE" not in str((await client.get("/api/v1/events")).json())
            finally:
                release.set()
                await chat

    asyncio.run(check())


def _client() -> TestClient:
    app = FastAPI()
    app.include_router(router)
    attach_rehearsal_state(app)
    return TestClient(app)


def test_life_page_is_public_html() -> None:
    response = _client().get("/life")
    assert response.status_code == 200
    assert "text/html" in response.headers.get("content-type", "")
    html = response.text
    assert 'lang="zh-CN"' in html
    assert "viewport" in html
    assert "<title>" in html
    assert "牛来" in html


def test_life_page_tells_the_toy_story_without_xiaozhi_cloud() -> None:
    html = _client().get("/life").text
    assert "礼貌" in html
    assert "吐槽" in html
    assert "GPIO 9" in html
    assert "github.com/23xxCh/ox-robot" in html
    assert "不连小智云" in html
    assert "tenclass.net" not in html
    assert "xiaozhi.me" not in html
    assert "/rehearsal" in html or 'href="/"' in html


def test_rehearsal_home_still_exists() -> None:
    response = _client().get("/")
    assert response.status_code == 200
    assert "排练台" in response.text
