from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient

from brain.app.api import attach_rehearsal_state, router


def _client() -> TestClient:
    app = FastAPI()
    app.include_router(router)
    attach_rehearsal_state(app)
    return TestClient(app)


def test_index_has_skip_link_viewport_and_stop_button() -> None:
    html = _client().get("/").text
    assert 'name="viewport"' in html
    assert 'href="#main"' in html
    assert "跳到主内容" in html
    assert 'id="btn-stop"' in html
    assert 'id="stale-label"' in html


def test_state_reports_stale_when_marked() -> None:
    app = FastAPI()
    app.include_router(router)
    attach_rehearsal_state(app)
    app.state.rehearsal["stale"] = True
    body = TestClient(app).get("/api/v1/state").json()
    assert body["stale"] is True
    assert body["connection"] in {"offline", "sim"}


def test_index_returns_html_containing_sim() -> None:
    response = _client().get("/")
    assert response.status_code == 200
    assert "text/html" in response.headers.get("content-type", "")
    assert "模拟" in response.text
    assert "模拟输入" in response.text
    assert "暂停表演" in response.text
    assert "机械" in response.text
    assert "偷偷活动" in response.text


def test_state_has_mode_sim_and_persona() -> None:
    body = _client().get("/api/v1/state").json()
    assert body["mode"] == "sim"
    assert body["connection"] in {"offline", "sim"}
    assert "persona" in body
    assert body["persona"] in {"MECHANICAL", "SECRET"}
    assert "presence" in body
    assert "safety" in body
    assert "paused" in body
    assert "scene_id" in body
    assert isinstance(body["stale"], bool)


def test_rehearsal_presence_absent_reflected_in_state() -> None:
    client = _client()
    posted = client.post(
        "/api/v1/rehearsal/events",
        json={"type": "presence", "presence": "ABSENT"},
    )
    assert posted.status_code == 200
    assert posted.json()["simulated"] is True
    state = client.get("/api/v1/state").json()
    assert state["presence"] == "ABSENT"
    assert state["mode"] == "sim"
    assert state["persona"] == "SECRET"


def test_stop_twice_returns_two_202_and_idempotent_pause() -> None:
    client = _client()
    first = client.post("/api/v1/control/stop")
    second = client.post("/api/v1/control/stop")
    assert first.status_code == 202
    assert second.status_code == 202
    assert "request_id" in first.json()
    assert "request_id" in second.json()
    assert "physical" not in first.json()
    state = client.get("/api/v1/state").json()
    assert state["paused"] is True
    assert state["persona"] == "MECHANICAL"


def test_delete_memory_empties_items_and_bumps_generation() -> None:
    client = _client()
    before = client.get("/api/v1/memory").json()
    deleted = client.delete("/api/v1/memory")
    assert deleted.status_code == 200
    after = client.get("/api/v1/memory").json()
    assert after["generation"] > before.get("generation", 0)
    assert after.get("items", []) == []


def test_script_tag_in_event_is_stored_as_text() -> None:
    client = _client()
    evil = "<script>alert(1)</script>"
    posted = client.post("/api/v1/rehearsal/events", json={"type": "note", "text": evil})
    assert posted.status_code == 200
    events = client.get("/api/v1/events").json()["events"]
    assert any(item.get("text") == evil for item in events)
    page = client.get("/").text
    assert evil not in page


def test_events_limit_500_is_clamped_to_200() -> None:
    client = _client()
    for index in range(210):
        client.post("/api/v1/rehearsal/events", json={"type": "note", "text": f"e{index}"})
    response = client.get("/api/v1/events?limit=500")
    assert response.status_code == 200
    body = response.json()
    assert body["limit"] == 200
    assert len(body["events"]) <= 200
