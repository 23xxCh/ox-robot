from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from brain.app.brain import NiulaiBrain
from brain.app.main import create_app


@pytest.fixture(autouse=True)
def _disable_live_llm(monkeypatch: pytest.MonkeyPatch) -> None:
    for key in ("NIULAI_LLM_API_KEY", "DEEPSEEK_API_KEY", "ZHIPU_API_KEY"):
        monkeypatch.delenv(key, raising=False)


@pytest.fixture
def brain() -> NiulaiBrain:
    return NiulaiBrain(autonomy_interval_s=0.05)


@pytest.fixture
def app(brain: NiulaiBrain):
    return create_app(brain)
