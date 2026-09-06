from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
LIFE = ROOT / "firmware" / "xiaozhi-niulai" / "niulai_life.cc"
FACE = ROOT / "firmware" / "xiaozhi-niulai" / "niulai_face_display.cc"


def test_overlay_close_parks_and_unknown_blocks_new_walk() -> None:
    text = LIFE.read_text(encoding="utf-8")
    assert "if (close) {" in text
    assert "ParkLegs();" in text
    assert "last_close_" in text
    assert "presence_ == kUnknown || last_close_" in text
    assert "ms > 2000" in text


def test_overlay_secret_faces_only_when_absent() -> None:
    life = LIFE.read_text(encoding="utf-8")
    face = FACE.read_text(encoding="utf-8")
    assert "AllowSecretFaces(next == kAbsent)" in life
    assert "if (!secret_ok_ && !IsListen(e) && !IsSmile(e))" in face
