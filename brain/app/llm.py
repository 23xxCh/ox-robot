from __future__ import annotations

import os
from typing import Any

import httpx

from brain.app.origin import mock_speak, normalize_origin, system_prompt


def llm_enabled() -> bool:
    return bool(_providers())


def _providers() -> list[tuple[str, str, str]]:
    specs: list[tuple[str, str, str]] = []
    if os.environ.get("NIULAI_LLM_API_KEY"):
        specs.append(
            (
                os.environ["NIULAI_LLM_API_KEY"].strip(),
                (os.environ.get("NIULAI_LLM_BASE_URL") or "https://api.deepseek.com").rstrip("/"),
                os.environ.get("NIULAI_LLM_MODEL") or "deepseek-chat",
            )
        )
    zhipu = (os.environ.get("ZHIPU_API_KEY") or "").strip()
    if zhipu:
        specs.append(
            (zhipu, "https://open.bigmodel.cn/api/paas/v4", os.environ.get("NIULAI_LLM_MODEL") or "glm-4-flash")
        )
    deepseek = (os.environ.get("DEEPSEEK_API_KEY") or "").strip()
    if deepseek:
        specs.append((deepseek, "https://api.deepseek.com", "deepseek-chat"))
    return [(key, base, model) for key, base, model in specs if key]


def speak(origin: dict[str, str], presence: str, user_text: str) -> tuple[str, str]:
    origin = normalize_origin(origin)
    if not llm_enabled():
        return mock_speak(origin, presence, user_text), "mock"
    prompt = system_prompt(origin, presence)
    user = user_text.strip() if user_text.strip() else "（没有人说话，你自己来一句。）"
    try:
        text = _complete(prompt, user)
    except Exception:
        return mock_speak(origin, presence, user_text), "mock"
    if not text:
        return mock_speak(origin, presence, user_text), "mock"
    return text, "llm"


def _complete(system: str, user: str) -> str:
    last_error: Exception | None = None
    payload: dict[str, Any] = {
        "temperature": 0.9,
        "max_tokens": 120,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
    }
    for key, base, model in _providers():
        body = dict(payload)
        body["model"] = model
        try:
            with httpx.Client(timeout=12.0) as client:
                response = client.post(
                    base + "/chat/completions",
                    json=body,
                    headers={
                        "Authorization": f"Bearer {key}",
                        "Content-Type": "application/json",
                    },
                )
                response.raise_for_status()
                data = response.json()
            choices = data.get("choices") or []
            if not choices:
                continue
            message = choices[0].get("message") or {}
            text = str(message.get("content") or "").strip()
            if text:
                return text
        except Exception as exc:  # noqa: BLE001 — try next provider
            last_error = exc
            continue
    if last_error:
        raise last_error
    return ""
