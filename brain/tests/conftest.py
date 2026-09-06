from __future__ import annotations

import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from brain.app.brain import NiulaiBrain
from brain.app.main import create_app


@pytest.fixture(autouse=True)
def _disable_live_llm(monkeypatch: pytest.MonkeyPatch) -> None:
    for key in (
        "NIULAI_LLM_API_KEY",
        "DEEPSEEK_API_KEY",
        "ZHIPU_API_KEY",
        "DASHSCOPE_API_KEY",
        "QWEN_API_KEY",
        "NIULAI_CLAWBOT_TOKEN",
    ):
        monkeypatch.delenv(key, raising=False)


@pytest.fixture(autouse=True)
def _authenticated_test_clients(monkeypatch: pytest.MonkeyPatch) -> None:
    """Real peer/key defaults for old tests; explicit headers={} tests no credentials."""
    monkeypatch.setenv("NIULAI_DEVICE_TOKEN", "test-device-token")
    monkeypatch.setenv("NIULAI_IM_TOKEN", "test-im-token")
    original_init = TestClient.__init__
    original_request = TestClient.request
    original_ws = TestClient.websocket_connect

    def init(self, *args, **kwargs):
        kwargs.setdefault("client", ("127.0.0.1", 50000))
        kwargs.setdefault("base_url", "http://127.0.0.1")
        original_init(self, *args, **kwargs)

    def request(self, method, url, **kwargs):
        if kwargs.get("headers") is None and "/im/" in str(url):
            kwargs["headers"] = {"Authorization": "Bearer test-im-token"}
        return original_request(self, method, url, **kwargs)

    def websocket_connect(self, url, *args, **kwargs):
        if kwargs.get("headers") is None:
            kwargs["headers"] = {"Authorization": "Bearer test-device-token"}
        return original_ws(self, url, *args, **kwargs)

    monkeypatch.setattr(TestClient, "__init__", init)
    monkeypatch.setattr(TestClient, "request", request)
    monkeypatch.setattr(TestClient, "websocket_connect", websocket_connect)


@pytest.fixture
def brain() -> NiulaiBrain:
    return NiulaiBrain(autonomy_interval_s=0.05)


@pytest.fixture
def app(brain: NiulaiBrain):
    return create_app(brain)
