from __future__ import annotations

import sqlite3
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
LIVE_SQLITE = (ROOT / "brain" / "data" / "niulai-memory.sqlite").resolve()


def test_importing_main_does_not_open_live_sqlite() -> None:
    probe = r"""
from __future__ import annotations
import sqlite3
import sys
from pathlib import Path

root = Path(sys.argv[1]).resolve()
sys.path.insert(0, str(root))
live = (root / "brain" / "data" / "niulai-memory.sqlite").resolve()
opened: list[str] = []
real = sqlite3.connect


def spy(database, *args, **kwargs):
    opened.append(str(database))
    raw = str(database)
    if raw != ":memory:":
        try:
            if Path(raw).resolve() == live:
                print("LIVE_SQLITE_OPENED")
                raise SystemExit(2)
        except OSError:
            pass
    return real(database, *args, **kwargs)


sqlite3.connect = spy
import brain.app.main  # noqa: E402
print("IMPORT_OK")
print("OPENED=" + repr(opened))
"""
    result = subprocess.run(
        [sys.executable, "-c", probe, str(ROOT)],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    output = result.stdout + result.stderr
    assert "LIVE_SQLITE_OPENED" not in output, output
    assert result.returncode == 0, output
    assert "IMPORT_OK" in result.stdout


def test_create_app_with_injected_brain_does_not_open_live_sqlite(
    monkeypatch,
) -> None:
    from brain.app.brain import NiulaiBrain
    from brain.app.main import create_app

    opened: list[str] = []
    real = sqlite3.connect

    def spy(database, *args, **kwargs):
        opened.append(str(database))
        raw = str(database)
        if raw != ":memory:":
            try:
                if Path(raw).resolve() == LIVE_SQLITE:
                    raise AssertionError(f"opened live sqlite: {database}")
            except OSError:
                pass
        return real(database, *args, **kwargs)

    monkeypatch.setattr(sqlite3, "connect", spy)
    import brain.app.memory as memory

    monkeypatch.setattr(memory.sqlite3, "connect", spy)
    create_app(NiulaiBrain())
    for path in opened:
        if path == ":memory:":
            continue
        assert Path(path).resolve() != LIVE_SQLITE


def test_create_app_opens_configured_persistent_db(tmp_path, monkeypatch) -> None:
    db = tmp_path / "prod.sqlite"
    import brain.app.main as main

    monkeypatch.setattr(main, "DEFAULT_MEMORY", db)
    app = main.create_app()
    assert Path(app.state.brain.memory.path).resolve() == db.resolve()
    assert db.exists()
