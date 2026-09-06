from __future__ import annotations

import asyncio
import json

from brain.app.brain import NiulaiBrain
from brain.app.main import create_app
from brain.app.persona import PersonaState


def test_hello_waits_for_explicit_absent_even_when_shared_brain_is_secret(monkeypatch) -> None:
    import brain.app.main as main

    async def check():
        brain = NiulaiBrain()
        brain.persona.set(PersonaState.SECRET_ALIVE)
        before_presence = brain.lifecycle.presence
        app = create_app(brain)
        incoming, outgoing = asyncio.Queue(), asyncio.Queue()
        compositions = []

        async def compose(brain, device_id, presence, origin, user_text, still_current):
            compositions.append(presence)
            return "终于清静了。", []

        monkeypatch.setattr(main, "_compose_line_async", compose)

        class Socket:
            headers = {"authorization": "Bearer test-device-token"}

            def __init__(self):
                self.app = app

            async def accept(self):
                pass

            async def receive(self):
                return await incoming.get()

            async def send_json(self, frame):
                await outgoing.put(frame)

        def send(frame):
            incoming.put_nowait({"type": "websocket.receive", "text": json.dumps(frame)})

        endpoint = next(route.endpoint for route in app.routes if getattr(route, "path", None) == "/xiaozhi/v1/")
        task = asyncio.create_task(endpoint(Socket()))
        try:
            send({"type": "hello", "version": 1})
            assert (await asyncio.wait_for(outgoing.get(), 1))["type"] == "hello"
            # The invalid-frame reply is a receive-loop barrier, without a timed sleep.
            send([])
            before_absent = []
            while True:
                frame = await asyncio.wait_for(outgoing.get(), 1)
                if frame.get("type") == "system":
                    break
                before_absent.append(frame)
            assert before_absent == []
            assert compositions == []
            assert brain.lifecycle.presence == before_presence

            send({"type": "niulai", "presence": "ABSENT"})
            texts = []
            while True:
                frame = await asyncio.wait_for(outgoing.get(), 1)
                if frame.get("type") == "tts" and frame.get("text"):
                    texts.append(frame["text"])
                if frame.get("type") == "tts" and frame.get("state") == "stop":
                    break
            assert texts == ["终于清静了。"]
            assert compositions == ["ABSENT"]
        finally:
            incoming.put_nowait({"type": "websocket.disconnect"})
            await asyncio.wait_for(task, 1)

    asyncio.run(check())
