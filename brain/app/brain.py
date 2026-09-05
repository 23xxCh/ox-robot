from __future__ import annotations

from pathlib import Path

from brain.app.lifecycle import Lifecycle, Presence
from brain.app.lua_sandbox import LuaSandbox, LuaSandboxError
from brain.app.mcp_broker import McpBroker
from brain.app.memory import MemoryStore
from brain.app.models import ActionIntent, ImOutbound
from brain.app.persona import PersonaState
from brain.app.providers import MockProviders

FREEZE_CM = 20
WANDER = Path(__file__).resolve().parents[1] / "scripts" / "lua" / "wander.lua"


class NiulaiBrain:
    def __init__(
        self,
        autonomy_interval_s: float = 12.0,
        memory_path: str | Path | None = None,
    ) -> None:
        self.autonomy_interval_s = autonomy_interval_s
        self.lifecycle = Lifecycle(autonomy_interval_ms=int(autonomy_interval_s * 1000))
        self.persona = self.lifecycle.persona
        self.lua = LuaSandbox()
        self.mcp = McpBroker()
        self.providers = MockProviders()
        self.im_outbox: list[ImOutbound] = []
        self.memory = MemoryStore(memory_path if memory_path is not None else ":memory:")

    def ingest_distance(self, cm: float) -> list[ActionIntent]:
        self.lifecycle.ingest_proximity(cm, now_ms=0, timeout=cm < 0)
        if cm < 0 or cm < FREEZE_CM:
            self.lifecycle.set_presence(Presence.UNKNOWN, source="proximity", now_ms=0)
            self.mcp.drop_motion()
            snore = ActionIntent(verb="snore", args={"on": True}, ttl_ms=0)
            return [snore]
        return []

    def autonomy_intents(self) -> list[ActionIntent]:
        if self.persona.state != PersonaState.SECRET_ALIVE:
            return []
        try:
            return self.lua.run_file(WANDER)
        except (LuaSandboxError, OSError):
            return [ActionIntent(verb="say", args={"text": "哼，又没人理我"})]

    def handle_utterance(self, text: str, *, now_ms: int = 0):
        return self.lifecycle.handle_utterance(text, now_ms=now_ms)

    def handle_user_text(self, text: str, *, channel: str, chat_id: str) -> ImOutbound:
        spoken = self.lifecycle.handle_utterance(text, now_ms=0)
        if self.persona.state == PersonaState.FREEZE:
            outbound = ImOutbound(
                channel=channel,
                chat_id=chat_id,
                text=spoken.text or "……",
                intents=[],
            )
            self.im_outbox.append(outbound)
            return outbound

        reply = spoken.text or self.providers.reply(text)
        intents: list[ActionIntent] = list(spoken.intents)
        if self.persona.allows_secret_speech() and "走" in text:
            walk = ActionIntent(verb="walk", args={"dir": "forward"}, ttl_ms=800)
            intents.append(walk)
            self.mcp.enqueue(walk)
        outbound = ImOutbound(channel=channel, chat_id=chat_id, text=reply, intents=intents)
        self.im_outbox.append(outbound)
        return outbound
