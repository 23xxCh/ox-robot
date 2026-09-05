from __future__ import annotations

from enum import Enum


class PersonaState(str, Enum):
    FREEZE = "FREEZE"
    MECHANICAL = "FREEZE"
    PUBLIC_ALIVE = "PUBLIC_ALIVE"
    SECRET_ALIVE = "SECRET_ALIVE"
    SECRET = "SECRET_ALIVE"


class PersonaFSM:
    def __init__(self, state: PersonaState = PersonaState.FREEZE) -> None:
        self.state = state

    def set(self, state: PersonaState) -> None:
        self.state = state

    def allows_secret_speech(self) -> bool:
        return self.state == PersonaState.SECRET_ALIVE

    def allows_motion(self) -> bool:
        return self.state in {PersonaState.SECRET_ALIVE, PersonaState.PUBLIC_ALIVE}
