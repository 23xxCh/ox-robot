"""Opus helpers for Xiaozhi websocket audio.

StreamingPcmToOpus / OpusPacketPacer follow
E:\\AI TOY\\xiaozhi-claw\\backend\\realtime\\media.py (ffmpeg libopus 24 kHz 60 ms).

Device mic is raw Opus frames (16 kHz 60 ms). ASR muxes them to Ogg Opus,
decodes to WAV, then calls DashScope qwen3-asr-flash. TTS prefers
qwen3-tts-flash (Dylan), then Windows SAPI, then a short beep.
"""

from __future__ import annotations

import asyncio
import contextlib
import logging
import math
import os
import struct
import sys
import tempfile
import time
from collections.abc import Awaitable, Callable
from pathlib import Path
from typing import Any

import httpx

OPUS_SAMPLE_RATE = 24000
MIC_SAMPLE_RATE = 16000
OPUS_FRAME_MS = 60
QWEN_TTS_URL = "https://dashscope.aliyuncs.com/api/v1/services/aigc/multimodal-generation/generation"
QWEN_TTS_MODEL = "qwen3-tts-flash"
QWEN_TTS_VOICE = "Dylan"
QWEN_ASR_MODEL = "qwen3-asr-flash"
logger = logging.getLogger(__name__)


class OpusPacketPacer:
    """Send Opus frames at playback rate without catch-up bursts."""

    def __init__(
        self,
        send: Callable[[bytes], Awaitable[bool]],
        *,
        frame_duration_ms: int = OPUS_FRAME_MS,
        clock: Callable[[], float] = time.monotonic,
        sleep: Callable[[float], Awaitable[None]] = asyncio.sleep,
    ) -> None:
        self._send = send
        self._frame_seconds = frame_duration_ms / 1000
        self._clock = clock
        self._sleep = sleep
        self._next_send_at: float | None = None

    async def send(self, packet: bytes) -> bool:
        now = self._clock()
        target = self._next_send_at if self._next_send_at is not None else now
        if now < target:
            await self._sleep(target - now)
        elif now > target:
            target = now
        delivered = await self._send(packet)
        self._next_send_at = target + self._frame_seconds
        return delivered


