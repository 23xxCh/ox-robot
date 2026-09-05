from __future__ import annotations

# Canned public reply when Opus (or any non-UTF-8) audio cannot be transcribed.
HEARD_FALLBACK = "嗯，我在。"


def looks_like_utf8(audio: bytes) -> bool:
    if not audio:
        return True
    try:
        audio.decode("utf-8")
    except UnicodeDecodeError:
        return False
    return True


class MockProviders:
    """Deterministic ASR/LLM/TTS stand-ins. No network."""

    heard_fallback = HEARD_FALLBACK

    def transcribe(self, audio: bytes) -> str:
        if not audio:
            return ""
        try:
            return audio.decode("utf-8")
        except UnicodeDecodeError:
            return ""

    def reply(self, transcript: str) -> str:
        text = transcript.strip()
        if "走" in text:
            return "行，我挪两步。"
        if text:
            return HEARD_FALLBACK
        return "哼，又没人理我。"
