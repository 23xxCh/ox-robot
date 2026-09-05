"""Opus helpers for Xiaozhi websocket audio.

StreamingPcmToOpus / OpusPacketPacer follow
E:\\AI TOY\\xiaozhi-claw\\backend\\realtime\\media.py (ffmpeg libopus 24 kHz 60 ms).

ASR of raw Opus is not implemented here: listen.stop with non-UTF-8 binary
falls back in the websocket handler. TTS PCM is Windows SAPI when it works,
otherwise a short beep so the speaker still plays something without API keys.
"""

from __future__ import annotations

import asyncio
import contextlib
import math
import struct
import sys
import tempfile
import time
from collections.abc import Awaitable, Callable
from pathlib import Path

OPUS_SAMPLE_RATE = 24000
OPUS_FRAME_MS = 60


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


async def tts_pcm(text: str, ffmpeg_path: str) -> bytes:
    spoken = await try_sapi_pcm(text, ffmpeg_path)
    if spoken:
        return spoken
    return beep_pcm()


async def send_opus_pcm(
    send_bytes: Callable[[bytes], Awaitable[None]],
    pcm: bytes,
    ffmpeg_path: str,
) -> int:
    """Encode s16le 24 kHz PCM and pace raw Opus packets to the device. Returns frames sent."""
    encoder = StreamingPcmToOpus(ffmpeg_path)
    sent = 0

    async def _send(packet: bytes) -> bool:
        nonlocal sent
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
    except Exception:
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