class StreamingPcmToOpus:
    """One FFmpeg encoder per reply, preserving 60 ms Opus packet boundaries."""

    def __init__(self, ffmpeg_path: str) -> None:
        self.ffmpeg_path = ffmpeg_path
        self.process: asyncio.subprocess.Process | None = None
        self._reader_task: asyncio.Task[None] | None = None
        self._packets: asyncio.Queue[bytes | None] = asyncio.Queue(maxsize=100)
        self._buffer = bytearray()
        self._pending_packet = bytearray()

    async def start(self) -> None:
        self.process = await asyncio.create_subprocess_exec(
            self.ffmpeg_path,
            "-hide_banner",
            "-loglevel",
            "error",
            "-f",
            "s16le",
            "-ar",
            str(OPUS_SAMPLE_RATE),
            "-ac",
            "1",
            "-i",
            "pipe:0",
            "-vn",
            "-c:a",
            "libopus",
            "-b:a",
            "24k",
            "-frame_duration",
            str(OPUS_FRAME_MS),
            "-flush_packets",
            "1",
            "-page_duration",
            "60000",
            "-f",
            "ogg",
            "pipe:1",
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        self._reader_task = asyncio.create_task(self._read_output())

    async def write(self, pcm: bytes) -> None:
        if self.process is None or self.process.stdin is None:
            raise RuntimeError("encoder is not running")
        self.process.stdin.write(pcm)
        await self.process.stdin.drain()

    async def _read_output(self) -> None:
        assert self.process is not None and self.process.stdout is not None
        while chunk := await self.process.stdout.read(4096):
            self._buffer.extend(chunk)
            await self._extract_pages()
        await self._packets.put(None)

    async def _extract_pages(self) -> None:
        while len(self._buffer) >= 27:
            if self._buffer[:4] != b"OggS":
                raise RuntimeError("FFmpeg returned an invalid Ogg stream")
            segment_count = self._buffer[26]
            if len(self._buffer) < 27 + segment_count:
                return
            lacing = self._buffer[27 : 27 + segment_count]
            page_size = 27 + segment_count + sum(lacing)
            if len(self._buffer) < page_size:
                return
            payload_offset = 27 + segment_count
            for segment_size in lacing:
                self._pending_packet.extend(
                    self._buffer[payload_offset : payload_offset + segment_size]
                )
                payload_offset += segment_size
                if segment_size < 255:
                    packet = bytes(self._pending_packet)
                    self._pending_packet.clear()
                    if not packet.startswith((b"OpusHead", b"OpusTags")):
                        await self._packets.put(packet)
            del self._buffer[:page_size]

    async def packets(self, *, prebuffer_packets: int = 0):
        buffered: list[bytes] = []
        while len(buffered) < prebuffer_packets:
            packet = await self._packets.get()
            if packet is None:
                for buffered_packet in buffered:
                    yield buffered_packet
                return
            buffered.append(packet)
        for buffered_packet in buffered:
            yield buffered_packet
        while True:
            packet = await self._packets.get()
            if packet is None:
                return
            yield packet

    async def finish(self) -> None:
        if self.process is None:
            return
        if self.process.stdin is not None:
            self.process.stdin.close()
            await self.process.stdin.wait_closed()
        return_code = await self.process.wait()
        if self._reader_task is not None:
            await self._reader_task
        if return_code != 0:
            error = b""
            if self.process.stderr is not None:
                error = await self.process.stderr.read()
            raise RuntimeError(
                f"FFmpeg streaming encoder failed: {error.decode(errors='replace').strip()}"
            )

    async def cancel(self) -> None:
        if self.process is not None and self.process.returncode is None:
            self.process.terminate()
            with contextlib.suppress(ProcessLookupError):
                await self.process.wait()
        if self._reader_task is not None:
            self._reader_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._reader_task


def beep_pcm(*, duration_s: float = 0.36, freq: float = 440.0) -> bytes:
    """Short enveloped tone used when no local TTS voice is available."""
    n = max(1, int(duration_s * OPUS_SAMPLE_RATE))
    attack = max(1, int(0.02 * OPUS_SAMPLE_RATE))
    release = max(1, int(0.05 * OPUS_SAMPLE_RATE))
    out = bytearray()
    for index in range(n):
        env = 1.0
        if index < attack:
            env = index / attack
        remaining = n - index
        if remaining < release:
            env = remaining / release
        sample = int(9000 * env * math.sin(2 * math.pi * freq * index / OPUS_SAMPLE_RATE))
        out.extend(struct.pack("<h", max(-32767, min(32767, sample))))
    return bytes(out)


def pcm_s16le_to_wav(pcm: bytes, sample_rate: int = MIC_SAMPLE_RATE) -> bytes:
    return (
        struct.pack(
            "<4sI4s4sIHHIIHH4sI",
            b"RIFF",
            36 + len(pcm),
            b"WAVE",
            b"fmt ",
            16,
            1,
            1,
            sample_rate,
            sample_rate * 2,
            2,
            16,
            b"data",
            len(pcm),
        )
        + pcm
    )


def _ogg_crc(data: bytes) -> int:
    crc = 0
    for byte in data:
        crc ^= byte << 24
        for _ in range(8):
            if crc & 0x80000000:
                crc = ((crc << 1) ^ 0x04C11DB7) & 0xFFFFFFFF
            else:
                crc = (crc << 1) & 0xFFFFFFFF
    return crc


def _ogg_page(header_type: int, granule: int, seq: int, body: bytes, *, serial: int = 1) -> bytes:
    lacing = bytearray()
    remaining = len(body)
    offset = 0
    chunks: list[bytes] = []
    while remaining >= 255:
        lacing.append(255)
        chunks.append(body[offset : offset + 255])
        offset += 255
        remaining -= 255
    lacing.append(remaining)
    chunks.append(body[offset:])
    header = bytearray()
    header.extend(b"OggS")
    header.append(0)
    header.append(header_type)
    header.extend(struct.pack("<Q", granule))
    header.extend(struct.pack("<I", serial))
    header.extend(struct.pack("<I", seq))
    header.extend(b"\x00\x00\x00\x00")
    header.append(len(lacing))
    header.extend(lacing)
    page = bytes(header) + b"".join(chunks)
    crc = _ogg_crc(page)
    return page[:22] + struct.pack("<I", crc) + page[26:]


def raw_opus_packets_to_ogg(packets: list[bytes], sample_rate: int = MIC_SAMPLE_RATE) -> bytes:
    packets = [packet for packet in packets if packet]
    head = struct.pack("<8sBBHIhB", b"OpusHead", 1, 1, 312, sample_rate, 0, 0)
    tags = b"OpusTags" + struct.pack("<I", 6) + b"niulai" + struct.pack("<I", 0)
    pages = [
        _ogg_page(0x02, 0, 0, head),
        _ogg_page(0x00, 0, 1, tags),
    ]
    granule = 0
    seq = 2
    # RFC 7845 section 4: granules always count 48 kHz samples, even for a 16 kHz mic.
    samples_per_packet = 48000 * OPUS_FRAME_MS // 1000
    for index, packet in enumerate(packets):
        granule += samples_per_packet
        header_type = 0x04 if index == len(packets) - 1 else 0x00
        pages.append(_ogg_page(header_type, granule, seq, packet))
        seq += 1
    return b"".join(pages)


async def ogg_opus_to_wav(ogg: bytes, ffmpeg_path: str, sample_rate: int = MIC_SAMPLE_RATE) -> bytes:
    process = await asyncio.create_subprocess_exec(
        ffmpeg_path,
        "-hide_banner",
        "-loglevel",
        "error",
        "-i",
        "pipe:0",
        "-f",
        "wav",
        "-ac",
        "1",
        "-ar",
        str(sample_rate),
        "pipe:1",
        stdin=asyncio.subprocess.PIPE,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    wav, error = await process.communicate(ogg)
    if process.returncode != 0 or not wav:
        detail = error.decode("utf-8", errors="replace").strip()
        raise RuntimeError(f"FFmpeg could not decode mic opus: {detail}")
    return wav


def qwen_asr_text(data: dict[str, Any]) -> str:
    output = data.get("output") if isinstance(data, dict) else None
    if isinstance(output, dict):
        text = str(output.get("text") or "").strip()
        if text:
            return text
        choices = output.get("choices") or []
        if choices:
            message = choices[0].get("message") or {}
            content = message.get("content")
            if isinstance(content, str) and content.strip():
                return content.strip()
            if isinstance(content, list):
                parts: list[str] = []
                for item in content:
                    if isinstance(item, dict):
                        parts.append(str(item.get("text") or ""))
                    else:
                        parts.append(str(item))
                joined = "".join(parts).strip()
                if joined:
                    return joined
    return ""


async def try_qwen_asr(packets: list[bytes], ffmpeg_path: str) -> str | None:
    if not packets:
        return None
    from brain.app.llm import _load_env_files

    _load_env_files()
    key = (os.environ.get("DASHSCOPE_API_KEY") or os.environ.get("QWEN_API_KEY") or "").strip()
    if not key:
        return None
    try:
        ogg = raw_opus_packets_to_ogg(packets)
        wav = await ogg_opus_to_wav(ogg, ffmpeg_path)
    except Exception:
        logger.exception("mic opus decode failed")
        return None
    import base64

    encoded = base64.b64encode(wav).decode("ascii")
    payload = {
        "model": os.environ.get("DASHSCOPE_ASR_MODEL") or QWEN_ASR_MODEL,
        "input": {
            "messages": [
                {
                    "role": "user",
                    "content": [{"audio": f"data:audio/wav;base64,{encoded}"}],
                }
            ]
        },
    }
    url = os.environ.get("DASHSCOPE_TTS_URL") or QWEN_TTS_URL
    try:
        async with httpx.AsyncClient(timeout=20.0) as client:
            response = await client.post(
                url,
                json=payload,
                headers={
                    "Authorization": f"Bearer {key}",
                    "Content-Type": "application/json",
                },
            )
            if response.status_code != 200:
                logger.warning("qwen asr http %s", response.status_code)
                return None
            text = qwen_asr_text(response.json())
            return text or None
    except Exception:
        logger.exception("qwen asr failed")
        return None


async def wav_to_pcm(wav: bytes, ffmpeg_path: str) -> bytes:
    process = await asyncio.create_subprocess_exec(
        ffmpeg_path,
        "-hide_banner",
        "-loglevel",
        "error",
        "-i",
        "pipe:0",
        "-f",
        "s16le",
        "-ac",
        "1",
        "-ar",
        str(OPUS_SAMPLE_RATE),
        "pipe:1",
        stdin=asyncio.subprocess.PIPE,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    pcm, error = await process.communicate(wav)
    if process.returncode != 0 or not pcm:
        detail = error.decode("utf-8", errors="replace").strip()
        raise RuntimeError(f"FFmpeg could not decode TTS wav: {detail}")
    return pcm


async def try_sapi_pcm(text: str, ffmpeg_path: str) -> bytes | None:
    if sys.platform != "win32" or not text.strip():
        return None
    with tempfile.TemporaryDirectory() as tmp:
        folder = Path(tmp)
        txt_path = folder / "tts.txt"
        wav_path = folder / "tts.wav"
        txt_path.write_text(text, encoding="utf-8")
        txt = str(txt_path).replace("'", "''")
        wav = str(wav_path).replace("'", "''")
        script = (
            "Add-Type -AssemblyName System.Speech; "
            "$s = New-Object System.Speech.Synthesis.SpeechSynthesizer; "
            f"$s.SetOutputToWaveFile('{wav}'); "
            f"$s.Speak([IO.File]::ReadAllText('{txt}', [Text.Encoding]::UTF8)); "
            "$s.Dispose();"
        )
        process = await asyncio.create_subprocess_exec(
            "powershell",
            "-NoProfile",
            "-NonInteractive",
            "-ExecutionPolicy",
            "Bypass",
            "-Command",
            script,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        try:
            await asyncio.wait_for(process.wait(), timeout=8)
        except TimeoutError:
            process.kill()
            with contextlib.suppress(ProcessLookupError):
                await process.wait()
            return None
        if process.returncode != 0 or not wav_path.exists() or wav_path.stat().st_size < 64:
            return None
        try:
            return await wav_to_pcm(wav_path.read_bytes(), ffmpeg_path)
        except RuntimeError:
            return None


def qwen_audio_url(data: dict[str, Any]) -> str | None:
    output = data.get("output") if isinstance(data, dict) else None
    if not isinstance(output, dict):
        return None
    audio = output.get("audio")
    if isinstance(audio, dict):
        url = str(audio.get("url") or "").strip()
        if url.startswith("http"):
            return url
    url = str(output.get("audio_url") or "").strip()
    if url.startswith("http"):
        return url
    return None


async def try_qwen_tts_pcm(text: str, ffmpeg_path: str) -> bytes | None:
    spoken = text.strip()
    if not spoken:
        return None
    from brain.app.llm import _load_env_files

    _load_env_files()
    key = (os.environ.get("DASHSCOPE_API_KEY") or os.environ.get("QWEN_API_KEY") or "").strip()
    if not key:
        return None
    payload = {
        "model": os.environ.get("DASHSCOPE_TTS_MODEL") or QWEN_TTS_MODEL,
        "input": {
            "text": spoken[:200],
            "voice": os.environ.get("DASHSCOPE_TTS_VOICE") or QWEN_TTS_VOICE,
            "language_type": "Chinese",
        },
    }
    url = os.environ.get("DASHSCOPE_TTS_URL") or QWEN_TTS_URL
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.post(
                url,
                json=payload,
                headers={
                    "Authorization": f"Bearer {key}",
                    "Content-Type": "application/json",
                },
            )
            if response.status_code != 200:
                logger.warning("qwen tts http %s", response.status_code)
                return None
            audio_url = qwen_audio_url(response.json())
            if not audio_url:
                logger.warning("qwen tts missing audio url")
                return None
            audio = await client.get(audio_url)
            audio.raise_for_status()
            if not audio.content:
                return None
            return await wav_to_pcm(audio.content, ffmpeg_path)
    except Exception:
        logger.exception("qwen tts failed")
        return None


async def tts_pcm(text: str, ffmpeg_path: str) -> bytes:
    spoken: bytes | None = None
    try:
        spoken = await try_qwen_tts_pcm(text, ffmpeg_path)
    except Exception:
        logger.exception("qwen tts raised")
    if spoken:
        return spoken
    try:
        spoken = await try_sapi_pcm(text, ffmpeg_path)
    except Exception:
        logger.exception("sapi tts raised")
    if spoken:
        return spoken
    return beep_pcm()


async def send_opus_pcm(
    send_bytes: Callable[[bytes], Awaitable[None]],
    pcm: bytes,
    ffmpeg_path: str,
    *,
    alive: Callable[[], bool] | None = None,
) -> int:
    """Encode s16le 24 kHz PCM and pace raw Opus packets to the device. Returns frames sent."""
    encoder = StreamingPcmToOpus(ffmpeg_path)
    sent = 0

    async def _send(packet: bytes) -> bool:
        nonlocal sent
        if alive is not None and not alive():
            return False
        await send_bytes(packet)
        sent += 1
        return True

    pacer = OpusPacketPacer(_send, frame_duration_ms=OPUS_FRAME_MS)
    await encoder.start()
    pump = asyncio.create_task(_pump_packets(encoder, pacer))
    try:
        if pcm:
            await encoder.write(pcm)
        await encoder.finish()
        await pump
    except (Exception, asyncio.CancelledError):
        await encoder.cancel()
        pump.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await pump
        raise
    return sent


async def _pump_packets(encoder: StreamingPcmToOpus, pacer: OpusPacketPacer) -> None:
    async for packet in encoder.packets(prebuffer_packets=2):
        if not await pacer.send(packet):
            return
