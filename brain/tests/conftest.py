from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from brain.app.brain import NiulaiBrain
from brain.app.main import create_app


@pytest.fixture
def brain() -> NiulaiBrain:
    return NiulaiBrain(autonomy_interval_s=0.05)


@pytest.fixture
def app(brain: NiulaiBrain):
    return create_app(brain)
