from __future__ import annotations

from fastapi.testclient import TestClient

from brain.app.brain import NiulaiBrain
from brain.app.main import create_app
from brain.app.persona import PersonaState


def test_feishu_url_verification_echoes_challenge() -> None:
    client = TestClient(create_app(NiulaiBrain()))
    response = client.post(
        "/im/feishu/event",
        json={"type": "url_verification", "challenge": "n1u-challenge", "token": "x"},
    )
    assert response.status_code == 200
    assert response.json()["challenge"] == "n1u-challenge"


def test_feishu_text_in_secret_alive_replies_and_may_walk() -> None:
    brain = NiulaiBrain()
    brain.persona.set(PersonaState.SECRET_ALIVE)
    client = TestClient(create_app(brain))
    response = client.post(
        "/im/feishu/event",
        json={
            "schema": "2.0",
            "header": {"event_type": "im.message.receive_v1"},
            "event": {
                "message": {
                    "chat_id": "oc_niulai",
                    "message_type": "text",
                    "content": '{"text":"起来走走"}',
                }
            },
        },
    )
    assert response.status_code == 200
    assert brain.im_outbox
    last = brain.im_outbox[-1]
    assert last.channel == "feishu"
    assert last.chat_id == "oc_niulai"
    assert last.text
    assert any(item.verb == "walk" for item in last.intents)


def test_wechat_text_in_secret_alive_replies_and_may_walk() -> None:
    brain = NiulaiBrain()
    brain.persona.set(PersonaState.SECRET_ALIVE)
    client = TestClient(create_app(brain))
    response = client.post(
        "/im/wechat/callback",
        json={
            "ToUserName": "niulai",
            "FromUserName": "wx_user_1",
            "MsgType": "text",
            "Content": "起来走走",
        },
    )
    assert response.status_code == 200
    assert brain.im_outbox
    last = brain.im_outbox[-1]
    assert last.channel == "wechat"
    assert last.chat_id == "wx_user_1"
    assert last.text
    assert any(item.verb == "walk" for item in last.intents)


def test_im_during_freeze_does_not_walk_or_leak_secret_speech() -> None:
    brain = NiulaiBrain()
    brain.persona.set(PersonaState.FREEZE)
    client = TestClient(create_app(brain))
    client.post(
        "/im/feishu/event",
        json={
            "schema": "2.0",
            "header": {"event_type": "im.message.receive_v1"},
            "event": {
                "message": {
                    "chat_id": "oc_niulai",
                    "message_type": "text",
                    "content": '{"text":"起来走走"}',
                }
            },
        },
    )
    assert brain.im_outbox
    last = brain.im_outbox[-1]
    assert last.intents == []
    assert "走走" not in last.text
    assert "吐槽" not in last.text
