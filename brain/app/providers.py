from __future__ import annotations


class MockProviders:
    """Deterministic ASR/LLM/TTS stand-ins. No network."""

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
            return "嗯，我在。"
        return "哼，又没人理我。"
