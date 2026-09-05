from __future__ import annotations

from pathlib import Path

from brain.app.lua_sandbox import LuaSandbox, LuaSandboxError
from brain.app.mcp_broker import McpBroker
from brain.app.models import ActionIntent, ImOutbound
from brain.app.persona import PersonaFSM, PersonaState
from brain.app.providers import MockProviders

FREEZE_CM = 20
WANDER = Path(__file__).resolve().parents[1] / "scripts" / "lua" / "wander.lua"


class NiulaiBrain:
    def __init__(self, autonomy_interval_s: float = 12.0) -> None:
        self.autonomy_interval_s = autonomy_interval_s
        self.persona = PersonaFSM()
        self.lua = LuaSandbox()
        self.mcp = McpBroker()
        self.providers = MockProviders()
        self.im_outbox: list[ImOutbound] = []

    def ingest_distance(self, cm: float) -> list[ActionIntent]:
        if cm < 0 or cm < FREEZE_CM:
            self.persona.set(PersonaState.FREEZE)
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

    def handle_user_text(self, text: str, *, channel: str, chat_id: str) -> ImOutbound:
        if self.persona.state == PersonaState.FREEZE:
            outbound = ImOutbound(
                channel=channel,
                chat_id=chat_id,
                text="……",
                intents=[],
            )
            self.im_outbox.append(outbound)
            return outbound

        reply = self.providers.reply(text)
        intents: list[ActionIntent] = []
        if self.persona.allows_motion() and "走" in text:
            walk = ActionIntent(verb="walk", args={"dir": "forward"}, ttl_ms=800)
            intents.append(walk)
            self.mcp.enqueue(walk)
        outbound = ImOutbound(channel=channel, chat_id=chat_id, text=reply, intents=intents)
        self.im_outbox.append(outbound)
        return outbound
