from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient

from brain.app.api import attach_rehearsal_state, router


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
