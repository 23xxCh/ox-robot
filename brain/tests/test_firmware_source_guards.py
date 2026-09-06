from __future__ import annotations

import os
from pathlib import Path
import shutil
import subprocess

import pytest

ROOT = Path(__file__).resolve().parents[2]
LIFE = ROOT / "firmware" / "xiaozhi-niulai" / "niulai_life.cc"
FACE = ROOT / "firmware" / "xiaozhi-niulai" / "niulai_face_display.cc"


def test_overlay_close_parks_and_unknown_blocks_new_walk() -> None:
    text = LIFE.read_text(encoding="utf-8")
    assert "if (close || next == Presence::Unknown) {" in text
    assert "ParkLegs();" in text
    assert "last_close_" in text
    assert "presence_ == Presence::Unknown || last_close_" in text
    assert "ms > 2000" in text

    transition = text.split("void NiulaiLife::OnPresence(", 1)[1]
    assert "if (next != Presence::Absent) {" in transition
    assert "NiulaiEnterPresent();" in transition
    queued_secret = text.split("void NiulaiLife::AskBrainSecret()", 1)[1]
    assert "Schedule([this]() {" in queued_secret
    assert "if (presence_ == Presence::Absent) {" in queued_secret


def test_overlay_secret_faces_only_when_absent() -> None:
    life = LIFE.read_text(encoding="utf-8")
    face = FACE.read_text(encoding="utf-8")
    assert "AllowSecretFaces(next == Presence::Absent)" in life
    assert "if (!secret_ok_ && !IsListen(e) && !IsSmile(e))" in face


def test_actual_cpp_presence_handles_sensor_failure_and_recovery(tmp_path: Path) -> None:
    """The compiler executes the real firmware decision function via static_assert."""
    compiler = os.environ.get("CXX") or shutil.which("g++") or shutil.which("clang++")
    if not compiler and os.name == "nt":
        tools = Path(os.environ.get("IDF_TOOLS_PATH", "E:/AI_TOY_TOOLS/espressif"))
        compiler = next(tools.glob("tools/xtensa-esp-elf/*/*/bin/xtensa-esp32s3-elf-g++.exe"), None)
    if not compiler:
        pytest.skip("Set CXX to a C++17 compiler to run firmware presence checks")

    source = tmp_path / "presence.cpp"
    source.write_text(r'''
#include "niulai_presence.h"
#include <limits>
using P = NiulaiPresence;

constexpr bool invalid_stops(float cm) {
    int64_t since = 0;
    return ObserveNiulaiDistance(cm, 9000000, since, P::Absent) == P::Unknown && since == -1;
}
static_assert(invalid_stops(-1.0f), "timeout cancels ABSENT");
static_assert(invalid_stops(0.0f), "zero is not a clear room");
static_assert(invalid_stops(1.0f), "below sensor range is unknown");
static_assert(invalid_stops(401.0f), "above sensor range is unknown");
static_assert(invalid_stops(std::numeric_limits<float>::infinity()), "infinity is unknown");
static_assert(invalid_stops(std::numeric_limits<float>::quiet_NaN()), "NaN is unknown");

constexpr bool timeout_never_establishes_absence() {
    int64_t since = -1;
    P state = P::Unknown;
    for (int64_t now = 0; now <= 20000000; now += 200000) {
        state = ObserveNiulaiDistance(-1.0f, now, since, state);
        if (state != P::Unknown || since != -1) return false;
    }
    return true;
}
static_assert(timeout_never_establishes_absence(), "disconnected sensor must stay UNKNOWN");

constexpr bool continuous_far_requires_eight_seconds() {
    int64_t since = -1;
    P state = P::Unknown;
    for (int64_t now = 0; now < 8000000; now += 200000) {
        state = ObserveNiulaiDistance(100.0f, now, since, state);
        if (state != P::Unknown) return false;
    }
    return ObserveNiulaiDistance(100.0f, 8000000, since, state) == P::Absent;
}
static_assert(continuous_far_requires_eight_seconds(), "no premature SECRET");

constexpr bool recovery_restarts_countdown() {
    int64_t since = 0;
    P state = ObserveNiulaiDistance(-1.0f, 9000000, since, P::Absent);
    state = ObserveNiulaiDistance(100.0f, 10000000, since, state);
    if (state != P::Unknown || since != 10000000) return false;
    state = ObserveNiulaiDistance(100.0f, 17999999, since, state);
    if (state != P::Unknown) return false;
    return ObserveNiulaiDistance(100.0f, 18000000, since, state) == P::Absent;
}
static_assert(recovery_restarts_countdown(), "old clear time must not survive a failed reading");

constexpr bool near_resets_clear_time() {
    int64_t since = 0;
    P state = ObserveNiulaiDistance(2.0f, 7000000, since, P::Unknown);
    if (state != P::Present || since != -1) return false;
    state = ObserveNiulaiDistance(55.0f, 8000000, since, state);
    if (state != P::Present) return false;
    state = ObserveNiulaiDistance(400.0f, 15999999, since, state);
    if (state != P::Present) return false;
    return ObserveNiulaiDistance(100.0f, 16000000, since, state) == P::Absent;
}
static_assert(near_resets_clear_time(), "a person restarts the full absence interval");
''', encoding="utf-8")
    result = subprocess.run(
        [str(compiler), "-std=c++17", "-fsyntax-only", "-I", str(LIFE.parent), str(source)],
        capture_output=True, text=True, timeout=30,
    )
    assert result.returncode == 0, result.stdout + result.stderr
