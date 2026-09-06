# P-05 / NIU-L04 local-fallback evidence

Three columns stay separate. `heard=NOT_RUN` (no COM6 flash, no device listen this slice).

SHA-256 of overlay clips (2026-09-06), matching `E:\XIAOZHI_NATIVE\xiaozhi-esp32\main\assets\common\`:

| file | bytes | sha256 |
|---|---:|---|
| `secret1.ogg` | 10163 | `025E332C6E748D43683CAF109E16F5B0FC98E723F610E1862D1FDC92E6F0ACC7` |
| `secret2.ogg` | 5817 | `3D2A4136FF1480B4F21AFFEB07867EDAA91E25344A125F46E5C25472ADDCA39B` |
| `secret3.ogg` | 7228 | `17BE492CEB992B554AED67DC1B438826A974B9803CD739FBD40CD7793F94DCEF` |
| `mama.ogg` | 17427 | `B30FE644243F3102BE311DC8A10B19A10361901FCAA5C7EC798C3ACCD329F5FD` |
| `hi.ogg` | 7662 | `278D6DDFE09C4EA3FADC710F0DF4A743AEF8424C6573FE46EFB668C54F3F754C` |

| resource | exists | source branch | heard |
|---|---|---|---|
| overlay `secret1.ogg` | yes (`firmware/xiaozhi-niulai/secret1.ogg`) | overlay `AskBrainSecret()` schedules WSS only; native `application.cc` `NiulaiEnterSecret()` `PlaySound(OGG_SECRET1)` on WSS fail | NOT_RUN |
| overlay `secret2.ogg` | yes | same rotate slot 1 → `OGG_SECRET2` | NOT_RUN |
| overlay `secret3.ogg` | yes | same rotate slot 2 → `OGG_SECRET3` | NOT_RUN |
| overlay `mama.ogg` | yes | native `NiulaiStartPoliteChat()` only; **not** on ultrasonic PRESENT | NOT_RUN |
| overlay `hi.ogg` | yes | `OGG_HI` in native `lang_config.h`; unused by overlay life loop | NOT_RUN |
| native `main/assets/common/secret1.ogg` | yes (hash == overlay) | embedded as `Lang::Sounds::OGG_SECRET1` | NOT_RUN |
| native `main/assets/common/secret2.ogg` | yes (hash == overlay) | `OGG_SECRET2` | NOT_RUN |
| native `main/assets/common/secret3.ogg` | yes (hash == overlay) | `OGG_SECRET3` | NOT_RUN |
| close freeze | source-confirmed overlay | `Loop()` `close` → `ParkLegs()` zeros `motion_until_us_` + 1500 µs | NOT_RUN |
| secret quiet window | source-confirmed overlay | `presence_ == kAbsent` every 3rd retry; PRESENT asked walk not banned | NOT_RUN |
| native board copy `niulai_life.cc` | exists, **stale vs overlay** (no `last_close_`, close does `HoldCenter` not `ParkLegs`) | overlay-only this slice; native not written | NOT_RUN |
| IDF compile `niulai-s3-expand-v17` | yes: `python scripts/build.py niulai-s3-expand-v17` from `E:\XIAOZHI_NATIVE\xiaozhi-esp32` → `xiaozhi.bin` 0x2ac5b0, `merged-binary.bin` 0xafb985 | **BUILD_PASS** of **native** tree (stale `boards/niulai-s3-expand-v17/niulai_life.cc`, no overlay `last_close_` / close-`ParkLegs`). Overlay not copied. No flash. | NOT_RUN |

Hardware untested this slice: COM6 flash, speaker hear, ultrasonic PRESENT freeze on device, WSS-fail mutter on device. Overlay close-freeze / ABSENT quiet is source-confirmed only.
