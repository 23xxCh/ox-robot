from __future__ import annotations

import asyncio
import struct

import pytest

from brain.app.media import qwen_asr_text, qwen_audio_url, raw_opus_packets_to_ogg, tts_pcm


@pytest.mark.parametrize("sample_rate", [16000, 24000, 48000])
def test_ogg_opus_uses_48khz_timestamps_and_closes_last_audio_page(sample_rate):
    # RFC 7845 section 4: 60 ms is 2880 granules at every input sample rate.
    data = raw_opus_packets_to_ogg([b"first", b"", b"last", b""], sample_rate)
    pages = []
    offset = 0
    while offset < len(data):
        assert data[offset:offset + 4] == b"OggS"
        segments = data[offset + 26]
        length = 27 + segments + sum(data[offset + 27:offset + 27 + segments])
        pages.append((data[offset + 5], struct.unpack_from("<Q", data, offset + 6)[0]))
        offset += length
    assert pages == [(2, 0), (0, 0), (0, 2880), (4, 5760)]


def test_qwen_asr_text_reads_output() -> None:
    assert qwen_asr_text({"output": {"text": "牛来"}}) == "牛来"
    assert qwen_asr_text({"output": {"choices": [{"message": {"content": "你好"}}]}}) == "你好"
    assert qwen_asr_text({}) == ""


def test_qwen_audio_url_reads_output_audio() -> None:
    assert (
        qwen_audio_url({"output": {"audio": {"url": "https://example.com/a.wav"}}})
        == "https://example.com/a.wav"
    )
    assert qwen_audio_url({"output": {}}) is None
    assert qwen_audio_url({}) is None


def test_tts_pcm_prefers_qwen(monkeypatch) -> None:
    async def fake_qwen(text: str, ffmpeg_path: str) -> bytes | None:
        assert "独处" in text
        assert ffmpeg_path == "ffmpeg"
        return b"qwen-pcm"

    async def fake_sapi(text: str, ffmpeg_path: str) -> bytes | None:
        raise AssertionError("SAPI should not run when Qwen TTS works")

    monkeypatch.setattr("brain.app.media.try_qwen_tts_pcm", fake_qwen)
    monkeypatch.setattr("brain.app.media.try_sapi_pcm", fake_sapi)
    assert asyncio.run(tts_pcm("独处碎碎念", "ffmpeg")) == b"qwen-pcm"


def test_tts_pcm_does_not_raise_when_providers_fail(monkeypatch) -> None:
    async def boom_qwen(text: str, ffmpeg_path: str) -> bytes | None:
        raise RuntimeError("qwen down")

    async def boom_sapi(text: str, ffmpeg_path: str) -> bytes | None:
        raise RuntimeError("sapi down")

    monkeypatch.setattr("brain.app.media.try_qwen_tts_pcm", boom_qwen)
    monkeypatch.setattr("brain.app.media.try_sapi_pcm", boom_sapi)
    pcm = asyncio.run(tts_pcm("独处碎碎念", "ffmpeg"))
    assert isinstance(pcm, bytes)
    assert pcm
