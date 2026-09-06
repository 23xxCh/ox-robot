# FAST_TRACK assignment 2026-09-06 08:29 +08

HEAD: `381d86a` (L00/L02/L01 integrated). Live uvicorn PID 41712 not owned by this sprint. No second scheduler.

PM 3-liner:
- User-visible: abort/fail cannot keep playing a secret line; health shows a version; interrupt is used once; overlay fallback path is explicit in source.
- Accept: targeted tests green; orchestrator one `pytest brain/tests`; firmware source/build/hear recorded separately.
- Not this slice: flash, ClawBot token, Feishu, 40-item rescore, new scene engine.

## Path lock

| Line | Owns | Must not touch |
|---|---|---|
| A | `brain/app/main.py`, `brain/app/media.py`, `brain/tests/test_protocol.py`, `brain/tests/test_media.py` | firmware/, secret_life.py, memory.py, origin.py |
| B | `firmware/xiaozhi-niulai/` | brain/ |
| C | `brain/app/secret_life.py`, `brain/app/memory.py`, `brain/app/origin.py`, `brain/app/lifecycle.py`, `brain/tests/test_secret_life.py`, `brain/tests/test_memory.py`, `brain/tests/test_lifecycle.py` | main.py, media.py, firmware/ |

Shared leftover: `mcp_broker.py` frozen (L02). Nobody edits it this slice.

## Interface C produces, A may wire later

```python
# MemoryStore
def consume_interrupt(self, device_id: str) -> str | None:
    """Return pending_complaint once, then clear it. Missing -> None."""
```

A must not wait on C. If C is not merged yet, A only does abort/health.

## B evidence levels

resource exists / source branch / heard on device — never collapse these.
Native tree writes only if B verifies exclusive ownership; default overlay-only. No flash.
